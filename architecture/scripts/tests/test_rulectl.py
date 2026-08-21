import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import rulectl
import taskctl


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rulectl.main(argv)
    return code, out.getvalue(), err.getvalue()


def run_taskctl(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = taskctl.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestEndToEnd(unittest.TestCase):
    def test_three_level_metagroup_and_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            self.assertEqual(run(["--root", root, "add-language", "Python"])[0], 0)
            self.assertEqual(run(["--root", root, "add-context", "Python/001-backend"])[0], 0)
            self.assertEqual(
                run(["--root", root, "add-category", "Python/001-backend/001-validation"])[0], 0
            )
            code, out, _err = run(
                [
                    "--root", root, "--json", "add", "--name", "No bare except",
                    "--category", "Python/001-backend/001-validation",
                    "--description", "Explain the rule.", "--procedure", "Run ruff.",
                    "--weight", "high", "--tool", "ruff",
                ]
            )
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["status"], "active")
            self.assertEqual(data["metainfo"], {"weight": "high", "tool": "ruff"})
            self.assertEqual(data["content"]["Procedure"], "Run ruff.")

    def test_default_status_is_active_without_draft_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            run(["--root", root, "add-language", "Python"])
            code, out, _err = run(
                ["--root", root, "--json", "add", "--name", "Rule", "--language", "Python"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "active")

    def test_status_change_unrestricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            run(["--root", root, "add-language", "Python"])
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Rule", "--language", "Python"])
            object_id = json.loads(out)["id"]
            # active -> obsolete directly, no validator restricting it
            code, _out, _err = run(["--root", root, "set-status", object_id, "obsolete"])
            self.assertEqual(code, 0)
            code, _out, _err = run(["--root", root, "set-status", object_id, "draft"])
            self.assertEqual(code, 0)

    def test_collision_resolution_across_two_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            run(["--root", root, "add-language", "backend"])
            code1, out1, _e = run(["--root", root, "add-context", "backend/login"])
            code2, out2, _e = run(["--root", root, "add-context", "backend/logik"])
            self.assertEqual(code1, 0)
            self.assertEqual(code2, 0)
            self.assertIn("baclog", out1)
            self.assertIn("baclok", out2)

class TestTasklist(unittest.TestCase):
    def setUp(self):
        self._created_paths: set[tuple[str, str, str]] = set()

    def _add_rule(self, root, *, name="No bare except", checkable="llm", tool="", tool_rule="",
                  language="Python", context="backend", category="validation"):
        path = (language, context, category)
        if path not in self._created_paths:
            run(["--root", root, "add-language", language])
            run(["--root", root, "add-context", f"{language}/001-{context}"])
            run(["--root", root, "add-category", f"{language}/001-{context}/001-{category}"])
            self._created_paths.add(path)
        args = [
            "--root", root, "--json", "add", "--name", name,
            "--category", f"{language}/001-{context}/001-{category}",
            "--description", "Explain the rule.", "--checkable", checkable,
        ]
        if tool:
            args += ["--tool", tool]
        if tool_rule:
            args += ["--tool-rule", tool_rule]
        _code, out, _err = run(args)
        return json.loads(out)["id"]

    def test_tasklist_exports_active_rule_visible_via_taskctl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "project")
            rule_id = self._add_rule(root, checkable="ruff", tool="ruff", tool_rule="E722")

            code, out, _err = run(["--root", root, "tasklist"])
            self.assertEqual(code, 0)
            self.assertIn(rule_id, out)

            code, out, _err = run_taskctl(["--root", root, "--json", "show", rule_id])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["metainfo"]["assignee-type"], "tool")
            self.assertEqual(data["metainfo"]["assignee-name"], "ruff")

    def test_tasklist_skips_draft_and_obsolete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "project")
            active_id = self._add_rule(root, name="Active")
            draft_id = self._add_rule(root, name="Draft")
            run(["--root", root, "set-status", draft_id, "draft"])

            code, out, _err = run(["--root", root, "tasklist"])
            self.assertEqual(code, 0)
            self.assertIn(active_id, out)
            self.assertNotIn(draft_id, out)

    def test_tasklist_rerun_after_taskctl_marks_done_resets_to_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "project")
            rule_id = self._add_rule(root)
            run(["--root", root, "tasklist"])
            run_taskctl(["--root", root, "set-status", rule_id, "~"])
            run_taskctl(["--root", root, "set-status", rule_id, "X"])

            code, _out, _err = run(["--root", root, "tasklist"])
            self.assertEqual(code, 0)

            code, out, _err = run_taskctl(["--root", root, "show", rule_id, "--history"])
            self.assertEqual(code, 0)
            self.assertIn("[ ]", out)
            self.assertIn("re-exported from rulectl rule", out)

    def test_tasklist_language_scoping_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "project")
            python_id = self._add_rule(root, name="Python rule", language="Python")
            go_id = self._add_rule(root, name="Go rule", language="Go")

            code, out, _err = run(["--root", root, "tasklist", "--language", "Python"])
            self.assertEqual(code, 0)
            self.assertIn(python_id, out)
            self.assertNotIn(go_id, out)

    def test_tasklist_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "project")
            self._add_rule(root)

            code, out, _err = run(["--root", root, "--json", "tasklist"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)

    def test_tasklist_empty_store_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "project")
            code, out, _err = run(["--root", root, "tasklist"])
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), "")


if __name__ == "__main__":
    unittest.main()
