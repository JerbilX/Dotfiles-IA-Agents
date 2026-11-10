#!/usr/bin/env python3
"""
Unit tests for the self-sufficient basal prompt (ADR-0047): basal word budget, modular word budget
(<= 300 words), relative link integrity, absence of orphan core/ pointers and core invariants preservation.
"""

import glob
import json
import os
import re
import subprocess
import tempfile
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
            "Veto acumulativo",
            "Activación Obligatoria de Skills",
            "Local-First",
            "Circuit Breaker",
            "Frontera de Directivas",
            "Actionable Fallback",
            "Prevalencia del Código de Producción",
            "Minimal Blast Radius",
            "Inconsistencia Lógica",
            "Prohibición de Backlogs Locales",
            "Inmutabilidad de Workspace",
            "Límites de Workspace",
        ]

        for inv in required_invariants:
            self.assertIn(
                inv, all_core_content,
                f"Core invariant marker missing: '{inv}'"
            )

    def test_p0_invariants_mechanically_enforced(self):
        """P0 mechanical invariants evacuated from core/ (ADR-0054) must have active hooks and test coverage."""
        hooks_path = os.path.join(RUNTIMES_DIR, "antigravity", "hooks.json")
        self.assertTrue(os.path.isfile(hooks_path), f"Missing hooks file: {hooks_path}")
        with open(hooks_path, "r", encoding="utf-8") as f:
            hooks_data = json.load(f)

        # 1. Circuit breaker activo para herramientas de lectura
        cb_hooks = hooks_data.get("circuit-breaker", {}).get("PreToolUse", [])
        self.assertTrue(any("agent-circuit-breaker" in h.get("command", "") for item in cb_hooks for h in item.get("hooks", [])))

        # 2. Guard mecánico P0 activo para comandos y manipulación de archivos
        guard_hooks = hooks_data.get("guards", {}).get("PreToolUse", [])
        self.assertTrue(any("agent-guard" in h.get("command", "") for item in guard_hooks for h in item.get("hooks", [])))

        # 3. Binarios ejecutables presentes
        for bin_name in ("agent-guard", "agent-circuit-breaker"):
            bin_path = os.path.join(REPO_ROOT, "skills", "conversation-audit", "bin", bin_name)
            self.assertTrue(os.path.isfile(bin_path), f"Missing executable hook: {bin_path}")
            self.assertTrue(os.access(bin_path, os.X_OK), f"Hook not executable: {bin_path}")

    def test_procedural_rules_delegated_to_skills(self):
        """Procedural rules removed from core/ (ADR-0047, ADR-0048, #284) must live in skills (P1)."""
        provisioning = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "references", "repo-provisioning.md"
        )
        with open(provisioning, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Inicialización Local Proactiva", content)
        self.assertIn("Gate de Confirmación", content)

        # Procedural rules evacuated in #284
        workflow_skill = os.path.join(REPO_ROOT, "skills", "issue-driven-workflow", "SKILL.md")
        with open(workflow_skill, "r", encoding="utf-8") as f:
            workflow_content = f.read()
        self.assertIn("Fast-path", workflow_content)
        self.assertIn("Fast-Track", workflow_content)
        self.assertIn("Stop & Plan", workflow_content)
        self.assertIn("Precedencia de Entornos Locales", workflow_content)
        self.assertIn("Higiene, Pruebas y Atomicidad", workflow_content)

        lifecycle = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "references", "branch-lifecycle.md"
        )
        with open(lifecycle, "r", encoding="utf-8") as f:
            lifecycle_content = f.read()
        self.assertIn("Precedencia de Entornos Locales", lifecycle_content)
        self.assertIn("Higiene de Salida y Pruebas", lifecycle_content)
        self.assertIn("Lectura Quirúrgica en Dos Fases", lifecycle_content)

        backlog = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "references", "issue-backlog.md"
        )
        with open(backlog, "r", encoding="utf-8") as f:
            backlog_content = f.read()
        self.assertIn("N0", backlog_content)
        self.assertIn("N1", backlog_content)
        self.assertIn("N2", backlog_content)

        adr_skill = os.path.join(REPO_ROOT, "skills", "adr-manager", "SKILL.md")
        with open(adr_skill, "r", encoding="utf-8") as f:
            adr_content = f.read()
        self.assertIn("HISTORIAL.md", adr_content)
        self.assertIn("GEMINI.md", adr_content)

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
        """Execution profile labels and MBR matrix must be documented across skills and backlog reference."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        # ADR-0048 / #284: router delegates profile labels to issue-driven-workflow
        for label in ("profile:flash-low", "profile:flash-medium", "profile:flash-high", "profile:pro"):
            self.assertNotIn(label, router_content, f"Unexpected {label} remaining in core/00-router.md")

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
        for label in ("profile:flash-low", "profile:flash-medium", "profile:flash-high", "profile:pro"):
            self.assertIn(label, skill_content, f"Missing {label} in issue-driven-workflow SKILL.md")

    def test_pagination_and_atomic_edits_invariants(self):
        """Strict pagination in view_file and atomic granularity in replace_file_content are defined in P1 (ADR-0054)."""
        skill_path = os.path.join(REPO_ROOT, "skills", "issue-driven-workflow", "SKILL.md")
        with open(skill_path, "r", encoding="utf-8") as f:
            skill_content = f.read()
        self.assertIn("granularidad atómica", skill_content)
        self.assertIn("ventana ≤ 200 líneas", skill_content)

    def test_view_file_circuit_breaker_and_prompt_immunity_invariants(self):
        """core/00-router.md defines search circuit breaker; agent-circuit-breaker and lifecycle define read limits (ADR-0040, ADR-0048, ADR-0054)."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        self.assertIn("Circuit Breaker", router_content)

        cb_bin_path = os.path.join(
            REPO_ROOT, "skills", "conversation-audit", "bin", "agent-circuit-breaker"
        )
        with open(cb_bin_path, "r", encoding="utf-8") as f:
            cb_content = f.read()
        self.assertIn("DEFAULT_MAX_PASSIVE_READS = 6", cb_content)
        self.assertIn("lecturas pasivas", cb_content)
        self.assertIn("consecutivas", cb_content)

        lifecycle_ref_path = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "references", "branch-lifecycle.md"
        )
        with open(lifecycle_ref_path, "r", encoding="utf-8") as f:
            lifecycle_content = f.read()

        self.assertIn("Lectura Quirúrgica en Dos Fases", lifecycle_content)
        self.assertIn("búsqueda de contenido", lifecycle_content)
        self.assertIn("> 150 líneas", lifecycle_content)
        self.assertIn("≤ 50 líneas", lifecycle_content)
        self.assertIn("contenido no mostrado", lifecycle_content)

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

    def test_leantoken_precedence_in_core_router_and_compiled_prompts(self):
        """core/00-router.md and compiled prompts must enforce LeanToken precedence for transversal search (#315)."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            router_content = f.read()

        self.assertIn("leantoken.context", router_content)
        self.assertIn("leantoken.search", router_content)
        self.assertIn("investigación transversal", router_content)
        self.assertIn("exclusivas de herramientas nativas", router_content)

        for runtime in ("antigravity", "claude"):
            dist_prompt = os.path.join(DIST_DIR, runtime, "AGENTS.md")
            with open(dist_prompt, "r", encoding="utf-8") as f:
                prompt_content = f.read()
            self.assertIn("leantoken.context", prompt_content)
            self.assertIn("leantoken.search", prompt_content)
            self.assertIn("exclusivas de herramientas nativas", prompt_content)

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

    def test_basal_rules_admission_metadata(self):
        """All basal rules in core/*.md and runtimes/*/rules/*.md must have valid admission metadata (#286)."""
        rule_comment_pattern = re.compile(
            r"^<!--\s*rule:\s*id=([A-Za-z0-9_]+)\s+level=([A-Za-z0-9_/]+)\s+origin=(#[0-9]+|legacy)\s*-->$"
        )
        valid_levels = {"P0", "P1", "P2", "Build", "P0/P2", "P0/P1", "P1/P2"}
        root_bullet_pattern = re.compile(r"^([-*]|\d+\.)\s+")
        target_files = sorted(glob.glob(os.path.join(CORE_DIR, "*.md")))
        for rd in sorted(glob.glob(os.path.join(RUNTIMES_DIR, "*", "rules"))):
            target_files.extend(sorted(glob.glob(os.path.join(rd, "*.md"))))

        self.assertGreater(len(target_files), 0, "No basal target files found")
        seen_ids = set()
        total_rules = 0

        for file_path in target_files:
            rel = os.path.relpath(file_path, REPO_ROOT)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            pending_meta = None
            for idx, raw_line in enumerate(lines):
                line = raw_line.strip()
                lno = idx + 1
                if not line:
                    continue

                m = rule_comment_pattern.match(line)
                if m:
                    self.assertIsNone(
                        pending_meta,
                        f"Orphan metadata <!-- rule: id={pending_meta} ... --> at {rel}:{lno}"
                    )
                    pending_meta = {
                        "id": m.group(1),
                        "level": m.group(2),
                        "origin": m.group(3),
                        "line_no": lno,
                    }
                    continue

                is_root_bullet = bool(root_bullet_pattern.match(line)) and not raw_line.startswith("  ") and not raw_line.startswith("\t")
                if is_root_bullet:
                    total_rules += 1
                    self.assertIsNotNone(
                        pending_meta,
                        f"Rule at {rel}:{lno} lacks admission metadata comment: {line[:60]}"
                    )
                    rid = pending_meta["id"]
                    rlevel = pending_meta["level"]
                    self.assertNotIn(
                        rid, seen_ids,
                        f"Duplicate rule ID '{rid}' at {rel}:{pending_meta['line_no']}"
                    )
                    seen_ids.add(rid)
                    self.assertIn(
                        rlevel, valid_levels,
                        f"Invalid level '{rlevel}' for rule '{rid}' at {rel}:{pending_meta['line_no']}"
                    )
                    pending_meta = None
                    continue

                if pending_meta is not None:
                    self.fail(
                        f"Orphan metadata <!-- rule: id={pending_meta['id']} ... --> at {rel}:{pending_meta['line_no']} followed by non-bullet line {lno}: {line[:40]}"
                    )

            self.assertIsNone(
                pending_meta,
                f"Trailing metadata comment without associated rule at {rel}"
            )

        # 27 reglas basales tras evacuar 3 reglas P0 puras a hooks mecánicos (ADR-0054)
        self.assertGreaterEqual(total_rules, 27, f"Expected at least 27 audited rules, found {total_rules}")

    def test_p0_rules_word_budget_in_basal(self):
        """Rules marked P0 must not exceed the hard cap of 100 words in the basal prompt (#286, ADR-0048)."""
        rule_comment_pattern = re.compile(
            r"^<!--\s*rule:\s*id=([A-Za-z0-9_]+)\s+level=([A-Za-z0-9_/]+)\s+origin=(#[0-9]+|legacy)\s*-->$"
        )
        root_bullet_pattern = re.compile(r"^([-*]|\d+\.)\s+")
        target_files = sorted(glob.glob(os.path.join(CORE_DIR, "*.md")))
        for rd in sorted(glob.glob(os.path.join(RUNTIMES_DIR, "*", "rules"))):
            target_files.extend(sorted(glob.glob(os.path.join(rd, "*.md"))))

        for file_path in target_files:
            rel = os.path.relpath(file_path, REPO_ROOT)
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            pending_meta = None
            n = len(lines)
            for i in range(n):
                raw = lines[i]
                line = raw.strip()
                if not line:
                    continue

                m = rule_comment_pattern.match(line)
                if m:
                    pending_meta = {"id": m.group(1), "level": m.group(2), "line_no": i + 1}
                    continue

                is_root_bullet = bool(root_bullet_pattern.match(line)) and not raw.startswith("  ") and not raw.startswith("\t")
                if is_root_bullet:
                    if pending_meta and "P0" in pending_meta["level"].split("/"):
                        rid = pending_meta["id"]
                        rule_lines = [line]
                        saw_blank = False
                        for j in range(i + 1, n):
                            next_raw = lines[j]
                            next_line = next_raw.strip()
                            if not next_line:
                                saw_blank = True
                                continue
                            if rule_comment_pattern.match(next_line):
                                break
                            if next_line.startswith("#"):
                                break
                            is_next_root = bool(root_bullet_pattern.match(next_line)) and not next_raw.startswith("  ") and not next_raw.startswith("\t")
                            if is_next_root:
                                break
                            if saw_blank and not next_raw.startswith(" ") and not next_raw.startswith("\t"):
                                break
                            rule_lines.append(next_line)
                            saw_blank = False
                        rule_words_count = len(" ".join(rule_lines).split())
                        self.assertLessEqual(
                            rule_words_count, 100,
                            f"P0 rule '{rid}' in {rel}:{i + 1} exceeds hard cap of 100 words ({rule_words_count} words)"
                        )
                    pending_meta = None

    def test_compiled_dist_strips_rule_metadata_comments(self):
        """Compiled AGENTS.md in dist/ must not contain rule metadata comments (#286)."""
        for runtime in ("antigravity", "claude"):
            dist_file = os.path.join(DIST_DIR, runtime, "AGENTS.md")
            self.assertTrue(os.path.isfile(dist_file), f"Missing compiled artifact: {dist_file}")
            with open(dist_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("<!-- rule:", content, f"Rule metadata comment leaked in {dist_file}")
            self.assertNotIn("rule: id=", content, f"Rule metadata identifier leaked in {dist_file}")

    def test_admission_validation_negative_cases(self):
        """Admission check in lib/check.sh must reject missing metadata, multiline P0, invalid level, duplicate ID (#286)."""
        check_script = os.path.join(REPO_ROOT, "lib", "check.sh")
        self.assertTrue(os.path.isfile(check_script))

        with tempfile.TemporaryDirectory() as tmpdir:
            core_dir = os.path.join(tmpdir, "core")
            os.makedirs(core_dir)

            def run_check(extra_env=None):
                prefix = ""
                if extra_env:
                    prefix = " ".join(f'{k}="{v}"' for k, v in extra_env.items()) + " "
                cmd = [
                    "bash", "-c",
                    f'{prefix}source "{REPO_ROOT}/lib/common.sh" && source "{check_script}" && SCRIPT_DIR="{tmpdir}" CHECK_ERRORS=0 CHECK_WARNINGS=0 && check_basal_rules_admission; echo "CHECK_ERRORS:$CHECK_ERRORS"; echo "CHECK_WARNINGS:$CHECK_WARNINGS"'
                ]
                return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Caso 1: Regla sin metadatos
            f1 = os.path.join(core_dir, "00-test.md")
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write("# Header\n\n- **Regla Sin Meta:** Contenido de prueba.\n")
            res = run_check()
            self.assertIn("sin metadatos de admisión", res.stderr)
            self.assertNotIn("CHECK_ERRORS:0", res.stdout)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 1b: Reglas con bullets alternativos (* y 1.) sin metadatos
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write("# Header\n\n* **Regla Asterisco:** Contenido.\n")
            res = run_check()
            self.assertIn("sin metadatos de admisión", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            with open(f1, "w", encoding="utf-8") as fp:
                fp.write("# Header\n\n1. **Regla Numerada:** Contenido.\n")
            res = run_check()
            self.assertIn("sin metadatos de admisión", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 2: Regla P0 que supera el techo de 100 palabras
            too_long_p0 = " ".join(["palabra"] * 105)
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_P0_TEST level=P0 origin=legacy -->\n"
                    f"- **Regla P0 Larga:** {too_long_p0}\n"
                )
            res = run_check()
            self.assertIn("Regla P0 \"RULE_P0_TEST\"", res.stderr)
            self.assertIn("supera el techo transitorio de 100 palabras", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 2b: Regla mixta con componente P0 que supera el techo de 100 palabras
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_P0_MIXED level=P0/P2 origin=legacy -->\n"
                    f"- **Regla P0 Mixta:** {too_long_p0}\n"
                )
            res = run_check()
            self.assertIn("Regla P0 \"RULE_P0_MIXED\"", res.stderr)
            self.assertIn("supera el techo transitorio de 100 palabras", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 3: Nivel inválido
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_INVALID_LEVEL level=P9 origin=legacy -->\n"
                    "- **Regla Nivel Inválido:** Contenido de prueba.\n"
                )
            res = run_check()
            self.assertIn("Nivel inválido \"P9\"", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 4: ID duplicado
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_DUP level=P2 origin=legacy -->\n"
                    "- **Regla 1:** Contenido.\n"
                    "<!-- rule: id=RULE_DUP level=P2 origin=legacy -->\n"
                    "- **Regla 2:** Contenido duplicado.\n"
                )
            res = run_check()
            self.assertIn("ID de regla duplicado \"RULE_DUP\"", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 5: Metadato huérfano antes de encabezado
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_ORPHAN_HEADER level=P2 origin=legacy -->\n"
                    "## Nueva Seccion\n"
                    "- **Regla:** Contenido.\n"
                )
            res = run_check()
            self.assertIn("antes de encabezado de sección", res.stderr)
            self.assertIn("CHECK_ERRORS:2", res.stdout)  # 1 huérfano + 1 regla sin meta

            # Caso 6: Metadato huérfano seguido de texto plano
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_ORPHAN_TEXT level=P2 origin=legacy -->\n"
                    "Este es un párrafo de texto plano, no una regla con viñeta.\n"
                )
            res = run_check()
            self.assertIn("seguido de texto no-bullet", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 7: Ausencia de python3
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_OK level=P2 origin=legacy -->\n"
                    "- **Regla OK:** Contenido.\n"
                )
            cmd_no_py = [
                "bash", "-c",
                f'source "{REPO_ROOT}/lib/common.sh" && source "{check_script}" && SCRIPT_DIR="{tmpdir}" CHECK_ERRORS=0 && export PATH="/usr/local/bin-empty" && check_basal_rules_admission; echo "CHECK_ERRORS:$CHECK_ERRORS"'
            ]
            res = subprocess.run(cmd_no_py, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertIn("python3 no está disponible", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 8: Python termina con excepción o exit code != 0 (Punto 3)
            tmp_bin = os.path.join(tmpdir, "fake_bin")
            os.makedirs(tmp_bin, exist_ok=True)
            fake_py = os.path.join(tmp_bin, "python3")
            with open(fake_py, "w", encoding="utf-8") as fp:
                fp.write("#!/bin/sh\necho 'Traceback (most recent call last): Exception' >&2\nexit 2\n")
            os.chmod(fake_py, 0o755)

            cmd_py_err = [
                "bash", "-c",
                f'source "{REPO_ROOT}/lib/common.sh" && source "{check_script}" && SCRIPT_DIR="{tmpdir}" CHECK_ERRORS=0 && export PATH="{tmp_bin}:$PATH" && check_basal_rules_admission; echo "CHECK_ERRORS:$CHECK_ERRORS"'
            ]
            res = subprocess.run(cmd_py_err, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertIn("Error ejecutando auditoría de reglas basales", res.stderr)
            self.assertIn("exit code 2", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 9: Python no emite línea COUNT: (Punto 3)
            with open(fake_py, "w", encoding="utf-8") as fp:
                fp.write("#!/bin/sh\necho 'NO_COUNT_OUTPUT'\nexit 0\n")
            os.chmod(fake_py, 0o755)

            res = subprocess.run(cmd_py_err, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            self.assertIn("no retornó conteo de reglas (COUNT:)", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 10: Advertencia de palabras P0 > 30 (sin error en CHECK_ERRORS, con incremento en CHECK_WARNINGS)
            long_p0_text = " ".join(["palabra"] * 35)
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_P0_LONG level=P0 origin=legacy -->\n"
                    f"- **Regla Larga:** {long_p0_text}\n"
                )
            res = run_check()
            self.assertIn("supera límite recomendado de palabras residuales", res.stdout)
            self.assertIn("CHECK_ERRORS:0", res.stdout)
            self.assertIn("CHECK_WARNINGS:1", res.stdout)

            # Caso 11: Párrafo libre tras línea en blanco no contamina el conteo de la regla anterior (Hallazgo D)
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write(
                    "# Header\n\n"
                    "<!-- rule: id=RULE_P0_ISOLATED level=P0 origin=legacy -->\n"
                    "- **Regla Aislada:** Contenido breve de diez palabras exactamente para prueba.\n\n"
                    "Este es un párrafo de texto libre descolgado que no debe ser absorbido por la regla anterior.\n"
                )
            res = run_check()
            self.assertNotIn("supera el techo transitorio de 100 palabras", res.stderr)
            self.assertNotIn("supera límite recomendado de palabras residuales", res.stdout)
            self.assertIn("CHECK_ERRORS:0", res.stdout)
            self.assertIn("CHECK_WARNINGS:0", res.stdout)

            # Caso 12: Regla P0 pura multilínea es error (#286, ADR-0049)
            multiline_rule = (
                "- **Regla Multilínea:**\n"
                "  - Primera sub-viñeta breve.\n"
                "  - Segunda sub-viñeta breve.\n"
            )
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write("# Header\n\n<!-- rule: id=RULE_P0_MULTI level=P0 origin=legacy -->\n" + multiline_rule)
            res = run_check()
            self.assertIn("conserva más de una línea en el basal (3 líneas)", res.stderr)
            self.assertIn("CHECK_ERRORS:1", res.stdout)

            # Caso 13: Regla mixta multilínea pendiente de evacuación es advertencia (ADR-0049)
            with open(f1, "w", encoding="utf-8") as fp:
                fp.write("# Header\n\n<!-- rule: id=RULE_MIXED_MULTI level=P0/P2 origin=legacy -->\n" + multiline_rule)
            res = run_check()
            self.assertIn("pendiente de evacuación de su componente P0", res.stdout)
            self.assertIn("CHECK_ERRORS:0", res.stdout)
            self.assertIn("CHECK_WARNINGS:1", res.stdout)


if __name__ == "__main__":
    unittest.main()

