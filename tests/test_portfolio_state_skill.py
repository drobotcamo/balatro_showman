"""Structural OpenCode adapter checks; these do not execute agent behavior."""

from pathlib import Path
import unittest
from unittest.mock import patch

from planning import check_contracts as checks

ROOT = Path(__file__).parents[1]


class AgentStructureTests(unittest.TestCase):
    def setUp(self):
        checks.errors.clear()

    def test_current_roles_commands_and_skill_structure(self):
        checks.check_agent_wiring()
        checks.check_orchestrator()
        checks.check_portfolio_state()
        checks.check_lead_merge_gate()
        self.assertEqual(checks.errors, [])

    def test_command_body_cannot_spoof_routing(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == ROOT / ".opencode/command/resume.md":
                return text.replace("agent: lead", "agent: build") + "\nagent: lead\n"
            return text
        with patch.object(Path, "read_text", read):
            checks.check_agent_wiring()
        self.assertTrue(any("resume.md" in error for error in checks.errors))

    def test_reviewer_permissions_cannot_be_spoofed_by_body(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == ROOT / ".opencode/agents/reviewer.md":
                return text.replace("edit: deny", "edit: allow") + "\nedit: deny\n"
            return text
        with patch.object(Path, "read_text", read):
            checks.check_agent_wiring()
        self.assertTrue(any("read-only" in error for error in checks.errors))

    def test_frontmatter_missing_duplicate_or_unsupported_fails(self):
        for text in ("agent: lead", "---\nagent: lead\nagent: build\n---\n", "---\nitems: [a]\n- bad\n---\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                checks.frontmatter(text)


if __name__ == "__main__":
    unittest.main()
