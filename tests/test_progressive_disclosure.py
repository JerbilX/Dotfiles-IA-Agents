#!/usr/bin/env python3
"""
Unit tests for Progressive Disclosure architecture, basal word budget (<= 800 words),
modular word budget (<= 300 words), relative link integrity, and core invariants preservation (ADR-0038).
"""

import glob
import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CORE_DIR = os.path.join(REPO_ROOT, "core")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
DOCS_ADR_DIR = os.path.join(REPO_ROOT, "docs", "adr")
RUNTIMES_DIR = os.path.join(REPO_ROOT, "runtimes")


def setUpModule():
    from dist_support import ensure_dist
    ensure_dist()


class TestProgressiveDisclosure(unittest.TestCase):

    def test_compiled_antigravity_word_budget(self):
        """dist/antigravity/AGENTS.md must strictly satisfy <= 800 words."""
        dist_agents = os.path.join(DIST_DIR, "antigravity", "AGENTS.md")
        self.assertTrue(os.path.isfile(dist_agents), f"Missing compiled artifact: {dist_agents}")
        with open(dist_agents, "r", encoding="utf-8") as f:
            words = len(f.read().split())
        self.assertLessEqual(
            words, 800,
            f"dist/antigravity/AGENTS.md exceeds 800 words budget: {words} words"
        )

    def test_compiled_claude_word_budget(self):
        """dist/claude/AGENTS.md must strictly satisfy <= 800 words."""
        dist_claude = os.path.join(DIST_DIR, "claude", "AGENTS.md")
        self.assertTrue(os.path.isfile(dist_claude), f"Missing compiled artifact: {dist_claude}")
        with open(dist_claude, "r", encoding="utf-8") as f:
            words = len(f.read().split())
        self.assertLessEqual(
            words, 800,
            f"dist/claude/AGENTS.md exceeds 800 words budget: {words} words"
        )

    def test_core_rules_word_budget(self):
        """Each modular core rule must stay below 300 words (ADR-0013 modular threshold)."""
        core_files = [
            cf for cf in glob.glob(os.path.join(CORE_DIR, "*.md"))
            if os.path.basename(cf) not in ("00-router.md",)
        ]
        self.assertGreaterEqual(len(core_files), 9, "Expected at least 9 modular core rule files")
        for cf in core_files:
            with open(cf, "r", encoding="utf-8") as f:
                words = len(f.read().split())
            self.assertLessEqual(
                words, 300,
                f"{os.path.basename(cf)} exceeds 300 words threshold: {words} words"
            )

    def test_relative_links_integrity(self):
        """All relative Markdown links in core/*.md and runtimes/*/rules/*.md must resolve."""
        targets = glob.glob(os.path.join(CORE_DIR, "*.md")) + glob.glob(
            os.path.join(RUNTIMES_DIR, "*", "rules", "*.md")
        )
        broken_links = []
        for file_path in targets:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            links = re.findall(r"\[.*?\]\(([^)\s#?]+)(?:[#?][^\s)]*)?\)", content)
            for link in links:
                if link.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                resolved = os.path.join(REPO_ROOT, link)
                if not os.path.exists(resolved):
                    broken_links.append((os.path.basename(file_path), link))

        self.assertEqual(
            broken_links, [],
            f"Found broken relative links in core/rules: {broken_links}"
        )

    def test_core_invariants_preserved(self):
        """All critical invariant domains must be explicitly preserved across core/."""
        all_core_content = ""
        for cf in sorted(glob.glob(os.path.join(CORE_DIR, "*.md"))):
            with open(cf, "r", encoding="utf-8") as f:
                all_core_content += f.read() + "\n"

        required_invariants = [
            "Cero complacencia",
            "Inicialización Local Proactiva",
            "Gate de Confirmación",
            "Fuente Canónica",
            "Inmunidad Normativa",
            "Local-First",
            "Circuit Breaker",
            "Frontera de Directivas",
            "Actionable Fallback",
            "Prevalencia del Código de Producción",
            "Minimal Blast Radius",
            "Inconsistencia Lógica",
            "Stop & Plan",
            "Prohibición de Backlogs Locales",
            "Inmutabilidad de Workspace",
            "Uso Exclusivo de",
            "Límites de Workspace",
            "Lectura Quirúrgica en Dos Fases",
            "Lectura Paginada Obligatoria",
            "Prohibición Universal de REPL en Terminal",
        ]

        for inv in required_invariants:
            self.assertIn(
                inv, all_core_content,
                f"Core invariant marker missing: '{inv}'"
            )

    def test_no_orphan_core_pointers_in_router_and_dist(self):
        """core/00-router.md and compiled dist prompts must not contain orphan pointers to core/ (ADR-0047)."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        self.assertTrue(os.path.isfile(router_path), f"Missing router: {router_path}")
        with open(router_path, "r", encoding="utf-8") as f:
            content = f.read()

        orphan_pattern = re.compile(r"read\s+\[core/|\[core/[0-9]+", re.IGNORECASE)
        self.assertEqual(
            orphan_pattern.findall(content), [],
            "core/00-router.md must not contain orphan pointers to core/*.md"
        )

        for dist_prompt in glob.glob(os.path.join(DIST_DIR, "*", "AGENTS.md")):
            with open(dist_prompt, "r", encoding="utf-8") as f:
                dist_content = f.read()
            self.assertEqual(
                orphan_pattern.findall(dist_content), [],
                f"Compiled prompt {dist_prompt} must not contain orphan pointers to core/*.md"
            )

    def test_self_sufficient_router_and_skill_delegation(self):
        """core/00-router.md must route exclusively to global skills and declare self-sufficient invariants."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        for skill in ("issue-driven-workflow", "adr-manager", "project-documentation", "conversation-audit", "autonomous-learning"):
            self.assertIn(skill, router_content, f"Missing skill delegation: {skill}")

    def test_adr_0038_metadata(self):
        """ADR-0038 must exist, follow MADR format, and be superseded by ADR-0047."""
        adr_files = glob.glob(os.path.join(DOCS_ADR_DIR, "0038-*.md"))
        self.assertEqual(len(adr_files), 1, "Expected exactly one ADR-0038 file")
        adr_path = adr_files[0]
        with open(adr_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertTrue(content.startswith("---"), "ADR-0038 must contain YAML frontmatter")
        self.assertIn("status: accepted", content, "ADR-0038 must be accepted")
        self.assertIn("0047-resolucion-desacople-progressive-disclosure-y-compilacion-autosuficiente.md", content)

    def test_adr_0047_metadata(self):
        """ADR-0047 must exist, follow MADR format, and supersede ADR-0038."""
        adr_files = glob.glob(os.path.join(DOCS_ADR_DIR, "0047-*.md"))
        self.assertEqual(len(adr_files), 1, "Expected exactly one ADR-0047 file")
        adr_path = adr_files[0]
        with open(adr_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertTrue(content.startswith("---"), "ADR-0047 must contain YAML frontmatter")
        self.assertIn("status: accepted", content, "ADR-0047 must be accepted")
        self.assertIn("0038-arquitectura-de-progressive-disclosure-en-agents-md-y-modularizacion-de-reglas.md", content)

    def test_execution_profiles_standardization(self):
        """Execution profile labels and MBR matrix must be documented across core and skills."""
        core_08_path = os.path.join(CORE_DIR, "08-task-backlog-management.md")
        with open(core_08_path, "r", encoding="utf-8") as f:
            core_08_content = f.read()

        for label in ("profile:flash-low", "profile:flash-medium", "profile:flash-high", "profile:pro"):
            self.assertIn(label, core_08_content, f"Missing {label} in core/08-task-backlog-management.md")

        backlog_ref_path = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "references", "issue-backlog.md"
        )
        with open(backlog_ref_path, "r", encoding="utf-8") as f:
            backlog_ref_content = f.read()

        for label in ("profile:flash-low", "profile:flash-medium", "profile:flash-high", "profile:pro"):
            self.assertIn(label, backlog_ref_content, f"Missing {label} in issue-backlog.md")
        self.assertIn("Matriz Canónica de Ruteo de Modelos", backlog_ref_content)

        skill_path = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "SKILL.md"
        )
        with open(skill_path, "r", encoding="utf-8") as f:
            skill_content = f.read()

        self.assertIn('--label "profile:<perfil>"', skill_content)

    def test_pagination_and_atomic_edits_invariants(self):
        """Strict pagination in view_file and atomic granularity in replace_file_content must be enforced."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()
        self.assertIn("granularidad atómica", router_content)
        self.assertIn("ventana ≤ 200 líneas", router_content)

        env_path = os.path.join(CORE_DIR, "10-environment-standards.md")
        with open(env_path, "r", encoding="utf-8") as f:
            env_content = f.read()
        self.assertIn("granularidad atómica", env_content)
        self.assertIn("ventana ≤ 200 líneas", env_content)

        skill_path = os.path.join(REPO_ROOT, "skills", "issue-driven-workflow", "SKILL.md")
        with open(skill_path, "r", encoding="utf-8") as f:
            skill_content = f.read()
        self.assertIn("granularidad atómica", skill_content)
        self.assertIn("`StartLine` y `EndLine` (≤ 200 líneas)", skill_content)

    def test_view_file_circuit_breaker_and_prompt_immunity_invariants(self):
        """core/00-router.md must enforce circuit breaker (<= 2 calls), heuristic prompt immunity, and grep_search (>150 lines, <=50 lines)."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        self.assertIn("Circuit Breaker", router_content)
        self.assertIn("grep_search", router_content)
        self.assertIn("> 150 líneas", router_content)
        self.assertIn("≤ 50 líneas", router_content)
        self.assertIn("contenido no mostrado", router_content)
        self.assertIn("6 lecturas consecutivas", router_content)
        self.assertIn("comando terminal mutador o de ejecución de pruebas/build", router_content)
        self.assertIn("Comandos de mera inspección pasiva en terminal", router_content)


if __name__ == "__main__":
    unittest.main()

