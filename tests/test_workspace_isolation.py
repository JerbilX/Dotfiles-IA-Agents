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


class TestWorkspaceIsolation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_global_antigravity_mcp_servers_empty(self):
        """runtimes/antigravity/config.json must declare empty mcp_servers to avoid token waste."""
        cfg_path = os.path.join(RUNTIMES_DIR, "antigravity", "config.json")
        self.assertTrue(os.path.isfile(cfg_path))
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg.get("mcp_servers"), [], "Global antigravity mcp_servers must be empty list")

    def test_global_dist_mcp_config_is_empty(self):
        """dist/antigravity/mcp_config.json must compile with empty mcpServers."""
        mcp_path = os.path.join(DIST_DIR, "antigravity", "mcp_config.json")
        self.assertTrue(os.path.isfile(mcp_path))
        with open(mcp_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, {"mcpServers": {}}, "dist/antigravity/mcp_config.json must have empty mcpServers")

    def test_skill_eso_addon_development_present(self):
        """eso-addon-development must remain enabled in runtimes/antigravity/config.json on-demand."""
        cfg_path = os.path.join(RUNTIMES_DIR, "antigravity", "config.json")
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertIn("eso-addon-development", cfg.get("skills", []), "eso-addon-development skill must be preserved")

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
        """build.sh workspace eso <target_dir> must provision template files into destination."""
        target = os.path.join(self.temp_dir, "my-eso-addon")
        res = subprocess.run([BUILD_SH, "workspace", "eso", target], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"workspace command failed: {res.stderr}")

        dest_plugin = os.path.join(target, ".agents", "plugins", "eso-addon-suite", "plugin.json")
        dest_mcp = os.path.join(target, ".agents", "plugins", "eso-addon-suite", "mcp_config.json")
        dest_claude = os.path.join(target, ".mcp.json")

        self.assertTrue(os.path.isfile(dest_plugin), f"Missing {dest_plugin}")
        self.assertTrue(os.path.isfile(dest_mcp), f"Missing {dest_mcp}")
        self.assertTrue(os.path.isfile(dest_claude), f"Missing {dest_claude}")


if __name__ == "__main__":
    unittest.main()
