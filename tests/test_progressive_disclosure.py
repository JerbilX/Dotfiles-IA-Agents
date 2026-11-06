#!/usr/bin/env python3
"""
Unit tests for the self-sufficient basal prompt (ADR-0047): basal word budget, modular word budget
(<= 300 words), relative link integrity, absence of orphan core/ pointers and core invariants preservation.
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
BASAL_WORD_BUDGET = 2000  # Debe coincidir con MAX_CONTEXT_WORDS en build.sh (ADR-0048)
TARGET_WORD_BUDGET = 1100  # Debe coincidir con TARGET_CONTEXT_WORDS en build.sh (ADR-0048)


def setUpModule():
    from dist_support import ensure_dist
    ensure_dist()


class TestProgressiveDisclosure(unittest.TestCase):

    def test_compiled_antigravity_word_budget(self):
        """dist/antigravity/AGENTS.md must satisfy the basal word budget."""
        dist_agents = os.path.join(DIST_DIR, "antigravity", "AGENTS.md")
        self.assertTrue(os.path.isfile(dist_agents), f"Missing compiled artifact: {dist_agents}")
        with open(dist_agents, "r", encoding="utf-8") as f:
            words = len(f.read().split())
        self.assertLessEqual(
            words, BASAL_WORD_BUDGET,
            f"dist/antigravity/AGENTS.md exceeds {BASAL_WORD_BUDGET} words budget: {words} words"
        )

    def test_compiled_claude_word_budget(self):
        """dist/claude/AGENTS.md must satisfy the basal word budget."""
        dist_claude = os.path.join(DIST_DIR, "claude", "AGENTS.md")
        self.assertTrue(os.path.isfile(dist_claude), f"Missing compiled artifact: {dist_claude}")
        with open(dist_claude, "r", encoding="utf-8") as f:
            words = len(f.read().split())
        self.assertLessEqual(
            words, BASAL_WORD_BUDGET,
            f"dist/claude/AGENTS.md exceeds {BASAL_WORD_BUDGET} words budget: {words} words"
        )

    def test_build_budget_matches_tests(self):
        """build.sh default MAX_CONTEXT_WORDS and TARGET_CONTEXT_WORDS must match the tested basal budget."""
        with open(os.path.join(REPO_ROOT, "build.sh"), "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn(f'MAX_CONTEXT_WORDS="${{MAX_CONTEXT_WORDS:-{BASAL_WORD_BUDGET}}}"', content)
            self.assertIn(f'TARGET_CONTEXT_WORDS="${{TARGET_CONTEXT_WORDS:-{TARGET_WORD_BUDGET}}}"', content)

    def test_core_rules_word_budget(self):
        """Non-router core rules must stay below 300 words (ADR-0013 modular threshold)."""
        core_files = [
            cf for cf in glob.glob(os.path.join(CORE_DIR, "*.md"))
            if os.path.basename(cf) not in ("00-router.md",)
        ]
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
            "GEMINI.md",
            "Inmunidad Normativa",
            "Blindaje Anti-Reconocimiento y Anti-Exfiltración",
            "Precedencia de Entornos Locales",
            "Higiene de Salida y Pruebas",
            "Veto acumulativo",
            "Fast-path",
            "Activación Obligatoria de Skills",
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

    def test_procedural_rules_delegated_to_skills(self):
        """Procedural rules removed from core/ (ADR-0047) must live in the issue-driven-workflow skill."""
        provisioning = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "references", "repo-provisioning.md"
        )
        with open(provisioning, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Inicialización Local Proactiva", content)
        self.assertIn("Gate de Confirmación", content)

    def test_no_orphan_core_pointers_in_router_and_dist(self):
        """core/00-router.md and compiled dist prompts must not contain orphan pointers to core/ (ADR-0047)."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        self.assertTrue(os.path.isfile(router_path), f"Missing router: {router_path}")
        with open(router_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Solo 00-router y 01-objectivity existen; cualquier core/02+ es un puntero huérfano
        orphan_pattern = re.compile(r"core/(?:0[2-9]|[1-9][0-9])-")
        self.assertEqual(
            orphan_pattern.findall(content), [],
            "core/00-router.md must not contain orphan pointers to core/*.md"
        )

        # Artefactos que viajan al runtime: prompt compilado, skills y reglas de runtime
        runtime_artifacts = (
            glob.glob(os.path.join(CORE_DIR, "*.md"))
            + glob.glob(os.path.join(DIST_DIR, "*", "AGENTS.md"))
            + glob.glob(os.path.join(REPO_ROOT, "skills", "**", "*.md"), recursive=True)
            + glob.glob(os.path.join(RUNTIMES_DIR, "*", "rules", "*.md"))
        )
        offenders = []
        for path in runtime_artifacts:
            with open(path, "r", encoding="utf-8") as f:
                if orphan_pattern.search(f.read()):
                    offenders.append(os.path.relpath(path, REPO_ROOT))
        self.assertEqual(offenders, [], f"Orphan pointers to core/NN-*.md found in: {offenders}")

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
        self.assertIn("status: superseded by ADR-0047", content, "ADR-0038 must be marked as superseded")
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
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        for label in ("profile:flash-low", "profile:flash-medium", "profile:flash-high", "profile:pro"):
            self.assertIn(label, router_content, f"Missing {label} in core/00-router.md")

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

    def test_domain_mcp_precedence_over_web_search_invariants(self):
        """core/00-router.md and skills/eso-addon-development/SKILL.md must enforce MCP precedence over web search (#266)."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        self.assertIn("servidores MCP de dominio antes que la web", router_content)

        eso_skill_path = os.path.join(REPO_ROOT, "skills", "eso-addon-development", "SKILL.md")
        with open(eso_skill_path, "r", encoding="utf-8") as f:
            eso_skill_content = f.read()

        self.assertIn("Vía Contingencia — Búsqueda Web", eso_skill_content)
        self.assertIn("Flujo Ordenado de Inspección y Fallback", eso_skill_content)
        self.assertIn("Con Servidor MCP Disponible", eso_skill_content)
        self.assertIn("Si el MCP No Está Disponible", eso_skill_content)
        self.assertIn("gate humano", eso_skill_content)
        self.assertIn("hipótesis técnica verificable", eso_skill_content)
        self.assertIn("eso-mcp-server", eso_skill_content)
        self.assertIn("búsqueda web", eso_skill_content.lower())
        self.assertIn("vacíos documentales confirmados", eso_skill_content)
        self.assertNotIn("Límite Externo", eso_skill_content)

    def test_eso_lookup_flow_order_and_single_circuit_breaker(self):
        """skills/eso-addon-development/SKILL.md must consult local references before web and define the circuit breaker once (#266)."""
        eso_skill_path = os.path.join(REPO_ROOT, "skills", "eso-addon-development", "SKILL.md")
        with open(eso_skill_path, "r", encoding="utf-8") as f:
            eso_skill_content = f.read()

        self.assertIn(
            "**Con Servidor MCP Disponible:** MCP -> Referencias Locales -> Web -> Stop & Ask.",
            eso_skill_content,
        )
        self.assertIn(
            "**Si el MCP No Está Disponible:** Referencias Locales -> Web -> Stop & Ask.",
            eso_skill_content,
        )
        self.assertIn("tras consultar sin éxito el MCP y las referencias locales", eso_skill_content)
        self.assertIn("o tras agotar su límite sin localizar el símbolo", eso_skill_content)

        self.assertEqual(eso_skill_content.count("Límites por Etapa (fuente única del circuit breaker)"), 1)
        self.assertEqual(eso_skill_content.count("Prohibido reiniciar el contador"), 1)
        self.assertEqual(eso_skill_content.count("Máximo 1 búsqueda web acotada"), 1)
        self.assertLess(
            eso_skill_content.index("Límites por Etapa"),
            eso_skill_content.index("Flujo Ordenado de Inspección y Fallback"),
        )


if __name__ == "__main__":
    unittest.main()

