from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from scripts import validate_task

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_task.py"
EXAMPLE_TASK = ROOT / "tasks" / "mathematical-sciences" / "applied-mathematics" / "amr-poisson-contribution-example"
DISCUSSION = "Approved: https://github.com/example/repo/discussions/1"


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


def init_repository(repository: Path) -> str:
    run(["git", "init", "-b", "main"], repository)
    run(["git", "config", "user.email", "test@example.test"], repository)
    run(["git", "config", "user.name", "Validator test"], repository)
    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
    return commit_all(repository, "initial fixture")


def validate(repository: Path, base: str, head: str, body: str = DISCUSSION) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", base, "--head", head],
        cwd=repository,
        text=True,
        capture_output=True,
        env={**os.environ, "GITHUB_REPOSITORY": "example/repo", "PR_BODY": body},
        check=False,
    )


def test_task_validator_requires_discussion_and_accepts_terminal_bench_science_shape(tmp_path: Path) -> None:
    base = init_repository(tmp_path)
    run(["git", "checkout", "-b", "task/contribution"], tmp_path)
    task_files(tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / "sparse-assimilation")
    head = commit_all(tmp_path, "add task fixture")

    missing_discussion = validate(tmp_path, base, head, body="No proposal link yet.")
    assert missing_discussion.returncode != 0
    assert "Discussion" in missing_discussion.stderr

    accepted = validate(tmp_path, base, head)
    assert accepted.returncode == 0, accepted.stderr
    assert "Validated 1 task contribution" in accepted.stdout


def test_discussion_link_must_point_at_this_repository(tmp_path: Path) -> None:
    base = init_repository(tmp_path)
    task_files(tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / "sparse-assimilation")
    head = commit_all(tmp_path, "add task fixture")

    assert validate(tmp_path, base, head, body="https://github.com/other/repo/discussions/1").returncode != 0
    assert validate(tmp_path, base, head, body="Link to /discussions/ follows.").returncode != 0


def test_task_toml_must_parse_and_name_a_harbor_package(tmp_path: Path) -> None:
    task_toml = tmp_path / "task.toml"

    task_toml.write_text("# [metadata]\nthis is = = not toml\n", encoding="utf-8")
    assert "invalid TOML" in validate_task.task_toml_errors(task_toml)[0]

    task_toml.write_text("[metadata]\n\n[task]\ndescription = 'no name'\n", encoding="utf-8")
    assert "[task].name" in validate_task.task_toml_errors(task_toml)[0]

    task_toml.write_text("[metadata]\n\n[task]\nname = 'ai4sbench/sparse-assimilation'\n", encoding="utf-8")
    assert validate_task.task_toml_errors(task_toml) == []


def test_repository_example_task_is_a_valid_harbor_task() -> None:
    assert validate_task.task_toml_errors(EXAMPLE_TASK / "task.toml") == []
    assert "/logs/verifier/reward.txt" in (EXAMPLE_TASK / "tests" / "test.sh").read_text(encoding="utf-8")


def test_files_directly_under_a_field_are_not_tasks(tmp_path: Path) -> None:
    base = init_repository(tmp_path)
    (tmp_path / "tasks" / "earth-sciences" / "ocean-sciences").mkdir(parents=True)
    (tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / ".gitkeep").write_text("", encoding="utf-8")
    head = commit_all(tmp_path, "add field placeholder")

    result = validate(tmp_path, base, head, body="")
    assert result.returncode == 0, result.stderr
    assert "No task directory changed" in result.stdout


def test_deleting_a_task_needs_no_validation(tmp_path: Path) -> None:
    init_repository(tmp_path)
    task_files(tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / "sparse-assimilation")
    base = commit_all(tmp_path, "add task fixture")
    shutil.rmtree(tmp_path / "tasks")
    head = commit_all(tmp_path, "remove task fixture")

    result = validate(tmp_path, base, head, body="")
    assert result.returncode == 0, result.stderr


def test_changes_merged_to_main_after_branching_are_not_attributed_to_the_pr(tmp_path: Path) -> None:
    init_repository(tmp_path)
    run(["git", "checkout", "-b", "task/contribution"], tmp_path)
    task_files(tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / "sparse-assimilation")
    head = commit_all(tmp_path, "add task fixture")
    run(["git", "checkout", "main"], tmp_path)
    broken = tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / "merged-elsewhere"
    task_files(broken)
    (broken / "task.toml").write_text("not = = toml\n", encoding="utf-8")
    base = commit_all(tmp_path, "unrelated task merged to main")
    # GitHub checks out the PR merged into main.
    run(["git", "checkout", "--detach", head], tmp_path)
    run(["git", "merge", "--no-edit", base], tmp_path)

    result = validate(tmp_path, base, head)
    assert result.returncode == 0, result.stderr
    assert "Validated 1 task contribution" in result.stdout
