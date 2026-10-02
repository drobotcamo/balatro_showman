"""Executable contract checks for the NOVA portfolio-state procedure."""

from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / ".opencode" / "skill" / "portfolio-state" / "SKILL.md"


class PortfolioStateSkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = SKILL.read_text(encoding="utf-8")
        cls.flat = " ".join(cls.text.split())

    def test_authority_and_entry_point(self) -> None:
        self.assertIn("sole portfolio authority", self.text)
        self.assertIn("/orchestrate", self.text)
        self.assertIn("`.opencode/agents/orchestrator.md`", self.text)

    def test_audit_only_has_no_write_boundary(self) -> None:
        self.assertIn("audit-only mode", self.text)
        self.assertIn("performs no repository, GitHub, tag, branch, or worktree writes", self.flat)
        self.assertIn("only authorized T0", self.text)
        self.assertIn("Never merge", self.text)

    def test_required_procedure_and_scenarios_are_explicit(self) -> None:
        for marker in (
            "State snapshot", "Baton audit", "Dependency/readiness derivation",
            "Duplicate search", "Bounded issue creation", "Final recheck",
            "healthy continuation", "stale/conflicting batons", "blocked issues",
            "eligible issue creation", "duplicate suppression", "missing CI",
            "stale worktrees", "unavailable tag allocator", "budget exhaustion",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.flat)

    def test_budget_and_fixed_report_reserve_verification(self) -> None:
        self.assertIn("finite token and external-action budgets", self.text)
        self.assertIn("Reserve budget for final verification and reporting", self.flat)
        self.assertIn("exactly one recommendation", self.text)
        self.assertIn("Uncertainty", self.text)


if __name__ == "__main__":
    unittest.main()
