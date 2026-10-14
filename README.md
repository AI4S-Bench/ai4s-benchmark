# AI4S-Bench

AI4S-Bench is an open benchmark for evaluating agents on research tasks in
AI for Science. This repository contains the public, runnable Harbor tasks and
the contribution rules. Explore the project at [ai4sbench.org](https://ai4sbench.org)
and browse the [contributor documentation](https://dashboard.ai4sbench.org/document/).

## Participate

| If you want to… | Start here |
| --- | --- |
| Propose a research task | [Submit a proposal](https://dashboard.ai4sbench.org/document/submit-proposal/) |
| Become a reviewer | [Apply to review](https://dashboard.ai4sbench.org/document/apply-reviewer/) |
| Review a proposal | [Reviewer guide](https://dashboard.ai4sbench.org/document/review-proposal/) |
| Contribute a runnable task | [Task contribution guide](https://dashboard.ai4sbench.org/document/contribute-task/) |

A proposal begins as a GitHub Discussion through the
[proposal form](https://ai4sbench.org/submit/). AI review offers advice; a
human reviewer must approve the proposal before a new task PR is submitted.
The [task board](https://ai4sbench.org/tasks/) shows proposals and reviews.

## Try a task

The AMR Poisson contribution example is a small Harbor layout fixture. It
demonstrates the task files, an Oracle solution, and a verifier; it is not a
scientific AMR benchmark task. From a checkout of this repository with Harbor
installed, run:

```bash
harbor run -p tasks/mathematical-sciences/applied-mathematics/amr-poisson-contribution-example -a oracle -e docker
harbor run -p tasks/mathematical-sciences/applied-mathematics/amr-poisson-contribution-example -a nop -e docker
```

The Oracle should earn reward `1.0` and the no-op agent reward `0.0`.
See the [full example](https://dashboard.ai4sbench.org/document/example/)
for the file layout, PR description, and validation commands.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. New tasks need a
link to a **human-approved** proposal Discussion. Repairs to existing tasks
do not require a new proposal. CI checks the contribution structure and the
link format; maintainers verify the human approval decision.

## Repository layout

| Path | Purpose |
| --- | --- |
| `tasks/<domain>/<field>/<task-slug>/` | Public Harbor tasks; new task domains follow the [seven proposal choices](CONTRIBUTING.md#required-task-layout) |
| `bench/` | Pinned runtime and validation matrix |
| `scripts/` and `tests/` | Contribution checks |
| `docs/` and `mkdocs.yml` | Source for the [documentation site](https://dashboard.ai4sbench.org/document/) |

See [bench/README.md](bench/README.md) for the Harbor validation setup.
