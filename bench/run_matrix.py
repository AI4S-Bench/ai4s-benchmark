from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import tomllib

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "bench" / "ai4sbench.toml"
RESULTS_DIR = ROOT / "results"


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open("rb") as stream:
        return tomllib.load(stream)


def harbor_command() -> list[str] | None:
    executable = shutil.which("harbor")
    return [executable] if executable else None


def task_path(manifest: dict[str, Any]) -> Path:
    task = manifest["tasks"][0]
    return ROOT / "references" / "terminal-bench-science" / task["path"]


def codex_auth_path() -> Path:
    configured = os.getenv("CODEX_AUTH_JSON_PATH")
    return Path(configured).expanduser() if configured else Path.home() / ".codex" / "auth.json"


def run_probe(command: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (completed.stdout or completed.stderr).strip()
    return completed.returncode == 0, output[-500:]


def nft_fib_inet_enabled(config: str) -> bool:
    return "CONFIG_NFT_FIB_INET=y" in config or "CONFIG_NFT_FIB_INET=m" in config


def contains_crlf(content: bytes) -> bool:
    return b"\r\n" in content


def shell_scripts_use_lf(task: Path) -> tuple[bool, str]:
    crlf_scripts = [path.relative_to(task) for path in task.rglob("*.sh") if contains_crlf(path.read_bytes())]
    if crlf_scripts:
        names = ", ".join(str(path) for path in crlf_scripts[:5])
        return False, f"CRLF shell scripts cannot execute in Linux containers: {names}"
    return True, "shell scripts use Linux LF line endings"


def docker_network_policy_support(task: Path) -> tuple[bool, str]:
    task_config = (task / "task.toml").read_text(encoding="utf-8")
    restricted = 'network_mode = "no-network"' in task_config or 'network_mode = "allowlist"' in task_config
    if not restricted:
        return True, "task does not require restricted Docker egress"
    if not sys.platform.startswith("linux"):
        return True, "daemon kernel capability is delegated to Harbor"

    candidates = (Path("/proc/config.gz"), Path(f"/boot/config-{os.uname().release}"))
    for config_path in candidates:
        if not config_path.is_file():
            continue
        if config_path.suffix == ".gz":
            with gzip.open(config_path, "rt", encoding="utf-8") as stream:
                config = stream.read()
        else:
            config = config_path.read_text(encoding="utf-8")
        supported = nft_fib_inet_enabled(config)
        detail = f"{config_path}: CONFIG_NFT_FIB_INET=" + ("enabled" if supported else "missing")
        return supported, detail
    return True, "kernel config unavailable; Harbor must validate the Docker daemon"


def preflight(manifest: dict[str, Any], require_codex: bool = True) -> dict[str, Any]:
    docker = shutil.which("docker")
    docker_ok, docker_detail = (False, "docker executable not found")
    if docker:
        docker_ok, docker_detail = run_probe([docker, "info", "--format", "{{.ServerVersion}}"])

    harbor = harbor_command()
    expected_harbor = manifest["runtime"]["harbor"]["version"]
    harbor_ok, harbor_detail = (False, "prebuilt Harbor CLI is not installed")
    if harbor:
        version_ok, version_output = run_probe([*harbor, "--version"])
        harbor_ok = version_ok and expected_harbor in version_output
        harbor_detail = (
            version_output
            if harbor_ok
            else f"expected prebuilt harbor=={expected_harbor}; got: {version_output or 'unknown'}"
        )

    task = task_path(manifest)
    required_task_files = (Path("task.toml"), Path("instruction.md"), Path("environment/Dockerfile"))
    task_ok = all((task / name).is_file() for name in required_task_files)
    line_endings_ok, line_endings_detail = (
        shell_scripts_use_lf(task) if task_ok else (False, "task configuration unavailable")
    )
    network_ok, network_detail = (
        docker_network_policy_support(task) if task_ok else (False, "task configuration unavailable")
    )

    free_gb = shutil.disk_usage(ROOT).free / 1024**3
    auth_json = codex_auth_path()
    codex_auth = bool(os.getenv("OPENAI_API_KEY")) or auth_json.is_file()

    checks = {
        "docker": {"ok": docker_ok, "detail": docker_detail},
        "harbor": {"ok": harbor_ok, "detail": harbor_detail},
        "pinned_task": {"ok": task_ok, "detail": str(task)},
        "task_line_endings": {"ok": line_endings_ok, "detail": line_endings_detail},
        "docker_network_policy": {"ok": network_ok, "detail": network_detail},
        "disk": {"ok": free_gb >= 15, "detail": f"{free_gb:.1f} GiB free; 15 GiB required"},
        "codex_auth": {
            "ok": codex_auth or not require_codex,
            "detail": f"OPENAI_API_KEY or {auth_json}" if codex_auth else f"missing: {auth_json}",
        },
    }
    return {"ok": all(item["ok"] for item in checks.values()), "checks": checks}


def selected_runs(manifest: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    runs = manifest["matrix"]["runs"]
    if phase == "all":
        return runs
    return [item for item in runs if item["name"] == phase]


def execute(manifest: dict[str, Any], phase: str) -> int:
    runs = selected_runs(manifest, phase)
    if not runs:
        raise ValueError(f"Unknown phase: {phase}")

    require_codex = any(item["agent"] == "codex" for item in runs)
    report = preflight(manifest, require_codex=require_codex)
    if not report["ok"]:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2

    harbor = harbor_command()
    if harbor is None:
        return 2
    if require_codex and not os.getenv("OPENAI_API_KEY") and not os.getenv("CODEX_AUTH_JSON_PATH"):
        os.environ.setdefault("CODEX_FORCE_AUTH_JSON", "1")

    started = datetime.now(UTC)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    matrix_dir = RESULTS_DIR / f"matrix-{stamp}"
    matrix_dir.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []

    for item in runs:
        job_name = f"{item['name']}-{stamp}"
        command = [
            *harbor,
            "run",
            "-p",
            str(task_path(manifest)),
            "-a",
            item["agent"],
            "-k",
            str(item["attempts"]),
            "-n",
            str(manifest["matrix"]["n_concurrent"]),
            "-e",
            manifest["matrix"]["environment"],
            "--job-name",
            job_name,
            "--jobs-dir",
            str(matrix_dir),
        ]
        if item.get("model"):
            command.extend(["-m", item["model"]])
        print(f"Running {item['name']}: {item['attempts']} attempt(s)", flush=True)
        completed = subprocess.run(command, cwd=ROOT, check=False)
        records.append(
            {
                "name": item["name"],
                "agent": item["agent"],
                "model": item.get("model"),
                "attempts": item["attempts"],
                "exit_code": completed.returncode,
                "job_dir": str(matrix_dir / job_name),
            }
        )
        if completed.returncode != 0:
            break

    summary = {
        "schema_version": "1.0",
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "task": manifest["tasks"][0],
        "upstreams": manifest["upstreams"],
        "runtime": manifest["runtime"],
        "runs": records,
        "passed": len(records) == len(runs) and all(item["exit_code"] == 0 for item in records),
    }
    (matrix_dir / "matrix-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the pinned ai4sbench Harbor matrix")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("preflight")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--phase", default="all", choices=("all", "oracle", "negative-control", "codex"))
    args = parser.parse_args()
    manifest = load_manifest()
    if args.command == "preflight":
        report = preflight(manifest)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["ok"] else 2
    return execute(manifest, args.phase)


if __name__ == "__main__":
    sys.exit(main())
