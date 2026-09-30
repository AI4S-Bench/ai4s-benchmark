# ai4sbench benchmark repository

This directory is the public, standalone Harbor task repository. Its layout is
intentionally compatible with the Terminal-Bench-Science contribution model:

```text
benchmark-repository/
├── .github/                 pull request template and task validation workflow
├── tasks/<domain>/<field>/  Harbor task directories
├── scripts/                 contribution validation
├── bench/                   pinned runtime and validation matrix
├── tests/                   public repository validation tests
└── CONTRIBUTING.md          public contributor protocol
```

It must not contain control-plane credentials, SQLite state, EC2 configuration,
or the operator dashboard. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for task
submission requirements and [`bench/README.md`](bench/README.md) for Harbor
validation.

## Automated proposal reviews

`proposal-review.yml` reviews new `Task Proposals` Discussions, write/admin
collaborator `/review` comments and manual Discussion-number dispatches.
Configure Actions Secrets `OPENROUTER_API_KEY` and `AI_REVIEW_SERVICE_KEY`, and
Actions Variable `AI_REVIEW_BACKEND_URL` (the backend HTTPS origin).
Deploy the backend AI review API first. It owns GitHub/Discord publication.

The free test model is `qwen/qwen3.8-27b:free`, configured in
`.github/llm-config.json` with OpenRouter's `https://openrouter.ai/api/v1` endpoint.
Its zero prompt/completion pricing and availability were checked against the
[OpenRouter catalog](https://openrouter.ai/api/v1/models) on 2026-09-30 UTC.
Recheck availability and your account quota before enabling the workflow.
Upstream rubric
provenance and local adaptations are documented in `ci_checks/UPSTREAM.md`.
No paid fallback is configured. Run helper tests with:

```sh
uv run --locked --script ci_checks/rubric_review.py --help
python -m unittest discover -s ci_checks -p 'test_*.py'
```

Python 3.12 and `uv` are used in CI. The SDK smoke test uses a local HTTP server
and synthetic proposal; no provider key or paid model calls are needed.

Only the backend service key belongs in the callback; the OpenRouter key is used
only by the model process. The workflow does not need a Discord webhook or a
GitHub publishing token. A 202 callback means queued; operators monitor delivery
states in the backend. Results and sanitized diagnostics are retained as Actions
artifacts for seven days. This integration reviews text only, even if the selected
model supports images: image references remain in the text but are not downloaded.
The combined rubric/input budget remains 28,000 UTF-8 bytes and each pass requests
up to 4,096 output tokens. Empty, truncated, malformed or oversized review output
produces an unavailable-review placeholder. Author-fit is advisory and its failure
does not replace a valid primary verdict.

### Deployment and acceptance

1. Deploy the backend from `hycarbon-b/ai4sbench#34`, including migration
   `20260924_0017`, the API and job runner. Configure the bot publishing token,
   Discord webhook and service key there.
2. In this repository's Settings > Secrets and variables > Actions, set secrets
   `OPENROUTER_API_KEY` and `AI_REVIEW_SERVICE_KEY` (matching backend
   `TBCP_AI_REVIEW_SERVICE_KEY`), plus variable `AI_REVIEW_BACKEND_URL` to the HTTPS
   origin only, without `/api/v1`, a query string or credentials.
3. Merge this workflow to the default branch only when the backend/configuration
   is ready: new `Task Proposals` Discussions then trigger reviews automatically.
4. Run Proposal Review manually for a test Discussion in `Task Proposals`.
   Verify both model passes using a proposal with an Author Information section.
   Check `receipt.json` for the review ID, then call
   `GET /api/v1/internal/proposal-ai-reviews/{review_id}` with the service key to
   confirm both deliveries completed. Check the actual GitHub and Discord messages.
5. Test a write/admin collaborator's `/review` comment, an unauthorized comment,
   a new proposal, model unavailability and partial publication failure. Permission
   lookup uses the Actions token and must be checked in the real repository;
   lookup failures deny the review. Repeated reviews must update existing messages.
6. Run Full Sync and verify AI advice does not change human approval. Update the
   parent repository's submodule pointer after this PR merges.

The workflow checks out default-branch code and records the executed commit as
`workflow_sha`. Callback retries reuse the same payload/run/attempt; 401, 409 and
422 responses are not retried. A failed callback fails Actions and retains the
result for diagnosis. Editing a proposal requires a new `/review` to assess the
new content. Disabling the workflow stops new runs; already queued backend
deliveries may still publish.
