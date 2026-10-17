# Contributing a scientific benchmark task

ai4sbench follows the Terminal-Bench Science contribution sequence:

1. Sign in to the contribution portal and submit the short scientific proposal form.
2. The portal opens a GitHub Discussion in **Task Proposals**. A maintainer reviews the scope, provenance and reproducibility claim.
3. After approval, open a PR that links the Discussion and adds one Harbor task.

## Required task layout

```text
tasks/<domain>/<task-slug>/
├── task.toml
├── instruction.md
├── environment/Dockerfile
├── solution/solve.sh
└── tests/test.sh
```

The proposal form offers seven domains for new tasks:

| Proposal domain | `<domain>` folder |
| --- | --- |
| Materials Science | `materials-science` |
| Physics | `physics` |
| Chemistry | `chemistry` |
| Biology | `biology` |
| AI / ML | `ai-ml` |
| Applied Mathematics | `applied-mathematics` |
| Interdisciplinary | `interdisciplinary` |

A proposal may select multiple domains; the **first** is primary and determines
`<domain>`. The research field remains descriptive proposal metadata and does
not add a path segment. For example, a Physics proposal goes under
`tasks/physics/<task-slug>/`.

For a new task, set `[metadata].domain` in `task.toml` to the domain folder.
`[metadata].field` may describe the research field but is not part of the path.
Do not use the older combined `category` key for new-task classification.
The PR check enforces the domain list and metadata-to-folder match for new tasks.
The contribution example now lives at
`tasks/applied-mathematics/amr-poisson-contribution-example/`.

`tests/test.sh` must write the trial's reward (for example `1` or `0`) to
`/logs/verifier/reward.txt`, or a JSON object to `/logs/verifier/reward.json`.
Harbor ignores the script's exit code and errors the trial if neither file exists.
New tasks must define `[task].name = "ai4sbench/<task-slug>"` and a non-empty
`[task].description`. Existing tasks with a `[task]` table keep a valid
`org/name` Harbor package name.

The PR check validates the layout and that `task.toml` is valid TOML with a
`[metadata]` table and Harbor task identity fields. For a **new**
task, the PR body must link an approved Discussion in this repository. Repairs
to an existing task do not require a new proposal, but should explain the
problem and the evidence for the fix. The check verifies the link's format;
maintainers confirm the human approval. It does not replace executing the
oracle and verifier.

## Reference example

The pinned reference task is Terminal-Bench Science's real
[`amr-poisson-optimize`](https://github.com/harbor-framework/terminal-bench-science/tree/main/tasks/mathematical-sciences/applied-mathematics/amr-poisson-optimize)
task: a Docker environment, oracle solution, and independent verifier for AMR
Poisson optimization. Its immutable upstream revision is recorded in
[`bench/ai4sbench.toml`](bench/ai4sbench.toml).
