# Contribute a new task

Submit a new Harbor task only after its proposal receives an **approved human
review**. The [proposal guide](submit-proposal.md) explains how to create the
Discussion. Include that Discussion URL in your PR description. AI review
alone is not approval.

## Build the task

Place a task under `tasks/<domain>/<field>/<task-name>/`. Follow
[CONTRIBUTING.md](https://github.com/AI4S-Bench/ai4s-benchmark/blob/main/CONTRIBUTING.md)
and include at least:

| File | Purpose |
| --- | --- |
| `task.toml` | Harbor task metadata: a `[metadata]` table (required by CI) and `[task].name` |
| `instruction.md` | Instructions visible to the agent |
| `environment/Dockerfile` | Reproducible execution environment |
| `solution/solve.sh` | Oracle solution |
| `tests/test.sh` | Verifier that writes `/logs/verifier/reward.txt` |

Use an identifier such as `ai4sbench/my-task` for `[task].name`. Make shell
scripts executable and use LF line endings. The verifier should emit a
numeric reward; demonstrate that the Oracle succeeds and a no-op agent does
not. See the [complete example](example.md).

## Validate and open the PR

Install the pinned runtime described in
[bench/README.md](https://github.com/AI4S-Bench/ai4s-benchmark/blob/main/bench/README.md),
then run Harbor from the repository root:

```bash
harbor run -p tasks/<domain>/<field>/<task-name> -a oracle -e docker
harbor run -p tasks/<domain>/<field>/<task-name> -a nop -e docker
```

Open a PR against `AI4S-Bench/ai4s-benchmark` with a summary of the task,
the **human-approved proposal Discussion URL**, the validation commands,
and the observed rewards. CI checks the directory structure, the `[metadata]`
table in `task.toml`, and the Discussion link format. Maintainers verify the
proposal's actual human approval and review the task behavior.

If your PR only repairs an existing task, say so in its description. A
maintenance PR does not require a new proposal link, but should explain the
change and show the relevant validation result.
