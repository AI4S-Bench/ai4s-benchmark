# Contribute a new task

Submit a new Harbor task only after its proposal receives an **approved human
review**. The [proposal guide](submit-proposal.md) explains how to create the
Discussion. Include that Discussion URL in your PR description. AI review
alone is not approval.

## Build the task

Fork the [benchmark repository](https://github.com/AI4S-Bench/ai4s-benchmark),
then clone your fork and create a branch. Replace `YOUR_GITHUB_USERNAME` with
your GitHub account:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/ai4s-benchmark.git
cd ai4s-benchmark
git switch -c add-inverse-problems-task
```

Place a task under `tasks/<domain>/<task-slug>/`. The first domain in the
proposal is primary and determines `<domain>`. The proposal's research field
is descriptive metadata and does not add a path segment. Use one of these seven
values for the folder and `[metadata].domain`:

| Proposal domain | `<domain>` value |
| --- | --- |
| Materials Science | `materials-science` |
| Physics | `physics` |
| Chemistry | `chemistry` |
| Biology | `biology` |
| AI / ML | `ai-ml` |
| Applied Mathematics | `applied-mathematics` |
| Interdisciplinary | `interdisciplinary` |

You may retain the research field in `[metadata].field`. See the
[benchmark contribution rules](https://github.com/AI4S-Bench/ai4s-benchmark/blob/main/CONTRIBUTING.md#required-task-layout)
for the metadata requirements. Include at least:

| File | Purpose |
| --- | --- |
| `task.toml` | Harbor task metadata, including `[metadata].domain` and `[task].name` |
| `instruction.md` | Instructions visible to the agent |
| `environment/Dockerfile` | Reproducible execution environment |
| `solution/solve.sh` | Oracle solution |
| `tests/test.sh` | Verifier that writes `/logs/verifier/reward.txt` |

For instructions on writing these files, follow Harbor's
[Create a task tutorial](https://docs.harborframework.com/tutorials/create-a-task)
or the [Terminal-Bench Science contribution guide](https://github.com/harbor-framework/terminal-bench-science/blob/main/CONTRIBUTING.md).
Apply this benchmark's domain and metadata rules to their examples. Use an
identifier such as `ai4sbench/my-task` for `[task].name` and make shell
scripts executable. The verifier should emit a numeric reward; demonstrate
that the Oracle succeeds and a no-op agent does not. See the
[complete example](example.md).

For example, a new task in `tasks/physics/my-task/` includes:

```toml
[metadata]
domain = "physics"
field = "inverse-problems" # optional research description, not a path segment
```

The PR check requires `domain` to match the folder for new tasks. It also
requires `[task].name = "ai4sbench/my-task"` and a non-empty description.

## Validate and open the PR

Install the pinned Harbor release described in
[bench/README.md](https://github.com/AI4S-Bench/ai4s-benchmark/blob/main/bench/README.md)
in Linux or WSL, and ensure Docker is running:

```bash
uv tool install --no-build --no-cache --python 3.12 "harbor==0.20.0"
harbor --version
docker ps
```

From the repository root, run the Oracle and no-op checks for your task. The
Oracle should earn reward `1`; `nop` should earn `0`:

```bash
harbor run -p tasks/physics/my-task -a oracle -e docker
harbor run -p tasks/physics/my-task -a nop -e docker
```

Then try a real agent and model to gauge difficulty. For example, with the
model provider's credentials configured locally:

```bash
harbor run -p tasks/physics/my-task -a claude-code -m anthropic/claude-haiku-4-5 -e docker
```

See Harbor's [run command guide](https://docs.harborframework.com/jobs/run-a-job)
for other agents and models.

After adding your task files, push the branch and open the PR form with the
GitHub CLI installed and signed in:

```bash
git add tasks/physics/my-task/
git commit -m "Add inverse problems task"
git push -u origin add-inverse-problems-task
gh pr create --repo AI4S-Bench/ai4s-benchmark --base main --head YOUR_GITHUB_USERNAME:add-inverse-problems-task --web
```

Open a PR against `AI4S-Bench/ai4s-benchmark` with a summary of the task,
the **human-approved proposal Discussion URL**, the validation commands,
and the observed rewards. CI checks the directory structure and Discussion
link format. Maintainers verify the proposal's actual human approval and
review the task behavior.

If your PR only repairs an existing task, say so in its description. A
maintenance PR does not require a new proposal link, but should explain the
change and show the relevant validation result.
