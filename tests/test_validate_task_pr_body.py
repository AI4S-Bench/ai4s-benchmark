from __future__ import annotations

from pathlib import Path

from tests.test_validate_task import commit_all, init_repository, task_files, validate

LINK = "https://github.com/example/repo/discussions/1"


def test_discussion_link_hidden_in_an_html_comment_does_not_count(tmp_path: Path) -> None:
    base = init_repository(tmp_path)
    task_files(tmp_path / "tasks" / "earth-sciences" / "ocean-sciences" / "sparse-assimilation")
    head = commit_all(tmp_path, "add task fixture")

    hidden = f"## Task proposal (new tasks only)\n\n<!-- Link the human-approved GitHub Discussion.\n{LINK} -->\n"
    result = validate(tmp_path, base, head, body=hidden)
    assert result.returncode != 0
    assert "Discussion" in result.stderr

    visible = f"## Task proposal (new tasks only)\n\n<!-- Link the human-approved GitHub Discussion. -->\n{LINK}\n"
    result = validate(tmp_path, base, head, body=visible)
    assert result.returncode == 0, result.stderr
