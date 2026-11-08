import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(REPO_ROOT, *parts), "r", encoding="utf-8") as f:
        return f.read()


class TestProportionality(unittest.TestCase):
    """ADR-0044: la ceremonia escala por nivel sin perder trazabilidad."""

    def test_router_declares_proportionality_and_levels(self):
        router = _read("core", "00-router.md")
        for marker in ("Proporcionalidad", "Trazabilidad"):
            self.assertIn(marker, router, f"Falta '{marker}' en core/00-router.md")

        backlog = _read("skills", "issue-driven-workflow", "references", "issue-backlog.md")
        for marker in ("**N0**", "**N1**", "**N2**"):
            self.assertIn(marker, backlog, f"Falta '{marker}' en issue-backlog.md")

    def test_traceability_chain_is_preserved(self):
        router = _read("core", "00-router.md")
        self.assertIn("Closes #<id>", router)
        self.assertIn("rama efímera", router)

    def test_secondary_findings_require_confirmation(self):
        self.assertIn("con su confirmación", _read("core", "00-router.md"))

    def test_stop_and_plan_is_scoped_to_n2(self):
        lifecycle = _read("skills", "issue-driven-workflow", "references", "branch-lifecycle.md")
        self.assertIn("solo n2", lifecycle.lower())
        self.assertIn("Stop & Plan", lifecycle)

    def test_hygiene_is_not_triggered_by_queries(self):
        skill = _read("skills", "issue-driven-workflow", "SKILL.md")
        self.assertNotIn("obligatoria ante cualquier interacción", skill)

    def test_claude_runtime_tool_equivalences_removed(self):
        """CLAUDE_TOOL_EQUIVALENCES is removed in favor of neutral tool vocabulary (ADR-0050, #288)."""
        rules = _read("runtimes", "claude", "rules", "01-claude-tools.md")
        self.assertNotIn("CLAUDE_TOOL_EQUIVALENCES", rules)
        self.assertNotIn("Equivalencias de Herramientas", rules)
        self.assertLessEqual(len(rules.split()), 300)


if __name__ == "__main__":
    unittest.main()
