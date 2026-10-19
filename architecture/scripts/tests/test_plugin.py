"""Packaging consistency of the `architecture-tools` Claude Code plugin.

The plugin root is `architecture/` (`.claude-plugin/plugin.json`); the repo
root carries the marketplace (`.claude-plugin/marketplace.json`). Nothing is
generated, so these tests catch drift between the manifests and the tree
(design-decisions.md, "Amendments (2026-10-19, plugin distribution)").
"""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PLUGIN_ROOT.parent
SCRIPTS = PLUGIN_ROOT / "scripts"
BIN = PLUGIN_ROOT / "bin"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class TestManifests(unittest.TestCase):
    def setUp(self):
        self.plugin = load_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
        self.marketplace = load_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")

    def test_marketplace_points_at_plugin_root(self):
        (entry,) = self.marketplace["plugins"]
        self.assertEqual(entry["name"], self.plugin["name"])
        self.assertEqual((REPO_ROOT / entry["source"]).resolve(), PLUGIN_ROOT)

    def test_agents_use_default_directory_scan(self):
        # A custom `agents` key would replace the scan of agents/.
        self.assertNotIn("agents", self.plugin)
        self.assertTrue(any((PLUGIN_ROOT / "agents").glob("*.md")))

    def test_skills_dir_holds_only_skill_folders(self):
        skills = PLUGIN_ROOT / self.plugin["skills"]
        for child in skills.iterdir():
            if child.is_dir():
                self.assertTrue((child / "SKILL.md").is_file(), child)

    def test_version_is_semver(self):
        self.assertRegex(self.plugin["version"], r"^\d+\.\d+\.\d+$")

    def test_repo_disables_its_own_plugin(self):
        # CLAUDE.md: the tools must not be used for work on this repository.
        settings = load_json(REPO_ROOT / ".claude" / "settings.json")
        key = f"{self.plugin['name']}@{self.marketplace['name']}"
        self.assertIs(settings["enabledPlugins"][key], False)


class TestBinWrappers(unittest.TestCase):
    def test_one_executable_wrapper_per_cli(self):
        clis = {p.stem for p in SCRIPTS.glob("*ctl.py")}
        wrappers = {p.name for p in BIN.iterdir()}
        self.assertEqual(wrappers, clis)
        for name in wrappers:
            self.assertTrue(os.access(BIN / name, os.X_OK), name)

    def test_wrapper_runs_cli_through_symlink_from_foreign_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "rulectl"
            link.symlink_to(BIN / "rulectl")
            result = subprocess.run(
                [str(link), "--help"], cwd=tmp, capture_output=True, text=True
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("usage: rulectl"))

    def test_skills_reference_bare_cli_names_only(self):
        for skill in (PLUGIN_ROOT / "skills").glob("*/SKILL.md"):
            text = skill.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"scripts/\w+ctl\.py", text), skill)


if __name__ == "__main__":
    unittest.main()
