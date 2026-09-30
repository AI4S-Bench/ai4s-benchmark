# Proposal reviewer provenance

Vendored from harbor-framework/terminal-bench-science at
`f55c14ea065243c8d094e02c0aa156d5fd22fdd4`:

- `ci_checks/rubric_review.py`
- `rubrics/task-proposal.md`
- `rubrics/author-fit.md`

Apache-2.0 license: [TBS-LICENSE](TBS-LICENSE).
The rubrics are adapted for AI4S-Bench. Both name the correct benchmark;
`task-proposal.md` describes the portal/Discussion, human approval and Harbor PR
process, and removes upstream-specific claims about a target model success rate,
internet access, a deployed process grader and an included task catalog. The
seven review criteria and output labels remain intact. Modified files carry
adaptation notices; the upstream license remains unchanged.

AI4S changes to the runner are limited to disabling
image downloads for this text-only integration, reading proposal/rubric files as
UTF-8, bounding input bytes, setting SDK timeouts, configuring the completion-token
parameter, and rejecting empty/truncated output. Both upstream passes
and result extraction remain intact. The adjacent script lock pins dependencies.

The workflow preserves discussion-created, maintainer `/review`, and manual
Discussion-number triggers. Backend publication replaces all direct GitHub and
Discord writes. Model/provider configuration uses JSON to avoid a yq dependency.

The temporary free test model is `qwen/qwen3.8-27b:free`; the original planned
`z-ai/glm-5.2:free` was absent from the public OpenRouter catalog when rechecked
on 2026-09-30 UTC. Model selection is configured independently of the rubrics.
The helper also supports explicitly configured OpenAI-compatible endpoints with
the generic `LLM_API_KEY` secret. The free-only policy is optional. Sponsor
integration awaits confirmation of its API and authentication requirements.
