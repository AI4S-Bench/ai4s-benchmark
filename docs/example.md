# Complete example: AMR Poisson task fixture

The repository includes
[`amr-poisson-contribution-example`](https://github.com/AI4S-Bench/ai4s-benchmark/tree/main/tasks/mathematical-sciences/applied-mathematics/amr-poisson-contribution-example).
It is a minimal **Harbor contribution fixture**: the instruction asks the
agent to write a specific marker, and the verifier checks it. It demonstrates
the packaging and validation workflow, not a scientific AMR Poisson problem.

## Files

```text
tasks/mathematical-sciences/applied-mathematics/amr-poisson-contribution-example/
├── task.toml
├── instruction.md
├── environment/Dockerfile
├── solution/solve.sh
└── tests/test.sh
```

`task.toml` declares `[task].name = "ai4sbench/amr-poisson-contribution-example"`.
`instruction.md` specifies the output. The Dockerfile provides the runtime,
`solution/solve.sh` is the Oracle, and `tests/test.sh` writes `1` or `0` to
`/logs/verifier/reward.txt` after checking the output.

## Run it

Set up the pinned Harbor runtime as described in
[`bench/README.md`](https://github.com/AI4S-Bench/ai4s-benchmark/blob/main/bench/README.md).
From the benchmark repository root, run:

```bash
harbor run -p tasks/mathematical-sciences/applied-mathematics/amr-poisson-contribution-example -a oracle -e docker
harbor run -p tasks/mathematical-sciences/applied-mathematics/amr-poisson-contribution-example -a nop -e docker
```

The Oracle run should report reward `1.0`; the no-op run should report `0.0`.
This positive and negative check confirms that the verifier discriminates
between the intended solution and no solution.

## Describe your PR

For a **new** task, include the URL of its human-approved GitHub Discussion.
Use this outline, replacing the placeholder with the real approved proposal:

```text
Summary: Add <task name> with instructions, environment, Oracle, and verifier.
Approved proposal: https://github.com/AI4S-Bench/ai4s-benchmark/discussions/<number>
Validation: harbor run -p <task path> -a oracle -e docker → reward 1.0
            harbor run -p <task path> -a nop -e docker → reward 0.0
```

The [PR that repaired this fixture](https://github.com/AI4S-Bench/ai4s-benchmark/pull/27)
is a **maintenance** example. An existing-task repair does not need a new
proposal Discussion. It cannot stand in for a newly approved research task.
