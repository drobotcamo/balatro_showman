"""Validate agent-planning documents in this repository.

Run from the repository root: python planning/check_contracts.py

Checks (mechanical only; it does not judge prose quality or gate thresholds):
- Thread files are named <issue-number>-<short-name>.md and contain the
  handoff template fields defined in planning/agent-workflow.md.
- planning/DECISIONS.md uses ADR-lite entry headers, unique IDs, and
  append-only (strictly increasing) ID order.
- planning/LEARNINGS.md entries use the documented date-title format.
- Every open question in planning/DECISIONS.md has a row in the ROADMAP
  `## Open Questions And Gates` table.
- Every component contract has the required sections and a valid status.
- Every ROADMAP phase has a status and a gate, and every component file is
  listed in the ROADMAP `## Component Ownership` table.
- Backtick file references in the core agent/planning documents resolve to real
  files. Inventory documents that intentionally reference external or vendored
  artifacts (e.g. `planning/PHASE0_INVENTORY.md`) are excluded, because those
  targets are not present in a fresh checkout.
- The orchestrator agent (`.opencode/agent/orchestrator.md`) and its
  `/orchestrate` command exist with the required sections and wiring.

Stdlib only; exit code 1 on any failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PLANNING = Path(__file__).resolve().parent
ROOT = PLANNING.parent

STATUS_VOCABULARY = {
    "planned",
    "designing",
    "building",
    "validated",
    "blocked",
    "retired",
}

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

COMPONENT_REQUIRED_SECTIONS = (
    "## Purpose",
    "## Inputs",
    "## Outputs",
    "## Invariants",
    "## Acceptance Criteria",
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


def section(text: str, heading: str) -> str | None:
    """Return the body of a `## heading` section, or None if absent."""
    match = re.search(rf"(?m)^{re.escape(heading)}[ \t]*$", text)
    if not match:
        return None
    rest = text[match.end():]
    next_heading = re.search(r"(?m)^## ", rest)
    return rest[: next_heading.start()] if next_heading else rest


def check_decisions() -> None:
    path = PLANNING / "DECISIONS.md"
    text = strip_fenced(path.read_text(encoding="utf-8"))
    headers = re.findall(r"^### (D\d{3})", text, re.M)
    if not headers:
        fail("DECISIONS.md: no `### D### — status — title` entries found")
        return
    if len(headers) != len(set(headers)):
        fail("DECISIONS.md: duplicate decision IDs")
    numbers = [int(header[1:]) for header in headers]
    if numbers != sorted(numbers):
        fail("DECISIONS.md: decision IDs are not in append-only order")
    for header in re.findall(r"^### .*$", text, re.M):
        if not re.match(r"^### D\d{3} — (accepted|superseded|retired) — ", header):
            fail(f"DECISIONS.md: malformed entry header: {header!r}")


def check_learnings() -> None:
    path = PLANNING / "LEARNINGS.md"
    text = strip_fenced(path.read_text(encoding="utf-8"))
    for header in re.findall(r"^## .*$", text, re.M):
        if not re.match(r"^## \d{4}-\d{2}-\d{2}: ", header):
            fail(f"LEARNINGS.md: malformed entry header: {header!r}")


def check_open_questions() -> None:
    decisions = (PLANNING / "DECISIONS.md").read_text(encoding="utf-8")
    roadmap = (PLANNING / "ROADMAP.md").read_text(encoding="utf-8")
    questions = re.findall(r"\*\*(Q\d{2})\*\*", decisions)
    table = section(roadmap, "## Open Questions And Gates")
    if table is None:
        fail("ROADMAP.md: missing '## Open Questions And Gates' section")
        return
    rows = "\n".join(
        line for line in table.splitlines() if line.strip().startswith("|")
    )
    linked = set(re.findall(r"\|\s*(Q\d{2})\s*\|", rows))
    for question in questions:
        if question not in linked:
            fail(
                f"ROADMAP.md: open question {question} has no row in the "
                "Open Questions And Gates table"
            )


def check_components() -> None:
    components = PLANNING / "components"
    if not components.is_dir():
        fail("missing planning/components/")
        return
    for path in sorted(components.glob("*.md")):
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        for section in COMPONENT_REQUIRED_SECTIONS:
            if section not in text:
                fail(f"{rel}: missing required section {section!r}")
        match = re.search(r"^Status: `([a-z]+)`", text, re.M)
        if not match:
            fail(f"{rel}: missing or malformed `Status: ` line")
        elif match.group(1) not in STATUS_VOCABULARY:
            fail(f"{rel}: invalid status {match.group(1)!r}")


def check_roadmap() -> None:
    path = PLANNING / "ROADMAP.md"
    text = path.read_text(encoding="utf-8")
    for part in re.split(r"(?m)^## ", text):
        header = part.splitlines()[0] if part else ""
        if not header.startswith("Phase "):
            continue
        phase = header.split(":", 1)[0]
        if not re.search(r"^Status: `[a-z]+`", part, re.M):
            fail(f"ROADMAP.md: {phase} has no valid `Status: ` line")
        if not re.search(r"^Gate\b", part, re.M):
            fail(f"ROADMAP.md: {phase} has no gate")
    ownership = section(text, "## Component Ownership")
    if ownership is None:
        fail("ROADMAP.md: missing '## Component Ownership' section")
        return
    rows = "\n".join(
        line
        for line in ownership.splitlines()
        if line.strip().startswith("|")
    )
    listed = set(re.findall(r"components/[A-Za-z0-9._-]+\.md", rows))
    for component in sorted((PLANNING / "components").glob("*.md")):
        if f"components/{component.name}" not in listed:
            fail(
                f"ROADMAP.md: component {component.name!r} is not in the "
                "Component Ownership table"
            )


ORCHESTRATOR_REQUIRED_SECTIONS = (
    "## Procedure",
    "## Write Authority",
    "## Report Format",
    "## Boundaries",
)


def check_orchestrator() -> None:
    agent = ROOT / ".opencode" / "agent" / "orchestrator.md"
    command = ROOT / ".opencode" / "command" / "orchestrate.md"
    if not agent.is_file():
        fail("missing .opencode/agent/orchestrator.md")
    else:
        text = agent.read_text(encoding="utf-8")
        for heading in ORCHESTRATOR_REQUIRED_SECTIONS:
            if heading not in text:
                fail(f".opencode/agent/orchestrator.md: missing section {heading!r}")
    if not command.is_file():
        fail("missing .opencode/command/orchestrate.md")
    else:
        text = command.read_text(encoding="utf-8")
        if "agent: orchestrator" not in text:
            fail(".opencode/command/orchestrate.md: must wire `agent: orchestrator`")


def check_references() -> None:
    docs = (
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        PLANNING / "README.md",
        PLANNING / "ROADMAP.md",
        PLANNING / "ARCHITECTURE.md",
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
    check_open_questions()
    check_components()
    check_roadmap()
    check_orchestrator()
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
