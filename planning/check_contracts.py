"""Validate agent-planning documents in this repository.

Run from the repository root: python planning/check_contracts.py

Checks:
- Thread files are named <issue-number>-<short-name>.md and contain the
  handoff template fields defined in planning/agent-workflow.md.
- planning/DECISIONS.md uses ADR-lite entry headers and unique IDs.
- planning/LEARNINGS.md entries use the documented date-title format.
- Backtick file references in core agent documents resolve to real files.

Stdlib only; exit code 1 on any failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PLANNING = Path(__file__).resolve().parent
ROOT = PLANNING.parent

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(message)


THREAD_REQUIRED_FIELDS = (
    "Updated:",
    "Issue:",
    "PR:",
    "Owner:",
    "Branch:",
    "Worktree:",
    "Objective:",
    "Status:",
    "Scope:",
    "Dependencies:",
    "Next:",
    "Validation:",
)


def check_threads() -> None:
    threads = PLANNING / "agent-state" / "threads"
    if not threads.is_dir():
        fail("missing planning/agent-state/threads/")
        return
    for path in sorted(threads.glob("*.md")):
        rel = path.relative_to(ROOT)
        if path.name == "README.md":
            continue
        if not re.fullmatch(r"\d+-[a-z0-9-]+\.md", path.name):
            fail(f"{rel}: name must be <issue-number>-<short-name>.md")
        text = path.read_text(encoding="utf-8")
        for field in THREAD_REQUIRED_FIELDS:
            if field not in text:
                fail(f"{rel}: missing handoff field {field!r}")


def strip_fenced(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


def check_decisions() -> None:
    path = PLANNING / "DECISIONS.md"
    text = strip_fenced(path.read_text(encoding="utf-8"))
    headers = re.findall(r"^### (D\d{3})", text, re.M)
    if not headers:
        fail("DECISIONS.md: no `### D### — status — title` entries found")
    if len(headers) != len(set(headers)):
        fail("DECISIONS.md: duplicate decision IDs")
    for header in re.findall(r"^### .*$", text, re.M):
        if not re.match(r"^### D\d{3} — (accepted|superseded|retired) — ", header):
            fail(f"DECISIONS.md: malformed entry header: {header!r}")


def check_learnings() -> None:
    path = PLANNING / "LEARNINGS.md"
    text = strip_fenced(path.read_text(encoding="utf-8"))
    for header in re.findall(r"^## .*$", text, re.M):
        if not re.match(r"^## \d{4}-\d{2}-\d{2}: ", header):
            fail(f"LEARNINGS.md: malformed entry header: {header!r}")


def check_references() -> None:
    docs = (
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        PLANNING / "README.md",
        PLANNING / "agent-workflow.md",
        PLANNING / "agent-state" / "README.md",
    )
    ref_pattern = re.compile(r"`([^`\s]+?\.(?:md|py|json|yml))`")
    for doc in docs:
        if not doc.exists():
            fail(f"missing referenced document {doc.relative_to(ROOT)}")
            continue
        text = doc.read_text(encoding="utf-8")
        for ref in ref_pattern.findall(text):
            if any(ch in ref for ch in "<*>"):
                continue
            candidates = [
                ROOT / ref.lstrip("./"),
                PLANNING / ref,
                doc.parent / ref,
                PLANNING / ref.replace("planning/", "", 1),
            ]
            if not any(candidate.is_file() for candidate in candidates):
                fail(f"{doc.relative_to(ROOT)}: broken reference {ref!r}")


def main() -> int:
    check_threads()
    check_decisions()
    check_learnings()
    check_references()
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        print(f"\n{len(errors)} problem(s) found")
        return 1
    print("planning contracts OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())