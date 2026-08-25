# ai4sbench benchmark repository

`ai4sbench.toml` is the source of truth for the released Harbor runtime, upstream
task commit, task path, validation matrix, and portable resource requirements.
Harbor task directories remain native Harbor tasks; the control panel treats a
task as the immutable tuple `(repo_url, commit, path)`.

Harbor itself is never executed from the source checkout. Install the pinned
PyPI wheel in WSL with source builds and persistent download caching disabled:

```bash
uv tool install --no-build --no-cache --python 3.12 "harbor==0.20.0"
```

The runner fails closed unless `harbor --version` reports the pinned release.
It also rejects a restricted-network task when the local Linux kernel explicitly
lacks `CONFIG_NFT_FIB_INET`. Microsoft WSL kernel `6.6.87.2` has `nft_fib` but
not `NFT_FIB_INET`, so loading `nft_fib_ipv4` is insufficient. Run this task on
an EC2/Linux kernel with `CONFIG_NFT_FIB_INET=y|m`; do not silently change its
verifier from `no-network` to `public`.

For WSL diagnosis only, a copied task with verifier networking changed to
`public` and Windows CRLF shell scripts normalized to LF completed one real
oracle trial with reward `1.0`; all 12 verifier tests passed in 29.85 seconds
and the Harbor job completed in about 73 seconds. The evidence is under
`results/public-network-diagnostic/oracle-public-wsl-lf`. This proves the local
execution chain, but it is not a security-equivalent benchmark result because
the verifier had outbound network access.

The first tracked task is Terminal-Bench Science's
`amr-poisson-optimize`, pinned to the latest commit observed on 2026-08-21. It
is deliberately a real benchmark task, not a hello-world fixture.

## Repository layout

```text
bench/
  ai4sbench.toml       catalog, pins, task resources, validation matrix
  run_matrix.py        fail-closed preflight and reproducible Harbor runner
references/            shallow upstream checkouts; ignored by git
results/               Harbor jobs and matrix summaries; ignored by git
```

## Commands

```powershell
cd benchmark-repository
uv run --no-project --python 3.12 bench/run_matrix.py preflight
uv run --no-project --python 3.12 bench/run_matrix.py run --phase oracle
uv run --no-project --python 3.12 bench/run_matrix.py run --phase all
```

`run --phase all` executes five oracle attempts, one `nop` negative control,
and three Codex attempts. It refuses to start if Docker, Harbor, the pinned task,
free disk, or Codex authentication is unavailable. To use Codex subscription
authentication without exporting an API key, set `CODEX_FORCE_AUTH_JSON=1` and
let Harbor copy the local `~/.codex/auth.json` into the isolated agent container.

The upstream task is not copied into this repository. The pin and path are
recorded in the manifest and the runner executes the sparse checkout under
`references/terminal-bench-science`. This keeps upstream provenance intact and
avoids silently diverging from its verifier.
