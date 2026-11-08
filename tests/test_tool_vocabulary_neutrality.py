#!/usr/bin/env python3
"""
Unit tests for tool vocabulary neutrality and cross-runtime purity in compiled prompts (ADR-0050, Issue #288).
"""

import os
import re
import sys
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CORE_DIR = os.path.join(REPO_ROOT, "core")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
RUNTIMES_DIR = os.path.join(REPO_ROOT, "runtimes")
LIB_DIR = os.path.join(REPO_ROOT, "lib")
if LIB_DIR not in sys.path:
    sys.path.insert(0, LIB_DIR)

from tool_vocabulary import (
    CLAUDE_SPECIFIC_TOKENS,
    CONDITIONED_SUBAGENT_TOKENS,
    EXCLUDED_SKILLS_FILES,
    FORBIDDEN_CORE_TOOLS,
    FORBIDDEN_PARAMS,
    FORBIDDEN_SKILLS_TOOLS,
    FOREIGN_TOOLS_BY_RUNTIME,
    PLACEHOLDER_PATTERN,
    check_tool_vocabulary,
    validate_compiled_prompts,
    validate_core_router,
    validate_skills_file_content,
    validate_skills_prose,
)


def setUpModule():
    from dist_support import ensure_dist
    ensure_dist()


class TestToolVocabularyNeutrality(unittest.TestCase):

    def test_core_router_has_no_runtime_tool_names(self):
        """core/00-router.md must use neutral functional vocabulary without runtime-specific tool names."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            content = f.read()

        for tool in FORBIDDEN_CORE_TOOLS:
            match = re.search(r"\b" + re.escape(tool) + r"\b", content)
            self.assertIsNone(
                match,
                f"core/00-router.md must not mention runtime tool '{tool}' (use neutral vocabulary, ADR-0050)"
            )

    def test_claude_rules_no_tool_equivalences(self):
        """runtimes/claude/rules/01-claude-tools.md must not contain CLAUDE_TOOL_EQUIVALENCES."""
        claude_tools_path = os.path.join(RUNTIMES_DIR, "claude", "rules", "01-claude-tools.md")
        with open(claude_tools_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertNotIn("CLAUDE_TOOL_EQUIVALENCES", content)
        self.assertNotIn("Equivalencias de Herramientas", content)

    def test_compiled_prompts_have_no_unresolved_placeholders(self):
        """Compiled prompts in dist/ must not contain any unresolved {{...}} placeholders."""
        for r_name in ("antigravity", "claude"):
            prompt_file = os.path.join(DIST_DIR, r_name, "AGENTS.md")
            self.assertTrue(os.path.isfile(prompt_file), f"Compiled prompt missing: {prompt_file}")
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            placeholders = PLACEHOLDER_PATTERN.findall(content)
            self.assertEqual(
                placeholders, [],
                f"Unresolved placeholders found in dist/{r_name}/AGENTS.md: {placeholders}"
            )

    def test_claude_compiled_prompt_has_no_antigravity_tools(self):
        """dist/claude/AGENTS.md must not contain Antigravity-specific tool names."""
        prompt_file = os.path.join(DIST_DIR, "claude", "AGENTS.md")
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        antigravity_tools = FOREIGN_TOOLS_BY_RUNTIME["claude"]
        for tool in antigravity_tools:
            match = re.search(r"\b" + re.escape(tool) + r"\b", content)
            self.assertIsNone(
                match,
                f"dist/claude/AGENTS.md must not contain foreign tool '{tool}' from Antigravity"
            )

    def test_antigravity_compiled_prompt_has_no_claude_tools(self):
        """dist/antigravity/AGENTS.md must not contain Claude-specific tool references."""
        prompt_file = os.path.join(DIST_DIR, "antigravity", "AGENTS.md")
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        claude_specific_tokens = FOREIGN_TOOLS_BY_RUNTIME["antigravity"]
        for token in claude_specific_tokens:
            self.assertNotIn(
                token,
                content,
                f"dist/antigravity/AGENTS.md must not contain Claude-specific tool reference {token}"
            )

    def test_skills_normative_prose_tool_vocabulary_neutrality(self):
        """Markdown files in skills/ must use neutral vocabulary without unconditioned runtime-specific tool names (ADR-0050, Issue #292)."""
        skills_dir = os.path.join(REPO_ROOT, "skills")
        self.assertTrue(os.path.isdir(skills_dir), f"Skills directory not found: {skills_dir}")

        for root, dirs, files in os.walk(skills_dir):
            dirs[:] = [d for d in dirs if d not in ("bin", "scripts", "tests", "__pycache__")]
            for f in sorted(files):
                if not f.endswith(".md"):
                    continue
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, REPO_ROOT)
                if rel_path in EXCLUDED_SKILLS_FILES:
                    continue

                with open(file_path, "r", encoding="utf-8") as fp:
                    content = fp.read()

                for tool in FORBIDDEN_SKILLS_TOOLS:
                    match = re.search(r"\b" + re.escape(tool) + r"\b", content)
                    self.assertIsNone(
                        match,
                        f"Normative skill file '{rel_path}' contains runtime tool '{tool}'. Use neutral vocabulary (ADR-0050, Issue #292)."
                    )

                for token in CLAUDE_SPECIFIC_TOKENS:
                    self.assertNotIn(
                        token,
                        content,
                        f"Normative skill file '{rel_path}' contains Claude tool token '{token}'. Use neutral vocabulary (ADR-0050, Issue #292)."
                    )

                for param in FORBIDDEN_PARAMS:
                    match = re.search(r"\b" + re.escape(param) + r"\b", content)
                    self.assertIsNone(
                        match,
                        f"Normative skill file '{rel_path}' contains runtime parameter '{param}'. Use neutral vocabulary (ADR-0050, Issue #292)."
                    )

                in_fence = False
                for idx, line in enumerate(content.splitlines(), 1):
                    if line.lstrip().startswith("```"):
                        in_fence = not in_fence
                    conditioned = "Antigravity" in line or "antigravity" in line
                    if re.search(r"\bBypassSandbox\b", line):
                        self.assertTrue(
                            conditioned,
                            f"Normative skill file '{rel_path}:{idx}' mentions unconditioned 'BypassSandbox'. Must be conditioned to runtime (Issue #292)."
                        )
                    if in_fence or conditioned:
                        continue
                    for token in CONDITIONED_SUBAGENT_TOKENS:
                        self.assertIsNone(
                            re.search(r"\b" + re.escape(token) + r"\b", line),
                            f"Normative skill file '{rel_path}:{idx}' mentions unconditioned '{token}'. Must be conditioned to runtime (Issue #292)."
                        )

    def test_shared_validator_check_tool_vocabulary_passes_cleanly(self):
        """Unified check_tool_vocabulary validator must pass on current repository without errors."""
        errors, _warnings = check_tool_vocabulary(REPO_ROOT)
        self.assertEqual(errors, [], f"check_tool_vocabulary returned unexpected errors: {errors}")

    def test_validate_skills_file_content_detects_violations(self):
        """validate_skills_file_content must catch forbidden tools, tokens, params, and unconditioned terms."""
        content = (
            "Para editar usa view_file.\n"
            "También `Read` para leer.\n"
            "Especifica StartLine para paginar.\n"
            "Llama a BypassSandbox sin condicionar.\n"
            "Invoca invoke_subagent directamente.\n"
        )
        errors = validate_skills_file_content(content, "test_skill.md")
        self.assertTrue(any("view_file" in e for e in errors))
        self.assertTrue(any("`Read`" in e for e in errors))
        self.assertTrue(any("StartLine" in e for e in errors))
        self.assertTrue(any("BypassSandbox" in e for e in errors))
        self.assertTrue(any("invoke_subagent" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
