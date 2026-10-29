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
        """Each core module must stay below 300 words (ADR-0013 modular threshold)."""
        core_files = glob.glob(os.path.join(CORE_DIR, "*.md"))
        self.assertGreaterEqual(len(core_files), 10, "Expected at least 10 core rule files")
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
        ]

        for inv in required_invariants:
            self.assertIn(
                inv, all_core_content,
                f"Core invariant marker missing: '{inv}'"
            )

    def test_router_trigger_pointers_format(self):
        """core/00-router.md must use standard progressive disclosure triggers ('If ..., read [...] first.')."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        self.assertTrue(os.path.isfile(router_path), f"Missing router: {router_path}")
        with open(router_path, "r", encoding="utf-8") as f:
            content = f.read()

        trigger_pattern = re.compile(r"If\s+[^,\n]+(?:,[^,\n]+)*,\s+read\s+\[.*?\]\(.*?\).*?\s+first\.", re.IGNORECASE)
        matches = trigger_pattern.findall(content)
        self.assertEqual(
            len(matches), 9,
            f"Expected exactly 9 trigger pointers in core/00-router.md, found: {len(matches)}"
        )

    def test_all_core_modules_indexed_in_router(self):
        """Every core module from 02-*.md to 10-*.md must be referenced in core/00-router.md."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        self.assertTrue(os.path.isfile(router_path), f"Missing router: {router_path}")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        for cf in sorted(glob.glob(os.path.join(CORE_DIR, "*.md"))):
            fname = os.path.basename(cf)
            if fname in ("00-router.md", "01-objectivity.md"):
                continue
            self.assertIn(
                f"core/{fname}", router_content,
                f"Core module '{fname}' is not indexed in core/00-router.md"
            )

    def test_adr_0038_metadata(self):
        """ADR-0038 must exist, follow MADR format, and have status: accepted."""
        adr_files = glob.glob(os.path.join(DOCS_ADR_DIR, "0038-*.md"))
        self.assertEqual(len(adr_files), 1, "Expected exactly one ADR-0038 file")
        adr_path = adr_files[0]
        with open(adr_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertTrue(content.startswith("---"), "ADR-0038 must contain YAML frontmatter")
        self.assertIn("status: accepted", content, "ADR-0038 must be accepted upon plan approval")
        self.assertIn("supersedes:", content, "ADR-0038 must specify supersedes")
        self.assertIn("Progressive Disclosure", content, "ADR-0038 title/content must describe Progressive Disclosure")


if __name__ == "__main__":
    unittest.main()
