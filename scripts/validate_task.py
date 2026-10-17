from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

import tomllib

REQUIRED_FILES = (
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/test.sh",
)
# Harbor refuses to load a task whose [task].name is not "org/name".
HARBOR_TASK_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9][a-zA-Z0-9._-]*$")
TASK_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NEW_TASK_DOMAINS = frozenset(
    {
        "materials-science",
        "physics",
        "chemistry",
        "biology",
        "ai-ml",
        "applied-mathematics",
        "interdisciplinary",
    }
)


def changed_task_roots(base: str, head: str) -> set[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"], check=True, capture_output=True, text=True
    )
    roots: set[Path] = set()
    for name in result.stdout.splitlines():
        path = Path(name)
        # A task file is tasks/<domain>/<task-slug>/...; files directly under <domain>/ are not tasks.
        if path.parts[:1] == ("tasks",) and len(path.parts) >= 4:
            roots.add(Path(*path.parts[:3]))
    return roots


def is_new_task(merge_base: str, root: Path) -> bool:
    """A proposal is required for a new task, not a repair or directory migration."""
    task_config = f"{merge_base}:{(root / 'task.toml').as_posix()}"
    if subprocess.run(
        ["git", "cat-file", "-e", task_config], capture_output=True, check=False
    ).returncode == 0:
        return False
    # A move from the former domain/field/slug layout retains the task's slug.
    try:
        current_name = tomllib.loads((root / "task.toml").read_text(encoding="utf-8")).get("task", {}).get("name")
    except (OSError, tomllib.TOMLDecodeError, AttributeError):
        return True
    if not isinstance(current_name, str) or not current_name:
        return True
    previous = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", merge_base, "--", "tasks"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    for path in previous:
        if not path.endswith(f"/{root.name}/task.toml") or Path(path).is_file():
            continue
        old_text = subprocess.run(
            ["git", "show", f"{merge_base}:{path}"], check=True, capture_output=True, text=True,
        ).stdout
        try:
            old_name = tomllib.loads(old_text).get("task", {}).get("name")
        except (tomllib.TOMLDecodeError, AttributeError):
            continue
        if old_name == current_name:
            return False
    return True


def task_toml_errors(path: Path, *, task_root: Path | None = None, new_task: bool = False) -> list[str]:
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"{path}: invalid TOML: {exc}"]
    errors: list[str] = []
    metadata = config.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{path}: [metadata] is required")
    if task_root is not None:
        if len(task_root.parts) != 3 or task_root.parts[0] != "tasks":
            errors.append(f"{task_root}: task path must be tasks/<domain>/<task-slug>")
        if not TASK_SLUG.fullmatch(task_root.name):
            errors.append(f"{task_root}: task slug must use lowercase letters, digits, and single hyphens")
    if new_task and task_root is not None and len(task_root.parts) == 3:
        domain = task_root.parts[1]
        if domain not in NEW_TASK_DOMAINS:
            allowed = ", ".join(sorted(NEW_TASK_DOMAINS))
            errors.append(f"{task_root}: new tasks must use a supported primary-domain folder: {allowed}")
        if isinstance(metadata, dict):
            if metadata.get("domain") != domain:
                errors.append(f"{path}: [metadata].domain must equal the folder name {domain!r}")
    if new_task and "task" not in config:
        errors.append(f"{path}: new tasks require a [task] table")
    if "task" in config:
        task = config["task"]
        name = str(task.get("name", "")) if isinstance(task, dict) else ""
        if not HARBOR_TASK_NAME.match(name) or ".." in name:
            errors.append(f"{path}: [task].name must be an 'org/name' Harbor package name")
        if new_task and task_root is not None:
            expected_name = f"ai4sbench/{task_root.name}"
            if name != expected_name:
                errors.append(f"{path}: [task].name must equal {expected_name!r}")
            if not isinstance(task, dict) or not isinstance(task.get("description"), str) or not task["description"].strip():
                errors.append(f"{path}: new tasks require a non-empty [task].description")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Terminal-Bench-Science-style task PR")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    # Deleted or renamed-away task directories no longer exist and need no validation.
    task_roots = {root for root in changed_task_roots(args.base, args.head) if root.is_dir()}
    if not task_roots:
        print("No task directory changed; structural task checks are not required.")
        return
    merge_base = subprocess.run(
        ["git", "merge-base", args.base, args.head], check=True, capture_output=True, text=True
    ).stdout.strip()
    new_tasks = {root for root in task_roots if is_new_task(merge_base, root)}
    if new_tasks:
        body = os.environ.get("PR_BODY", "")
        repository = os.environ.get("GITHUB_REPOSITORY", "AI4S-Bench/ai4s-benchmark")
        discussion = re.compile(
            rf"https://github\.com/{re.escape(repository)}/discussions/\d+", re.IGNORECASE
        )
        if not discussion.search(body):
            raise SystemExit(
                "New task PR body must link its approved Task Proposal Discussion: "
                f"https://github.com/{repository}/discussions/<number>"
            )
    failures: list[str] = []
    for root in sorted(task_roots):
        missing = [str(root / file) for file in REQUIRED_FILES if not (root / file).is_file()]
        if missing:
            failures.append(f"{root}: missing required files: {', '.join(missing)}")
        if (root / "task.toml").is_file():
            failures.extend(
                task_toml_errors(root / "task.toml", task_root=root, new_task=root in new_tasks)
            )
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Validated {len(task_roots)} task contribution(s), including {len(new_tasks)} new task(s).")


if __name__ == "__main__":
    main()
