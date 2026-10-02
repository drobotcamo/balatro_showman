"""Fixture-backed validator behavior, not workflow/agent execution."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from planning import check_contracts as checks
from tools import issue_tags

COMPACT = """# Work Checkpoint
Updated: 2026-10-02
Issue: #123
PR: none
Branch: fixture
Worktree: fixture-path
Objective: validate fixtures
Validation: revision abc123; checks passed
Risks: no live evidence; fixture only
Next: lead resumes inspection
"""
FULL = COMPACT + "Owner: fixture\nStatus: blocked\nScope: fixture\nDependencies: none\n"


class PlanningValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.planning = self.root / "planning"
        self.threads = self.planning / "agent-state/threads"
        self.threads.mkdir(parents=True)
        self.registry = self.planning / "issue-tags.json"
        self.registry.write_text('{"BIRD": 58}', encoding="utf-8")
        self.patches = [patch.object(checks, "ROOT", self.root),
                        patch.object(checks, "PLANNING", self.planning),
                        patch.object(issue_tags, "REGISTRY", self.registry)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)
        checks.errors.clear()

    def thread(self, name, text):
        (self.threads / name).write_text(text, encoding="utf-8")
        checks.check_threads()
        return checks.errors

    def test_numeric_compact_without_tag(self):
        self.assertEqual(self.thread("123-fixture.md", COMPACT), [])

    def test_historical_full_numeric_and_titleless_tagged(self):
        self.thread("123-fixture.md", FULL.replace("Next: lead resumes inspection", "Next:\n- lead resumes inspection"))
        tagged = FULL.replace("Issue: #123", "Issue: BIRD (#58)").replace("Validation:", "  Validation:").replace("Next:", "- Next:").split("\n", 1)[1]
        self.assertEqual(self.thread("BIRD-fixture.md", tagged), [])

    def test_tagged_compact(self):
        self.assertEqual(self.thread("BIRD-fixture.md", COMPACT.replace("#123", "BIRD (#58)")), [])

    def test_missing_empty_fenced_and_invalid_checkpoint_data(self):
        for text in (COMPACT.replace("Risks: no live evidence; fixture only\n", ""),
                     COMPACT.replace("Validation: revision abc123; checks passed", "Validation: "),
                     "```\n" + COMPACT + "```\n", COMPACT.split("\n", 1)[1]):
            with self.subTest(text=text):
                checks.errors.clear()
                self.assertTrue(self.thread("123-fixture.md", text))

    def test_bad_name_unknown_tag_and_wrong_mapping(self):
        for name, text in (("bad.md", COMPACT), ("XXXX-fixture.md", COMPACT),
                           ("BIRD-fixture.md", COMPACT.replace("#123", "BIRD (#59)"))):
            with self.subTest(name=name):
                checks.errors.clear()
                self.assertTrue(self.thread(name, text))

    def test_registry_invalid_and_duplicate_inputs_both_consumers(self):
        for payload in ('{"bad": 1}', '{"BIRD": 0}', '{"BIRD": true}',
                        '{"BIRD": "58"}', '{"BIRD": 58, "WAVE": 58}',
                        '{"BIRD": 58, "BIRD": 59}', '{"BIRD": []}', '[]'):
            with self.subTest(payload=payload):
                self.registry.write_text(payload, encoding="utf-8")
                checks.errors.clear()
                checks.check_issue_tags()
                self.assertTrue(checks.errors)
                with self.assertRaises(ValueError):
                    issue_tags.load()

    def test_registry_valid_alias(self):
        checks.check_issue_tags()
        self.assertEqual(checks.errors, [])
        self.assertEqual(issue_tags.load(), {"BIRD": 58})

    def test_broken_reference_fails(self):
        for ref in ("AGENTS.md", "CLAUDE.md", "planning/README.md", "planning/ROADMAP.md",
                    "planning/ARCHITECTURE.md", "planning/agent-workflow.md", "planning/agent-state/README.md"):
            path = self.root / ref
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("`missing.py`" if ref == "AGENTS.md" else "fixture", encoding="utf-8")
        checks.check_references()
        self.assertTrue(any("broken reference" in error for error in checks.errors))

    def test_decision_duplicate_and_order_checks_remain(self):
        (self.planning / "DECISIONS.md").write_text(
            "### D002 — accepted — a\n### D001 — accepted — b\n### D001 — accepted — c\n", encoding="utf-8")
        checks.check_decisions()
        self.assertTrue(any("duplicate" in error for error in checks.errors))
        self.assertTrue(any("order" in error for error in checks.errors))
