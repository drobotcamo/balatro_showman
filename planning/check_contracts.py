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
- The orchestrator agent (`.opencode/agents/orchestrator.md`) and its
  `/orchestrate` command exist with the required sections and wiring.
- Commands, roles and configuration retain structural routing/permission boundaries.
  These checks do not execute an agent or enforce GitHub review/merge behavior.

Stdlib only; exit code 1 on any failure.
"""

from __future__ import annotations

import re
import json
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
    "Updated", "Issue", "PR", "Branch", "Worktree", "Objective", "Next", "Validation",
)
LEGACY_THREAD_FIELDS = ("Owner", "Status", "Scope", "Dependencies")

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
        if not re.fullmatch(r"(?:\d+|[A-Z]{4})-[a-z0-9-]+\.md", path.name):
            fail(f"{rel}: name must be <issue-number-or-tag>-<short-name>.md")
        text = strip_fenced(path.read_text(encoding="utf-8"))
        # Some historical full records indent fields or prefix them with a bullet.
        historical = all(re.search(rf"^(?:[ \t]*-[ \t]+|[ \t]*){field}:", text, re.M)
                         for field in LEGACY_THREAD_FIELDS)
        if historical:
            text = re.sub(r"^(?:[ \t]*-[ \t]+|[ \t]+)(?=[A-Za-z]+:)", "", text, flags=re.M)
        fields = dict(re.findall(
            r"^([A-Za-z]+):[ \t]*([\s\S]*?)(?=^[A-Za-z]+:|^#{1,6}[ \t]+|\Z)", text, re.M
        ))
        # Full historical records retain their old fields. Anything else is compact.
        legacy = all(field in fields for field in LEGACY_THREAD_FIELDS)
        required = THREAD_REQUIRED_FIELDS + (LEGACY_THREAD_FIELDS if legacy else ("Risks",))
        if not legacy and not re.search(r"^# .+", text, re.M):
            fail(f"{rel}: compact checkpoint needs a title")
        for field in required:
            if not fields.get(field, "").strip():
                fail(f"{rel}: missing or empty handoff field {field!r}")
        match = re.fullmatch(r"(?P<id>\d+|[A-Z]{4})-[a-z0-9-]+\.md", path.name)
        if match and match.group("id").isalpha():
            tag = match.group("id")
            registry = load_issue_tags()
            issue = registry.get(tag)
            issue_field = re.search(r"^Issue:\s*([A-Z]{4})\s*\(#(\d+)\)", text, re.M)
            if issue is None:
                fail(f"{rel}: tag {tag} is not registered")
            elif not issue_field or issue_field.group(1) != tag or int(issue_field.group(2)) != issue:
                fail(f"{rel}: Issue field must be {tag} (#{issue})")


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


def check_issue_tags() -> None:
    path = PLANNING / "issue-tags.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    except (OSError, ValueError) as exc:
        fail(f"issue-tags.json: invalid JSON: {exc}")
        return
    if not isinstance(data, dict):
        fail("issue-tags.json: expected an object")
        return
    for tag, issue in data.items():
        if not isinstance(tag, str) or not re.fullmatch(r"[A-Z]{4}", tag):
            fail(f"issue-tags.json: invalid tag {tag!r}")
        if type(issue) is not int or issue < 1:
            fail(f"issue-tags.json: invalid issue number for {tag!r}")
    if len(data) != len(set(str(value) for value in data.values())):
        fail("issue-tags.json: duplicate issue number")


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key {key!r}")
        result[key] = value
    return result


def load_issue_tags() -> dict[str, int]:
    import json

    try:
        data = json.loads((PLANNING / "issue-tags.json").read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


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
    agent = ROOT / ".opencode" / "agents" / "orchestrator.md"
    command = ROOT / ".opencode" / "command" / "orchestrate.md"
    if not agent.is_file():
        fail("missing .opencode/agents/orchestrator.md")
    else:
        text = agent.read_text(encoding="utf-8")
        for heading in ORCHESTRATOR_REQUIRED_SECTIONS:
            if heading not in text:
                fail(f".opencode/agent/orchestrator.md: missing section {heading!r}")
    if not command.is_file():
        fail("missing .opencode/command/orchestrate.md")
    else:
        text = command.read_text(encoding="utf-8")
        if frontmatter(text).get("agent") != "orchestrator":
            fail(".opencode/command/orchestrate.md: must wire `agent: orchestrator`")


def check_portfolio_state() -> None:
    skill = ROOT / ".opencode" / "skill" / "portfolio-state" / "SKILL.md"
    if not skill.is_file():
        fail("missing .opencode/skill/portfolio-state/SKILL.md")
        return
    text = skill.read_text(encoding="utf-8")
    required = (
        "## Authority and entry point",
        "## Modes and write boundary",
        "## Procedure",
        "## Budget",
        "## Fixed report",
    )
    for marker in required:
        if section(text, marker) is None:
            fail(f"portfolio-state skill: missing section {marker!r}")
    if frontmatter(text).get("name") != "portfolio-state":
        fail("portfolio-state skill: incorrect frontmatter name")
    command = (ROOT / ".opencode/command/orchestrate.md").read_text(encoding="utf-8")
    if frontmatter(command).get("skill") != "portfolio-state":
        fail("orchestrate.md: incorrect portfolio-state metadata")
    agent = (ROOT / ".opencode/agents/orchestrator.md").read_text(encoding="utf-8")
    if "`.opencode/skill/portfolio-state/SKILL.md`" not in agent:
        fail("orchestrator.md: missing portfolio-state reference")


def frontmatter(text: str) -> dict:
    """Parse this repository's scalar/nested-map YAML subset, not general YAML.

    Reject unsupported syntax instead of accepting a matching phrase in the body.
    No third-party parser dependency is needed for these role/command adapters.
    """
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not match:
        raise ValueError("missing frontmatter")
    result = {}
    stack = [(-1, result)]
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        row = re.fullmatch(r'( *)("[^"\n]+"|[A-Za-z_][\w-]*):(?:[ \t]+(.*))?', line)
        if not row:
            raise ValueError(f"unsupported frontmatter line {line!r}")
        indent, key, value = len(row[1]), row[2].strip('"'), row[3]
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if key in parent:
            raise ValueError(f"duplicate frontmatter key {key!r}")
        if value is None:
            parent[key] = {}
            stack.append((indent, parent[key]))
        else:
            parent[key] = {"true": True, "false": False}.get(value, value.strip('"'))
    return result


def check_agent_wiring() -> None:
    """Structural adapter checks; not proof of agent obedience or review actions."""
    try:
        config = json.loads((ROOT / "opencode.json").read_text(encoding="utf-8"))
        if config.get("default_agent") != "lead" or config.get("subagent_depth") != 1:
            fail("opencode.json: expected default lead and depth one")
        for name, agent in (("work", "lead"), ("resume", "lead"), ("handoff", "lead"),
                            ("orchestrate", "orchestrator"), ("verify", "reviewer")):
            path = ROOT / ".opencode" / "command" / f"{name}.md"
            data = frontmatter(path.read_text(encoding="utf-8"))
            if data.get("agent") != agent:
                fail(f"{path.name}: expected agent {agent}")
            if name == "verify" and data.get("subtask") is not True:
                fail("verify.md: expected reviewer subtask")
        for name in ("lead", "orchestrator", "explorer", "reviewer"):
            path = ROOT / ".opencode" / "agents" / f"{name}.md"
            data = frontmatter(path.read_text(encoding="utf-8"))
            expected_mode = "primary" if name in ("lead", "orchestrator") else "subagent"
            if data.get("mode") != expected_mode:
                fail(f"{path.name}: expected mode {expected_mode}")
            permission = data.get("permission", {})
            if expected_mode == "primary":
                if permission.get("task") != {"*": "deny", "explorer": "allow", "reviewer": "allow"}:
                    fail(f"{path.name}: unexpected delegation boundary")
            elif permission.get("edit") != "deny" or permission.get("task") != "deny":
                fail(f"{path.name}: expected read-only nondelegating role")
            if name == "lead":
                check_lead_step_ceiling(data)
    except (OSError, ValueError, AttributeError) as exc:
        fail(f"agent wiring: {exc}")


def check_lead_step_ceiling(data: dict) -> None:
    """The production lead must not be forced into a text-only stop mid-issue."""
    if "steps" in data:
        fail("lead.md: production lead must not have a fixed steps ceiling")


def check_lead_merge_gate() -> None:
    """Canonical sections/references only; does not enforce GitHub behavior."""
    workflow = (PLANNING / "agent-workflow.md").read_text(encoding="utf-8")
    lead = (ROOT / ".opencode" / "agents" / "lead.md").read_text(encoding="utf-8")
    command = (ROOT / ".opencode" / "command" / "work.md").read_text(encoding="utf-8")
    template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    for heading in ("## Lead Loop", "## Approval And Merging", "## Handoff Protocol"):
        if section(workflow, heading) is None:
            fail(f"workflow: missing section {heading}")
    for name, text in (("lead", lead), ("work", command), ("PR template", template)):
        if "`planning/agent-workflow.md`" not in text:
            fail(f"{name}: missing canonical workflow reference")


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
    errors.clear()
    check_threads()
    check_decisions()
    check_learnings()
    check_open_questions()
    check_issue_tags()
    check_components()
    check_roadmap()
    check_orchestrator()
    check_portfolio_state()
    check_lead_merge_gate()
    check_agent_wiring()
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
