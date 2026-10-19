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
    # -z keeps non-ASCII paths unquoted; --no-renames also lists the task a file moved out of.
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", f"{base}...{head}"],
        check=True,
        capture_output=True,
        text=True,
    )
    roots: set[Path] = set()
    for name in result.stdout.split("\0"):
        path = Path(name)
        # A task file is tasks/<domain>/<field>/<task-slug>/...; files directly under <field>/ are not tasks.
        if path.parts[:1] == ("tasks",) and len(path.parts) >= 5:
            roots.add(Path(*path.parts[:4]))
    return roots


def is_new_task(merge_base: str, root: Path) -> bool:
    """A proposal is required for a new task, not a repair to an existing one."""
    task_config = f"{merge_base}:{(root / 'task.toml').as_posix()}"
    return subprocess.run(
        ["git", "cat-file", "-e", task_config], capture_output=True, check=False
    ).returncode != 0


def task_toml_errors(path: Path, *, task_root: Path | None = None, new_task: bool = False) -> list[str]:
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [f"{path}: invalid TOML: {exc}"]
    errors: list[str] = []
    metadata = config.get("metadata")
    if not isinstance(metadata, dict):
        errors.append(f"{path}: [metadata] is required")
    if new_task and task_root is not None:
        domain, field = task_root.parts[1:3]
        if domain not in NEW_TASK_DOMAINS:
            allowed = ", ".join(sorted(NEW_TASK_DOMAINS))
            errors.append(f"{task_root}: new tasks must use a supported primary-domain folder: {allowed}")
        if isinstance(metadata, dict):
            for key, expected in (("domain", domain), ("field", field)):
                if metadata.get(key) != expected:
                    errors.append(f"{path}: [metadata].{key} must equal the folder name {expected!r}")
    if "task" in config:
        task = config["task"]
        name = str(task.get("name", "")) if isinstance(task, dict) else ""
        if not HARBOR_TASK_NAME.match(name) or ".." in name:
            errors.append(f"{path}: [task].name must be an 'org/name' Harbor package name")
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
