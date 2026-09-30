import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import proposal_review as workflow


class WorkflowTests(unittest.TestCase):
    def test_sponsored_compatible_endpoint_uses_configured_model_and_key(self):
        with tempfile.TemporaryDirectory() as directory:
            proposal = Path(directory) / "proposal.md"
            proposal.write_text("Synthetic proposal", encoding="utf-8")
            config = {"llm_provider": "openai_compatible", "base_url": "https://sponsor.example/v1",
                      "model": "sponsor-model", "require_free_model": False,
                      "max_tokens_parameter": "max_completion_tokens"}
            process = subprocess.CompletedProcess([], 0, '{"decision":"Uncertain","review":"Text"}', "sponsor-key")
            with (patch.dict(os.environ, {"LLM_API_KEY": "sponsor-key", "OPENAI_API_KEY": "old-key",
                                         "OPENROUTER_API_KEY": "old-router-key"}),
                  patch.object(workflow.subprocess, "run", return_value=process) as run):
                workflow.run_review(proposal, config)
            env = run.call_args.kwargs["env"]
            self.assertEqual(env["OPENAI_API_KEY"], "sponsor-key")
            self.assertEqual(env["OPENAI_BASE_URL"], "https://sponsor.example/v1")
            self.assertEqual(env["RUBRIC_MAX_TOKENS_PARAMETER"], "max_completion_tokens")
            self.assertNotIn("LLM_API_KEY", env)
            self.assertNotIn("OPENROUTER_API_KEY", env)
            self.assertEqual(run.call_args.args[0].count("openai/sponsor-model"), 2)
            self.assertNotIn("sponsor-key", (Path(directory) / "review.log").read_text())

    def test_free_model_policy_is_optional_and_explicit(self):
        config = {"llm_provider": "openrouter", "base_url": "https://openrouter.ai/api/v1",
                  "model": "vendor/paid-model", "require_free_model": True}
        with self.assertRaises(ValueError):
            workflow.validate_model_config(config)
        config["require_free_model"] = False
        workflow.validate_model_config(config)

    def test_unknown_provider_and_invalid_endpoint_are_rejected_before_call(self):
        base = {"llm_provider": "openai_compatible", "base_url": "https://sponsor.example/v1", "model": "model"}
        for change in ({"llm_provider": "bedrock"}, {"base_url": "http://sponsor.example/v1"},
                       {"base_url": "https://key@sponsor.example/v1"}, {"base_url": "https://sponsor.example/v1?key=value"},
                       {"model": ""}, {"require_free_model": "false"}, {"max_tokens_parameter": "unsupported"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                workflow.validate_model_config(base | change)

    def test_missing_generic_key_does_not_reuse_other_provider_credentials(self):
        with (patch.dict(os.environ, {"OPENROUTER_API_KEY": "old-key"}, clear=True),
              patch.object(workflow.subprocess, "run") as run):
            with self.assertRaises(ValueError):
                workflow.run_review(Path("unused"), {"llm_provider": "openai_compatible",
                    "base_url": "https://sponsor.example/v1", "model": "sponsor-model"})
        run.assert_not_called()

    def event(self, comment="/review"):
        return {"action": "created", "discussion": {"number": 33, "category": {"name": "Task Proposals"}},
                "comment": {"body": comment, "user": {"login": "member"}}}

    def test_trigger_matrix(self):
        self.assertTrue(workflow.allowed_trigger("discussion", self.event()))
        self.assertTrue(workflow.allowed_trigger("workflow_dispatch", {}))
        for permission in ("read", "triage", None):
            self.assertFalse(workflow.allowed_trigger("discussion_comment", self.event(), permission))
        for permission in ("write", "admin"):
            self.assertTrue(workflow.allowed_trigger("discussion_comment", self.event(), permission))
        self.assertFalse(workflow.allowed_trigger("discussion_comment", self.event("AI review result"), "admin"))
        event = self.event()
        event["discussion"]["category"]["name"] = "General"
        self.assertFalse(workflow.allowed_trigger("discussion", event))

    def test_unprivileged_comment_does_not_fetch_proposal(self):
        with patch.object(workflow, "request_json", return_value={"permission": "read"}) as request:
            self.assertIsNone(workflow.resolve_discussion("discussion_comment", self.event(), "owner/repo", "token"))
            self.assertEqual(request.call_count, 1)

    def test_runner_uses_free_model_and_excludes_service_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            proposal = Path(directory) / "proposal.md"
            proposal.write_text("# proposal")
            config = {"llm_provider": "openrouter", "base_url": "https://openrouter.ai/api/v1", "model": "qwen/qwen3.8-27b:free"}
            result = {"decision": "Accept", "review": "Scientific review", "author_fit": None, "task": "path"}
            process = subprocess.CompletedProcess([], 0, json.dumps(result), "api-key")
            with (patch.dict(os.environ, {"LLM_API_KEY": "api-key", "AI_REVIEW_SERVICE_KEY": "internal-secret", "GH_TOKEN": "github-secret"}),
                  patch.object(workflow.subprocess, "run", return_value=process) as run):
                actual = workflow.run_review(proposal, config)
            self.assertNotIn("task", actual)
            env = run.call_args.kwargs["env"]
            self.assertNotIn("AI_REVIEW_SERVICE_KEY", env)
            self.assertNotIn("GH_TOKEN", env)
            self.assertEqual(env["OPENAI_BASE_URL"], config["base_url"])
            self.assertIn("openai/qwen/qwen3.8-27b:free", run.call_args.args[0])
            self.assertNotIn("api-key", (Path(directory) / "review.log").read_text())

    def test_upstream_parser_and_sdk_routing(self):
        spec = importlib.util.spec_from_file_location("rubric_review", Path(__file__).with_name("rubric_review.py"))
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"anthropic": MagicMock(), "httpx": MagicMock()}):
            spec.loader.exec_module(module)
        self.assertEqual(module._model_provider("openai/qwen/qwen3.8-27b:free"), "openai")
        self.assertEqual(module._strip_provider_prefix("openai/qwen/qwen3.8-27b:free"), "qwen/qwen3.8-27b:free")
        self.assertEqual(module.extract_decision("Decision: Strong Accept\nDecision-Reason: Sound science"), "Strong Accept")
        source = "Scientific problem\n## Author Information\nAuthor: Someone\nProfessional Profile: https://example.org"
        self.assertNotIn("Someone", module.strip_author_info(source))
        self.assertIn("Someone", module.extract_author_info(source))
        openai = MagicMock()
        response = openai.OpenAI.return_value.chat.completions.create.return_value
        response.choices[0].finish_reason = "length"
        with patch.dict(sys.modules, {"openai": openai}):
            with self.assertRaises(ValueError):
                module.call_openai("rubric", "proposal", "openai/qwen/qwen3.8-27b:free")
        response.choices[0].finish_reason = "stop"
        response.choices[0].message.content = "Decision: Uncertain"
        with (patch.dict(sys.modules, {"openai": openai}),
              patch.dict(os.environ, {"OPENAI_BASE_URL": "https://openrouter.ai/api/v1", "RUBRIC_MAX_TOKENS_PARAMETER": "max_tokens"})):
            self.assertEqual(module.call_openai("rubric", "proposal", "openai/qwen/qwen3.8-27b:free"),
                             "Decision: Uncertain")
        kwargs = openai.OpenAI.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "qwen/qwen3.8-27b:free")
        self.assertEqual(kwargs["max_tokens"], 4096)
        self.assertNotIn("max_completion_tokens", kwargs)

    def test_completed_result_is_preserved_when_backend_is_unavailable(self):
        import hashlib

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github").mkdir()
            (root / ".github/llm-config.json").write_text(json.dumps({"proposal_review": {
                "llm_provider": "openrouter", "model": "qwen/qwen3.8-27b:free",
                "base_url": "https://openrouter.ai/api/v1", "upstream_sha": "b" * 40,
            }}))
            event = root / "event.json"
            event.write_text("{}")
            environment = {"GITHUB_EVENT_PATH": str(event), "GITHUB_REPOSITORY": "owner/repo",
                "GH_TOKEN": "github-key", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ID": "101",
                "GITHUB_RUN_ATTEMPT": "1", "AI_REVIEW_BACKEND_URL": "https://backend.example/",
                "AI_REVIEW_SERVICE_KEY": "service-key" * 4}
            discussion = {"title": "Unicode 科学", "body": "$(echo untrusted)\n`text`", "number": 33, "id": "D_33"}
            with (patch.dict(os.environ, environment), patch.object(workflow, "ROOT", root),
                  patch.object(workflow, "resolve_discussion", return_value=discussion),
                  patch.object(workflow.subprocess, "check_output", return_value="c" * 40),
                  patch.object(workflow, "run_review", return_value={"decision": "Uncertain", "review": "Text"}),
                  patch.object(workflow, "request_json", side_effect=RuntimeError("Backend unavailable"))):
                with self.assertRaises(RuntimeError):
                    workflow.main()
            submitted = json.loads((root / "review-artifacts/result.json").read_text(encoding="utf-8"))
            self.assertEqual(submitted["status"], "completed")
            self.assertIsNone(submitted["error_summary"])
            digest = hashlib.sha256(f"{discussion['title']}\n{discussion['body']}".encode()).hexdigest()
            self.assertEqual(submitted["proposal_digest"], digest)
            self.assertIn(discussion["body"], (root / "review-artifacts/proposal.md").read_text(encoding="utf-8"))
            self.assertFalse((root / "review-artifacts/receipt.json").exists())


    def test_failed_model_still_submits_unavailable_and_retains_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github").mkdir()
            (root / ".github/llm-config.json").write_text(json.dumps({"proposal_review": {
                "llm_provider": "openrouter", "model": "qwen/qwen3.8-27b:free",
                "base_url": "https://openrouter.ai/api/v1", "upstream_sha": "b" * 40,
            }}))
            event = root / "event.json"
            event.write_text("{}")
            environment = {"GITHUB_EVENT_PATH": str(event), "GITHUB_REPOSITORY": "owner/repo",
                "GH_TOKEN": "github-key", "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ID": "101",
                "GITHUB_RUN_ATTEMPT": "2", "GITHUB_WORKFLOW_SHA": "a" * 40,
                "AI_REVIEW_BACKEND_URL": "https://backend.example", "AI_REVIEW_SERVICE_KEY": "service-key" * 4}
            discussion = {"title": "A proposal", "body": "Text", "number": 33, "id": "D_33"}
            with (patch.dict(os.environ, environment), patch.object(workflow, "ROOT", root),
                  patch.object(workflow, "resolve_discussion", return_value=discussion),
                  patch.object(workflow.subprocess, "check_output", return_value="c" * 40 + "\n"),
                  patch.object(workflow, "run_review", side_effect=RuntimeError("provider-secret")),
                  patch.object(workflow, "request_json", return_value={"review_id": "review-1"}) as request):
                workflow.main()
            submitted = request.call_args.args[2]
            self.assertEqual(submitted["status"], "unavailable")
            self.assertIsNone(submitted["result"])
            self.assertEqual(submitted["run_attempt"], 2)
            self.assertEqual(submitted["workflow_sha"], "c" * 40)
            self.assertNotIn("provider-secret", json.dumps(submitted))
            self.assertEqual(request.call_args.args[0], "https://backend.example/api/v1/internal/proposal-ai-reviews")
            self.assertTrue((root / "review-artifacts/receipt.json").exists())

    def test_malformed_and_oversized_results_are_rejected(self):
        for result in ([], None, {"decision": [], "review": "text"},
                       {"decision": "Accept", "review": 42},
                       {"decision": "Accept", "review": " "},
                       {"decision": "Accept", "review": "x" * 30_001},
                       {"decision": "Accept", "review": "ok", "summary": "x" * 4_001}):
            with self.subTest(result_type=type(result).__name__):
                with self.assertRaises(ValueError):
                    workflow.validate_result(result)

    def test_invalid_advisory_enums_do_not_change_primary_verdict(self):
        result = workflow.validate_result({"decision": "Reject", "review": "text",
                                           "author_fit": [], "coi": "Unknown"})
        self.assertEqual(result["decision"], "Reject")
        self.assertIsNone(result["author_fit"])
        self.assertIsNone(result["coi"])

    def test_permission_lookup_failure_denies_review(self):
        with patch.object(workflow, "request_json", side_effect=RuntimeError("HTTP 403")) as request:
            self.assertIsNone(workflow.resolve_discussion("discussion_comment", self.event(), "owner/repo", "token"))
        self.assertEqual(request.call_count, 1)

    def test_dispatch_resolves_canonical_discussion_and_checks_category(self):
        discussion = {"id": "D_33", "number": 33, "title": "Title", "body": "Text",
                      "category": {"name": "Task Proposals"}}
        with patch.object(workflow, "request_json", return_value={"data": {"repository": {"discussion": discussion}}}) as request:
            self.assertEqual(workflow.resolve_discussion("workflow_dispatch", {"inputs": {"discussion_number": "33"}},
                                                        "owner/repo", "token"), discussion)
            self.assertEqual(request.call_args.args[2]["variables"]["number"], 33)
            discussion["category"]["name"] = "General"
            with self.assertRaises(ValueError):
                workflow.resolve_discussion("workflow_dispatch", {"inputs": {"discussion_number": "33"}}, "owner/repo", "token")

    def test_graphql_errors_are_not_treated_as_success(self):
        with patch.object(workflow, "request_json", return_value={"errors": [{"message": "denied"}]}):
            with self.assertRaises(RuntimeError):
                workflow.resolve_discussion("discussion", self.event(), "owner/repo", "token")

    def test_permanent_callback_errors_are_not_retried(self):
        import urllib.error

        for status in (401, 409, 422):
            opener = MagicMock()
            opener.open.side_effect = urllib.error.HTTPError("https://backend.example", status, "rejected", {}, None)
            with (patch.object(workflow.urllib.request, "build_opener", return_value=opener),
                  patch.object(workflow.time, "sleep") as sleep):
                with self.assertRaises(RuntimeError):
                    workflow.request_json("https://backend.example", "private-key", {"run_id": 123})
            self.assertEqual(opener.open.call_count, 1)
            sleep.assert_not_called()

    def test_callback_retries_are_bounded(self):
        opener = MagicMock()
        opener.open.side_effect = TimeoutError()
        with (patch.object(workflow.urllib.request, "build_opener", return_value=opener),
              patch.object(workflow.time, "sleep") as sleep):
            with self.assertRaises(RuntimeError):
                workflow.request_json("https://backend.example", "private-key", {}, attempts=3)
        self.assertEqual(opener.open.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_redirect_does_not_forward_credentials(self):
        self.assertIsNone(workflow.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.example"))

    def test_transient_callback_retry_preserves_payload(self):
        import io
        import urllib.error

        error = urllib.error.HTTPError("https://backend.example", 503, "busy", {}, None)
        opener = MagicMock()
        response = MagicMock()
        response.__enter__.return_value = io.BytesIO(b'{"review_id":"same"}')
        opener.open.side_effect = [error, response]
        with (patch.object(workflow.urllib.request, "build_opener", return_value=opener),
              patch.object(workflow.time, "sleep")):
            value = workflow.request_json("https://backend.example", "private-key", {"run_id": 123})
        self.assertEqual(value["review_id"], "same")
        first, second = opener.open.call_args_list
        self.assertEqual(first.args[0].data, second.args[0].data)

    def test_bad_model_decision_fails_instead_of_inventing_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            proposal = Path(directory) / "proposal.md"
            proposal.write_text("proposal")
            process = subprocess.CompletedProcess([], 0, '{"decision":null,"review":"Unparseable"}', "")
            with (patch.dict(os.environ, {"LLM_API_KEY": "test-key"}),
                  patch.object(workflow.subprocess, "run", return_value=process)):
                with self.assertRaises(ValueError):
                    workflow.run_review(proposal, {"llm_provider": "openrouter", "base_url": "https://openrouter.ai/api/v1", "model": "qwen/qwen3.8-27b:free"})


if __name__ == "__main__":
    unittest.main()
