#!/usr/bin/env python3
"""
Unit tests for the project-documentation skill, static documentation audit subagent protocol,
checklist standardization, prompt templates, and relative link integrity.
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SKILL_DIR = os.path.join(REPO_ROOT, "skills", "project-documentation")
RESOURCES_DIR = os.path.join(SKILL_DIR, "resources")


class TestProjectDocumentation(unittest.TestCase):

    def setUp(self):
        self.skill_file = os.path.join(SKILL_DIR, "SKILL.md")
        self.template_file = os.path.join(RESOURCES_DIR, "template-doc-audit-subagent.md")

    def test_subagent_prompt_template_exists_and_valid(self):
        """template-doc-audit-subagent.md must exist and declare the static auditor protocol."""
        self.assertTrue(
            os.path.isfile(self.template_file),
            f"Missing subagent template file: {self.template_file}"
        )
        with open(self.template_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Static Documentation Auditor", content)
        self.assertIn("Tool Budget", content)
        self.assertIn("Stop & Synthesize", content)
        self.assertIn("Circuit Breaker", content)
        self.assertIn("Diagnóstico de Calidad Documental", content)
        self.assertIn("Veredicto Global", content)
        self.assertIn("APROBADO", content)
        self.assertIn("REQUIERE SUBSANACIÓN", content)

    def test_subagent_shielding_and_read_only_rules(self):
        """Prompt template must enforce read-only tool confinement and prohibit mutators."""
        with open(self.template_file, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("inspección", content)
        self.assertIn("lectura de archivos", content)
        self.assertIn("escritura o edición", content)
        self.assertIn("PROHIBIDO", content)
        self.assertIn("Solo Lectura", content)

    def test_checklist_standardization_coverage(self):
        """Checklist must cover README structure, cross-links, Diátaxis taxonomy, and hygiene."""
        with open(self.template_file, "r", encoding="utf-8") as f:
            template_content = f.read()

        required_checklist_items = [
            "Presupuesto Cuantitativo",
            "Header & Badges",
            "Resumen Ejecutivo",
            "Arquitectura Esencial",
            "Quickstart Determinista",
            "Tabla Sintética de Interfaces",
            "Mapa Documental",
            "Enlaces Cruzados",
            "Diátaxis",
            "setup.md",
            "cli.md",
            "architecture.md",
            "adr/",
            "Cero Contenido Normativo",
            "Prohibición de Backlogs Locales",
        ]
        for item in required_checklist_items:
            self.assertIn(
                item, template_content,
                f"Missing checklist item in template: '{item}'"
            )

    def test_skill_markdown_contains_subagent_protocol(self):
        """SKILL.md must document section 7 with subagent delegation, parameters, and invocation."""
        self.assertTrue(
            os.path.isfile(self.skill_file),
            f"Missing skill file: {self.skill_file}"
        )
        with open(self.skill_file, "r", encoding="utf-8") as f:
            skill_content = f.read()

        self.assertIn("Protocolo de Auditoría Estática con Subagente Ligero", skill_content)
        self.assertIn("flash", skill_content)
        self.assertIn("flash_lite", skill_content)
        self.assertIn('"TypeName": "research"', skill_content)
        self.assertIn('"Role": "Static Documentation Auditor"', skill_content)
        self.assertIn("Stop & Synthesize", skill_content)
        self.assertIn("Tabla Diagnóstica de Deficiencias y Conformidad", skill_content)
        self.assertIn("template-doc-audit-subagent.md", skill_content)

    def test_relative_links_integrity(self):
        """All relative Markdown links within SKILL.md and template-doc-audit-subagent.md must resolve."""
        md_files = [self.skill_file, self.template_file]
        broken_links = []
        for file_path in md_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            links = re.findall(r"\[.*?\]\(([^)\s#?]+)(?:[#?][^\s)]*)?\)", content)
            base_dir = os.path.dirname(file_path)
            for link in links:
                if link.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                resolved = os.path.normpath(os.path.join(base_dir, link))
                if not os.path.exists(resolved):
                    broken_links.append((os.path.relpath(file_path, REPO_ROOT), link))

        self.assertEqual(
            broken_links, [],
            f"Found broken relative links in skills/project-documentation: {broken_links}"
        )


if __name__ == "__main__":
    unittest.main()
