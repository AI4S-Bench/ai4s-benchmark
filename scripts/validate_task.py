from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

REQUIRED_FILES = (
    "task.toml",
    "instruction.md",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/test.sh",
)


def changed_task_roots(base: str, head: str) -> set[Path]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}"], check=True, capture_output=True, text=True
    )
    roots: set[Path] = set()
    for name in result.stdout.splitlines():
        path = Path(name)
        if path.parts[:1] == ("tasks",) and len(path.parts) >= 4:
            roots.add(Path(*path.parts[:4]))
    return roots


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a Terminal-Bench-Science-style task PR")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    task_roots = changed_task_roots(args.base, args.head)
    if not task_roots:
        print("No task directory changed; structural task checks are not required.")
        return
    body = os.environ.get("PR_BODY", "")
    if "/discussions/" not in body:
        raise SystemExit("Task PR body must link its approved Task Proposal Discussion.")
    failures: list[str] = []
    for root in sorted(task_roots):
        missing = [str(root / file) for file in REQUIRED_FILES if not (root / file).is_file()]
        if missing:
            failures.append(f"{root}: missing required files: {', '.join(missing)}")
        if (root / "task.toml").is_file() and "[metadata]" not in (root / "task.toml").read_text(
            encoding="utf-8"
        ):
            failures.append(f"{root}/task.toml: [metadata] is required")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Validated {len(task_roots)} task contribution(s).")


if __name__ == "__main__":
    main()
