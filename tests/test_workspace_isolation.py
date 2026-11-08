#!/usr/bin/env python3
"""
Unit tests for domain MCP isolation, workspace templating, and global profile purity (ADR-0039, Issue #170).
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUNTIMES_DIR = os.path.join(REPO_ROOT, "runtimes")
MODULES_DIR = os.path.join(REPO_ROOT, "modules")
DIST_DIR = os.path.join(REPO_ROOT, "dist")
BUILD_SH = os.path.join(REPO_ROOT, "build.sh")


def setUpModule():
    from dist_support import ensure_dist
    ensure_dist()


class TestWorkspaceIsolation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_global_antigravity_mcp_servers_purity(self):
        """runtimes/antigravity/config.json must only declare transversal servers (leantoken) and no domain servers (ADR-0039, ADR-0053)."""
        cfg_path = os.path.join(RUNTIMES_DIR, "antigravity", "config.json")
        self.assertTrue(os.path.isfile(cfg_path))
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg.get("mcp_servers"), ["leantoken"], "Global antigravity mcp_servers must declare ['leantoken']")

    def test_global_dist_mcp_config_compilation(self):
        """dist/antigravity/mcp_config.json must compile with leantoken configured (ADR-0053)."""
        mcp_path = os.path.join(DIST_DIR, "antigravity", "mcp_config.json")
        self.assertTrue(os.path.isfile(mcp_path))
        with open(mcp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("leantoken", data.get("mcpServers", {}), "dist/antigravity/mcp_config.json must contain leantoken")

    def test_global_skills_purity_no_domain_skills(self):
        """runtimes/antigravity/config.json must not declare domain skills or binaries (ADR-0041, #176)."""
        cfg_path = os.path.join(RUNTIMES_DIR, "antigravity", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertNotIn(
            "eso-addon-development",
            cfg.get("skills", []),
            "eso-addon-development domain skill must not be in global skills",
        )
        self.assertNotIn(
            "eso-build",
            cfg.get("binaries", {}).values(),
            "eso-build domain binary must not be in global binaries",
        )
        self.assertIn(
            "agent-module",
            cfg.get("binaries", {}),
            "agent-module binary alias must be registered",
        )

    def test_module_eso_schema_validity(self):
        """modules/eso/module.json must exist and satisfy module-config schema requirements."""
        mod_path = os.path.join(MODULES_DIR, "eso", "module.json")
        schema_path = os.path.join(RUNTIMES_DIR, "schema", "module-config.schema.json")
        self.assertTrue(os.path.isfile(mod_path), "modules/eso/module.json must exist")
        self.assertTrue(os.path.isfile(schema_path), "module-config.schema.json must exist")

        with open(mod_path, "r", encoding="utf-8") as f:
            mod = json.load(f)
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        for req in schema.get("required", []):
            self.assertIn(req, mod, f"Property '{req}' required by schema")

        self.assertEqual(mod.get("name"), "eso")
        self.assertIn("eso-addon-development", mod.get("skills", []))
        self.assertIn("eso-mcp-server", mod.get("mcp_servers", []))

    def test_eso_workspace_template_validity(self):
        """Template files in modules/eso/template must be syntactically valid JSON."""
        plugin_json = os.path.join(
            MODULES_DIR, "eso", "template", ".agents", "plugins", "eso-addon-suite", "plugin.json"
        )
        mcp_config = os.path.join(
            MODULES_DIR, "eso", "template", ".agents", "plugins", "eso-addon-suite", "mcp_config.json"
        )
        mcp_claude = os.path.join(MODULES_DIR, "eso", "template", ".mcp.json")

        self.assertTrue(os.path.isfile(plugin_json))
        self.assertTrue(os.path.isfile(mcp_config))
        self.assertTrue(os.path.isfile(mcp_claude))

        with open(plugin_json, "r", encoding="utf-8") as f:
            p_data = json.load(f)
        self.assertEqual(p_data.get("name"), "eso-addon-suite")

        with open(mcp_config, "r", encoding="utf-8") as f:
            m_data = json.load(f)
        self.assertIn("eso-mcp-server", m_data.get("mcpServers", {}))

        with open(mcp_claude, "r", encoding="utf-8") as f:
            c_data = json.load(f)
        self.assertIn("eso-mcp-server", c_data.get("mcpServers", {}))

    def test_cmd_workspace_scaffolding(self):
        """build.sh workspace eso <target_dir> must provision template files and skills into destination."""
        target = os.path.join(self.temp_dir, "my-eso-addon")
        res = subprocess.run([BUILD_SH, "workspace", "eso", target], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"workspace command failed: {res.stderr}")

        dest_plugin = os.path.join(target, ".agents", "plugins", "eso-addon-suite", "plugin.json")
        dest_mcp = os.path.join(target, ".agents", "plugins", "eso-addon-suite", "mcp_config.json")
        dest_claude = os.path.join(target, ".mcp.json")
        dest_skill_ag = os.path.join(target, ".agents", "skills", "eso-addon-development", "SKILL.md")
        dest_skill_gm = os.path.join(target, ".gemini", "skills", "eso-addon-development", "SKILL.md")
        dest_skill_cl = os.path.join(target, ".claude", "skills", "eso-addon-development", "SKILL.md")

        self.assertTrue(os.path.isfile(dest_plugin), f"Missing {dest_plugin}")
        self.assertTrue(os.path.isfile(dest_mcp), f"Missing {dest_mcp}")
        self.assertTrue(os.path.isfile(dest_claude), f"Missing {dest_claude}")
        self.assertTrue(os.path.isfile(dest_skill_ag), f"Missing {dest_skill_ag}")
        self.assertTrue(os.path.isfile(dest_skill_gm), f"Missing {dest_skill_gm}")
        self.assertTrue(os.path.isfile(dest_skill_cl), f"Missing {dest_skill_cl}")

    def test_agent_module_cli_lifecycle(self):
        """agent-module list, status, enable, disable lifecycle operations."""
        agent_module_bin = os.path.join(
            REPO_ROOT, "skills", "issue-driven-workflow", "bin", "agent-module"
        )
        self.assertTrue(os.path.isfile(agent_module_bin))
        self.assertTrue(os.access(agent_module_bin, os.X_OK))

        # 1. list
        res_list = subprocess.run([agent_module_bin, "list"], capture_output=True, text=True)
        self.assertEqual(res_list.returncode, 0)
        self.assertIn("eso:", res_list.stdout)

        # 2. status on empty dir
        target = os.path.join(self.temp_dir, "test-agent-module-repo")
        os.makedirs(target, exist_ok=True)
        res_status = subprocess.run([agent_module_bin, "status", target], capture_output=True, text=True)
        self.assertEqual(res_status.returncode, 0)
        self.assertIn("inactivo", res_status.stdout)

        # 3. enable eso
        res_enable = subprocess.run([agent_module_bin, "enable", "eso", target], capture_output=True, text=True)
        self.assertEqual(res_enable.returncode, 0)
        self.assertTrue(os.path.isfile(os.path.join(target, ".agents", "skills", "eso-addon-development", "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(target, ".gemini", "skills", "eso-addon-development", "SKILL.md")))
        self.assertTrue(os.path.isfile(os.path.join(target, ".claude", "skills", "eso-addon-development", "SKILL.md")))

        # 4. status on enabled dir
        res_status_enabled = subprocess.run([agent_module_bin, "status", target], capture_output=True, text=True)
        self.assertEqual(res_status_enabled.returncode, 0)
        self.assertIn("ACTIVO", res_status_enabled.stdout)

        # 5. disable eso
        res_disable = subprocess.run([agent_module_bin, "disable", "eso", target], capture_output=True, text=True)
        self.assertEqual(res_disable.returncode, 0)
        self.assertFalse(os.path.lexists(os.path.join(target, ".agents", "skills", "eso-addon-development")))
        self.assertFalse(os.path.lexists(os.path.join(target, ".gemini", "skills", "eso-addon-development")))
        self.assertFalse(os.path.lexists(os.path.join(target, ".claude", "skills", "eso-addon-development")))


if __name__ == "__main__":
    unittest.main()
