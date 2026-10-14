# Contribute a new task

Submit a new Harbor task only after its proposal receives an **approved human
review**. The [proposal guide](submit-proposal.md) explains how to create the
Discussion. Include that Discussion URL in your PR description. AI review
alone is not approval.

## Build the task

Place a task under `tasks/<domain>/<field>/<task-slug>/`. The first domain in
the proposal is primary and determines `<domain>`; the proposal's research
field within it determines `<field>`. See the [seven supported domain slugs
and metadata rules](https://github.com/AI4S-Bench/ai4s-benchmark/blob/main/CONTRIBUTING.md#required-task-layout).
Follow that guide and include at least:

| File | Purpose |
| --- | --- |
| `task.toml` | Harbor task metadata, including `[metadata].domain`, `[metadata].field`, and `[task].name` |
| `instruction.md` | Instructions visible to the agent |
| `environment/Dockerfile` | Reproducible execution environment |
| `solution/solve.sh` | Oracle solution |
| `tests/test.sh` | Verifier that writes `/logs/verifier/reward.txt` |

Use an identifier such as `ai4sbench/my-task` for `[task].name`. Make shell
scripts executable and use LF line endings. The verifier should emit a
numeric reward; demonstrate that the Oracle succeeds and a no-op agent does
not. See the [complete example](example.md).

For example, a new task in `tasks/physics/inverse-problems/my-task/` includes:

```toml
[metadata]
domain = "physics"
field = "inverse-problems"
```

The PR check requires these two keys to match the folders for new tasks.
Existing task repairs keep their current paths.

## Validate and open the PR

Install the pinned runtime described in
[bench/README.md](https://github.com/AI4S-Bench/ai4s-benchmark/blob/main/bench/README.md),
then run Harbor from the repository root:

```bash
harbor run -p tasks/<domain>/<field>/<task-slug> -a oracle -e docker
harbor run -p tasks/<domain>/<field>/<task-slug> -a nop -e docker
```

Open a PR against `AI4S-Bench/ai4s-benchmark` with a summary of the task,
the **human-approved proposal Discussion URL**, the validation commands,
and the observed rewards. CI checks the directory structure and Discussion
link format. Maintainers verify the proposal's actual human approval and
review the task behavior.

If your PR only repairs an existing task, say so in its description. A
maintenance PR does not require a new proposal link, but should explain the
change and show the relevant validation result.
