import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import rulectl


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = rulectl.main(argv)
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

    def test_tasklist_is_deferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            code, _out, err = run(["--root", root, "tasklist"])
            self.assertEqual(code, 1)
            self.assertIn("not yet specified", err)


if __name__ == "__main__":
    unittest.main()
