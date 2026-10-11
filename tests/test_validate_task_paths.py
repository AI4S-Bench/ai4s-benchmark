from __future__ import annotations

from pathlib import Path

from tests.test_validate_task import commit_all, init_repository, run, task_files, validate


def test_task_with_a_non_ascii_slug_is_validated(tmp_path: Path) -> None:
    base = init_repository(tmp_path)
    root = tmp_path / "tasks" / "physical-sciences" / "optics" / "schrödinger-lens"
    root.mkdir(parents=True)
    (root / "instruction.md").write_text("Solve the scientific task.\n", encoding="utf-8")
    head = commit_all(tmp_path, "add incomplete task with a non-ASCII slug")

    result = validate(tmp_path, base, head)
    assert result.returncode != 0
    assert "schrödinger-lens: missing required files" in result.stderr


def test_moving_a_file_out_of_a_task_validates_the_task_it_left(tmp_path: Path) -> None:
    init_repository(tmp_path)
    field = Path("tasks", "earth-sciences", "ocean-sciences")
    task_files(tmp_path / field / "task-a")
    task_files(tmp_path / field / "task-b")
    base = commit_all(tmp_path, "existing tasks")
    moved_from = field / "task-a" / "tests" / "test.sh"
    run(["git", "mv", str(moved_from), str(field / "task-b" / "tests" / "helper.sh")], tmp_path)
    head = commit_all(tmp_path, "move a verifier file between tasks")

    result = validate(tmp_path, base, head, body="Maintenance PR without a proposal")
    assert result.returncode != 0
    assert "task-a: missing required files" in result.stderr
