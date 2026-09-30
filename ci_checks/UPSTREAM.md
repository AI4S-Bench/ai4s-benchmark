# Proposal reviewer provenance

Vendored from harbor-framework/terminal-bench-science at
`f55c14ea065243c8d094e02c0aa156d5fd22fdd4`:

- `ci_checks/rubric_review.py`
- `rubrics/task-proposal.md`
- `rubrics/author-fit.md`

Apache-2.0 license: [TBS-LICENSE](TBS-LICENSE).
Rubric Markdown is unchanged. AI4S changes to the runner are limited to disabling
image downloads for this text-only integration, reading proposal/rubric files as
UTF-8, bounding input bytes, setting SDK timeouts, configuring the completion-token
parameter, and rejecting empty/truncated output. Both upstream passes
and result extraction remain intact. The adjacent script lock pins dependencies.

The workflow preserves discussion-created, maintainer `/review`, and manual
Discussion-number triggers. Backend publication replaces all direct GitHub and
Discord writes. Model/provider configuration uses JSON to avoid a yq dependency.

The temporary free test model is `qwen/qwen3.8-27b:free`; the original planned
`z-ai/glm-5.2:free` was absent from the public OpenRouter catalog when rechecked
on 2026-09-30 UTC. This changes the model configuration, not either rubric.
The helper also supports explicitly configured OpenAI-compatible endpoints with
the generic `LLM_API_KEY` secret. The free-only policy is optional. Sponsor AWS
integration awaits its API/authentication contract; native Bedrock is not yet
implemented.
