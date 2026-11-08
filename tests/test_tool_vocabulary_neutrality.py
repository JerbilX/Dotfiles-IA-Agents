#!/usr/bin/env python3
"""
Unit tests for tool vocabulary neutrality and cross-runtime purity in compiled prompts (ADR-0050, Issue #288).
"""

import os
import re
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CORE_DIR = os.path.join(REPO_ROOT, "core")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
RUNTIMES_DIR = os.path.join(REPO_ROOT, "runtimes")


def setUpModule():
    from dist_support import ensure_dist
    ensure_dist()


class TestToolVocabularyNeutrality(unittest.TestCase):

    def test_core_router_has_no_runtime_tool_names(self):
        """core/00-router.md must use neutral functional vocabulary without runtime-specific tool names."""
        router_path = os.path.join(CORE_DIR, "00-router.md")
        with open(router_path, "r", encoding="utf-8") as f:
            content = f.read()

        forbidden_tools = [
            "view_file",
            "replace_file_content",
            "write_to_file",
            "grep_search",
            "find_by_name",
            "read_url_content",
        ]
        for tool in forbidden_tools:
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
        placeholder_pattern = re.compile(r"\{\{([a-zA-Z0-9_.-]+)\}\}")
        for r_name in ("antigravity", "claude"):
            prompt_file = os.path.join(DIST_DIR, r_name, "AGENTS.md")
            self.assertTrue(os.path.isfile(prompt_file), f"Compiled prompt missing: {prompt_file}")
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
            placeholders = placeholder_pattern.findall(content)
            self.assertEqual(
                placeholders, [],
                f"Unresolved placeholders found in dist/{r_name}/AGENTS.md: {placeholders}"
            )

    def test_claude_compiled_prompt_has_no_antigravity_tools(self):
        """dist/claude/AGENTS.md must not contain Antigravity-specific tool names."""
        prompt_file = os.path.join(DIST_DIR, "claude", "AGENTS.md")
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Mantener sincronizado con foreign_tools_by_runtime en lib/check.sh
        antigravity_tools = [
            "view_file",
            "replace_file_content",
            "grep_search",
            "find_by_name",
            "write_to_file",
            "run_command",
            "read_url_content",
            "ask_question",
        ]
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

        # Mantener sincronizado con foreign_tools_by_runtime en lib/check.sh
        claude_specific_tokens = ["`Read`", "`Grep`", "`Glob`", "`Write`", "`Edit`", "`Bash`"]
        for token in claude_specific_tokens:
            self.assertNotIn(
                token,
                content,
                f"dist/antigravity/AGENTS.md must not contain Claude-specific tool reference {token}"
            )

    def test_skills_normative_prose_tool_vocabulary_neutrality(self):
        """Markdown files in skills/ must use neutral vocabulary without unconditioned runtime-specific tool names (ADR-0050, Issue #292)."""
        skills_dir = os.path.join(REPO_ROOT, "skills")
        forbidden_tools = [
            "view_file",
            "replace_file_content",
            "grep_search",
            "find_by_name",
            "write_to_file",
            "read_url_content",
            "ask_question",
            "list_dir",
            "run_command",
        ]
        claude_specific_tokens = ["`Read`", "`Grep`", "`Glob`", "`Write`", "`Edit`", "`Bash`"]
        forbidden_params = ["StartLine", "EndLine"]
        # Antigravity subagent mechanisms: allowed only when conditioned on the same line
        # (outside code fences, which illustrate the invocation under a conditioned heading).
        conditioned_subagent_tokens = ["invoke_subagent", "manage_subagents", "TypeName"]
        # Files whose tool names are data (real traces), not instructions.
        excluded_files = set()

        self.assertTrue(os.path.isdir(skills_dir), f"Skills directory not found: {skills_dir}")

        for root, dirs, files in os.walk(skills_dir):
            dirs[:] = [d for d in dirs if d not in ("bin", "scripts", "tests", "__pycache__")]
            for f in sorted(files):
                if not f.endswith(".md"):
                    continue
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, REPO_ROOT)
                if rel_path in excluded_files:
                    continue

                with open(file_path, "r", encoding="utf-8") as fp:
                    content = fp.read()

                for tool in forbidden_tools:
                    match = re.search(r"\b" + re.escape(tool) + r"\b", content)
                    self.assertIsNone(
                        match,
                        f"Normative skill file '{rel_path}' contains runtime tool '{tool}'. Use neutral vocabulary (ADR-0050, Issue #292)."
                    )

                for token in claude_specific_tokens:
                    self.assertNotIn(
                        token,
                        content,
                        f"Normative skill file '{rel_path}' contains Claude tool token '{token}'. Use neutral vocabulary (ADR-0050, Issue #292)."
                    )

                for param in forbidden_params:
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
                    for token in conditioned_subagent_tokens:
                        self.assertIsNone(
                            re.search(r"\b" + re.escape(token) + r"\b", line),
                            f"Normative skill file '{rel_path}:{idx}' mentions unconditioned '{token}'. Must be conditioned to runtime (Issue #292)."
                        )


if __name__ == "__main__":
    unittest.main()
