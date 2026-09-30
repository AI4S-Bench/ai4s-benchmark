"""Actions entry point: resolve a proposal, run the TBS judge, call the backend.

Only trusted repository code is executed. Proposal text is always file data.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = {"Strong Reject", "Reject", "Uncertain", "Accept", "Strong Accept"}
FIELDS = {"decision", "decision_reason", "review", "scientific_domain", "summary", "justification",
          "author_name", "author_profile", "author_academic_profile", "author_fit", "author_fit_reason",
          "author_fit_review", "coi", "coi_reason"}
FIELD_LIMITS = {
    "review": 30_000, "decision_reason": 2_000, "scientific_domain": 500,
    "summary": 4_000, "justification": 4_000, "author_name": 300,
    "author_profile": 1_000, "author_academic_profile": 1_000,
    "author_fit_reason": 2_000, "author_fit_review": 12_000, "coi_reason": 2_000,
}


def validate_model_config(config):
    """Only repository-owned configuration chooses where the model key is sent."""
    provider = config.get("llm_provider")
    if provider not in {"openrouter", "openai_compatible"}:
        raise ValueError("Unsupported model provider; an adapter is required")
    model = config.get("model")
    if not isinstance(model, str) or not model.strip() or len(model) > 200:
        raise ValueError("Configure a model ID")
    endpoint = urllib.parse.urlsplit(config.get("base_url", ""))
    if (endpoint.scheme != "https" or not endpoint.hostname or endpoint.username
            or endpoint.password or endpoint.query or endpoint.fragment):
        raise ValueError("Configure an HTTPS model base URL without credentials or query parameters")
    if provider == "openrouter" and config["base_url"].rstrip("/") != "https://openrouter.ai/api/v1":
        raise ValueError("Unexpected OpenRouter endpoint")
    free_only = config.get("require_free_model", False)
    if not isinstance(free_only, bool):
        raise ValueError("require_free_model must be a boolean")
    if free_only and (provider != "openrouter" or not model.endswith(":free")):
        raise ValueError("Free-only policy requires an OpenRouter :free model")
    if config.get("max_tokens_parameter", "max_tokens") not in {"max_tokens", "max_completion_tokens"}:
        raise ValueError("Unsupported completion token parameter")


def validate_result(result):
    """Reject malformed output before it can turn into a backend 422 response."""
    if (not isinstance(result, dict) or not isinstance(result.get("decision"), str)
            or result["decision"] not in DECISIONS):
        raise ValueError("Rubric runner returned no valid decision")
    review = result.get("review")
    if not isinstance(review, str) or not review.strip():
        raise ValueError("Rubric runner returned no review text")
    result = {key: value for key, value in result.items() if key in FIELDS}
    for field, limit in FIELD_LIMITS.items():
        value = result.get(field)
        if value is not None and (not isinstance(value, str) or len(value.strip()) > limit):
            raise ValueError(f"Rubric field {field} exceeds the backend contract")
    for field, allowed in (("author_fit", (None, "Direct", "Adjacent", "Unrelated")),
                           ("coi", (None, "None", "Disclosed"))):
        if result.get(field) not in allowed:
            result[field] = None
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward a credential to a redirected host.


def request_json(url, token, payload=None, attempts=7):
    encoded = json.dumps(payload).encode() if payload is not None else None
    for attempt in range(attempts):
        request = urllib.request.Request(url, data=encoded, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "Content-Type": "application/json", "User-Agent": "ai4s-proposal-review",
        })
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"Request rejected with HTTP {error.code}") from None
        except (urllib.error.URLError, TimeoutError):
            pass
        if attempt + 1 < attempts:
            time.sleep(min(30, 2 ** attempt * 2))
    raise RuntimeError("Request failed after bounded retries")


def allowed_trigger(event_name, event, permission=None):
    if event_name == "workflow_dispatch":
        return True
    if (event.get("discussion", {}).get("category") or {}).get("name") != "Task Proposals":
        return False
    if event_name == "discussion":
        return event.get("action") == "created"
    return (event_name == "discussion_comment" and event.get("action") == "created"
            and event.get("comment", {}).get("body", "").startswith("/review")
            and permission in {"write", "admin"})


def resolve_discussion(event_name, event, repo, token):
    if event_name == "discussion_comment":
        if not event.get("comment", {}).get("body", "").startswith("/review"):
            return None
        if (event.get("discussion", {}).get("category") or {}).get("name") != "Task Proposals":
            return None
        login = urllib.parse.quote(event["comment"]["user"]["login"], safe="")
        try:
            permission = request_json(f"https://api.github.com/repos/{repo}/collaborators/{login}/permission",
                                      token).get("permission")
        except RuntimeError:
            permission = None  # Fail closed when permission lookup is unavailable.
    else:
        permission = None
    if not allowed_trigger(event_name, event, permission):
        return None
    number = int(event.get("inputs", {}).get("discussion_number", 0) if event_name == "workflow_dispatch"
                 else event["discussion"]["number"])
    if number < 1:
        raise ValueError("A positive Discussion number is required")
    owner, name = repo.split("/", 1)
    result = request_json("https://api.github.com/graphql", token, {
        "query": "query($owner:String!,$name:String!,$number:Int!) { repository(owner:$owner,name:$name) { "
                 "discussion(number:$number) { id number title body category { name } } } }",
        "variables": {"owner": owner, "name": name, "number": number},
    })
    if result.get("errors"):
        raise RuntimeError("Discussion lookup returned GraphQL errors")
    discussion = (result.get("data", {}).get("repository") or {}).get("discussion")
    if not discussion or discussion["category"]["name"] != "Task Proposals":
        raise ValueError("Discussion must exist in Task Proposals")
    return discussion


def run_review(proposal, config):
    validate_model_config(config)
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise ValueError("Configure LLM_API_KEY for the selected endpoint")
    environment = dict(os.environ)
    for key in ("AI_REVIEW_SERVICE_KEY", "GH_TOKEN", "GITHUB_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
                "LLM_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        environment.pop(key, None)
    environment["OPENAI_API_KEY"] = api_key
    environment["OPENAI_BASE_URL"] = config["base_url"]
    environment["RUBRIC_MAX_TOKENS_PARAMETER"] = config.get("max_tokens_parameter", "max_tokens")
    environment["PYTHONIOENCODING"] = "utf-8"
    command = ["uv", "run", "--locked", "--script", str(ROOT / "ci_checks/rubric_review.py"),
               "--model", f"openai/{config['model']}", "--author-fit", "--author-fit-model", f"openai/{config['model']}", str(proposal)]
    completed = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True,
                               text=True, encoding="utf-8", timeout=360, check=False)
    # Upstream stderr may contain SDK errors; remove credentials before retaining diagnostics.
    log = completed.stderr
    for key in ("OPENAI_API_KEY", "LLM_API_KEY", "OPENROUTER_API_KEY", "AI_REVIEW_SERVICE_KEY", "GH_TOKEN", "GITHUB_TOKEN"):
        secret = environment.get(key) or os.environ.get(key)
        if secret:
            log = log.replace(secret, "[REDACTED]")
    (proposal.parent / "review.log").write_text(log, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError("Rubric runner failed")
    return validate_result(json.loads(completed.stdout))


def main():
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    discussion = resolve_discussion(os.environ["GITHUB_EVENT_NAME"], event, repo, token)
    if discussion is None:
        print("Trigger does not request an authorized proposal review.")
        return
    config = json.loads((ROOT / ".github/llm-config.json").read_text(encoding="utf-8"))["proposal_review"]
    validate_model_config(config)
    base_url = os.environ.get("AI_REVIEW_BACKEND_URL", "").rstrip("/")
    parsed_url = urllib.parse.urlsplit(base_url)
    if (parsed_url.scheme != "https" or not parsed_url.hostname or parsed_url.username
            or parsed_url.password or parsed_url.path or parsed_url.query or parsed_url.fragment):
        raise ValueError("Configure the backend HTTPS URL")
    service_key = os.environ.get("AI_REVIEW_SERVICE_KEY", "")
    if len(service_key) < 32:
        raise ValueError("Configure the backend service key")
    artifacts = ROOT / "review-artifacts"
    artifacts.mkdir(exist_ok=True)
    proposal = artifacts / "proposal.md"
    proposal.write_text(f"# {discussion['title']}\n\n{discussion['body']}\n", encoding="utf-8")
    digest = hashlib.sha256(f"{discussion['title']}\n{discussion['body']}".encode()).hexdigest()
    payload = {
        "schema_version": "ai4sbench-proposal-ai-review/v1", "repository": repo,
        "discussion_number": discussion["number"], "discussion_node_id": discussion["id"],
        "proposal_digest": digest, "run_id": int(os.environ["GITHUB_RUN_ID"]),
        "run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"]),
        # Checkout follows the trusted default branch, which may have advanced
        # since the event (or an old run being retried). Record the executed code.
        "workflow_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "upstream_sha": config["upstream_sha"],
        "model": config["model"], "status": "unavailable", "result": None,
        "error_summary": "Automated review failed; see workflow diagnostics.",
    }
    try:
        payload["result"] = run_review(proposal, config)
        payload["status"] = "completed"
        payload["error_summary"] = None
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.TimeoutExpired) as error:
        print(f"Review unavailable ({type(error).__name__}); submitting the failure placeholder.")
    (artifacts / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt = request_json(base_url + "/api/v1/internal/proposal-ai-reviews", service_key, payload)
    (artifacts / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"Backend accepted review {receipt['review_id']}; publication is queued.")


if __name__ == "__main__":
    main()
