from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_task.py"


def run(command: list[str], cwd: Path, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=True, **kwargs)


def commit_all(repository: Path, message: str) -> str:
    run(["git", "add", "."], repository)
    run(["git", "commit", "-m", message], repository)
    return run(["git", "rev-parse", "HEAD"], repository).stdout.strip()


def task_files(root: Path) -> None:
    (root / "environment").mkdir(parents=True)
    (root / "solution").mkdir()
    (root / "tests").mkdir()
    (root / "task.toml").write_text("[metadata]\nname = 'test-task'\n", encoding="utf-8")
    (root / "instruction.md").write_text("Solve the scientific task.\n", encoding="utf-8")
    (root / "environment" / "Dockerfile").write_text("FROM alpine:3.20\n", encoding="utf-8")
    (root / "solution" / "solve.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (root / "tests" / "test.sh").write_text("#!/bin/sh\n", encoding="utf-8")


def test_task_validator_requires_discussion_and_accepts_terminal_bench_science_shape(tmp_path: Path) -> None:
    run(["git", "init", "-b", "main"], tmp_path)
    run(["git", "config", "user.email", "test@example.test"], tmp_path)
    run(["git", "config", "user.name", "Validator test"], tmp_path)
    (tmp_path / "README.md").write_text("fixture\n", encoding="utf-8")
    base = commit_all(tmp_path, "initial fixture")
    run(["git", "checkout", "-b", "task/contribution"], tmp_path)
    task_files(tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / "sparse-assimilation")
    head = commit_all(tmp_path, "add task fixture")

    missing_discussion = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", base, "--head", head],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env={**os.environ, "PR_BODY": "No proposal link yet."},
        check=False,
    )
    assert missing_discussion.returncode != 0
    assert "Discussion" in missing_discussion.stderr

    accepted = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", base, "--head", head],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env={**os.environ, "PR_BODY": "Approved: https://github.com/example/repo/discussions/1"},
        check=False,
    )
    assert accepted.returncode == 0, accepted.stderr
    assert "Validated 1 task contribution" in accepted.stdout
