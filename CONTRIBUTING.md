# Contributing a scientific benchmark task

ai4sbench follows the Terminal-Bench Science contribution sequence:

1. Sign in to the contribution portal and submit the short scientific proposal form.
2. The portal opens a GitHub Discussion in **Task Proposals**. A maintainer reviews the scope, provenance and reproducibility claim.
3. After approval, open a PR that links the Discussion and adds one Harbor task.

## Required task layout

```text
tasks/<domain>/<field>/<task-slug>/
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
`<domain>`. The research field within that primary domain is free text in the
proposal and determines the `<field>` slug. For example, `Physics` with
`Inverse Problems` goes under
`tasks/physics/inverse-problems/<task-slug>/`.

For a new task, set `[metadata].domain` and `[metadata].field` in `task.toml`
to those two folder names. Do not use the older combined `category` key for
new-task classification. The PR check enforces the domain list and both
metadata-to-folder matches for **new tasks**. Existing task paths, including
the older `mathematical-sciences/applied-mathematics` example, are retained;
repairs to them do not have to change their directory or metadata.

`tests/test.sh` must write the trial's reward (for example `1` or `0`) to
`/logs/verifier/reward.txt`, or a JSON object to `/logs/verifier/reward.json`.
Harbor ignores the script's exit code and errors the trial if neither file exists.
If `task.toml` has a `[task]` table, its `name` must be an `org/name` package
name such as `ai4sbench/<task-slug>`; Harbor refuses to load the task otherwise.

The PR check validates the layout and that `task.toml` is valid TOML with a
`[metadata]` table and (if present) an `org/name` `[task].name`. For a **new**
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
