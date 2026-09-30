# ai4sbench benchmark repository

This directory is the public, standalone Harbor task repository. Its layout is
intentionally compatible with the Terminal-Bench-Science contribution model:

```text
benchmark-repository/
├── .github/                 pull request template and task validation workflow
├── tasks/<domain>/<field>/  Harbor task directories
├── scripts/                 contribution validation
├── bench/                   pinned runtime and validation matrix
├── tests/                   public repository validation tests
└── CONTRIBUTING.md          public contributor protocol
```

It must not contain control-plane credentials, SQLite state, EC2 configuration,
or the operator dashboard. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for task
submission requirements and [`bench/README.md`](bench/README.md) for Harbor
validation.
