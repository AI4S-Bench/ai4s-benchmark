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

`tests/test.sh` must write the trial's reward (for example `1` or `0`) to
`/logs/verifier/reward.txt`, or a JSON object to `/logs/verifier/reward.json`.
Harbor ignores the script's exit code and errors the trial if neither file exists.
If `task.toml` has a `[task]` table, its `name` must be an `org/name` package
name such as `ai4sbench/<task-slug>`; Harbor refuses to load the task otherwise.

The PR check validates the layout, that `task.toml` is valid TOML with a
`[metadata]` table and (if present) an `org/name` `[task].name`, and that the
PR body links a Discussion in this repository. It does not replace executing
the oracle and verifier.

## Reference example

The pinned reference task is Terminal-Bench Science's real
[`amr-poisson-optimize`](https://github.com/harbor-framework/terminal-bench-science/tree/main/tasks/mathematical-sciences/applied-mathematics/amr-poisson-optimize)
task: a Docker environment, oracle solution, and independent verifier for AMR
Poisson optimization. Its immutable upstream revision is recorded in
[`bench/ai4sbench.toml`](bench/ai4sbench.toml).
