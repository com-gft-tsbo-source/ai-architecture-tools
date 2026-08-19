import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import adrctl


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = adrctl.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestEndToEnd(unittest.TestCase):
    def test_two_level_metagroup_and_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            self.assertEqual(run(["--root", root, "add-domain", "Backend"])[0], 0)
            self.assertEqual(run(["--root", root, "add-component", "Backend/001-orders"])[0], 0)
            code, out, _err = run(
                [
                    "--root", root, "--json", "add", "--name", "Use event sourcing",
                    "--component", "Backend/001-orders",
                    "--motivation", "Need an audit trail.",
                    "--description", "Adopt event sourcing for orders.",
                    "--rationale", "Simplifies replay and debugging.",
                ]
            )
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["status"], "proposed")
            self.assertEqual(data["content"]["Motivation"], "Need an audit trail.")
            self.assertEqual(data["content"]["Rationale"], "Simplifies replay and debugging.")

    def test_superseded_by_metainfo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            run(["--root", root, "add-domain", "Backend"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Old ADR", "--domain", "Backend"]
            )
            old_id = json.loads(out)["id"]
            code, _out, _err = run(["--root", root, "set-status", old_id, "superseded"])
            self.assertEqual(code, 0)
            code, _out, _err = run(["--root", root, "set-superseded-by", old_id, "abc123"])
            self.assertEqual(code, 0)
            code, out, _err = run(["--root", root, "--json", "show", old_id])
            self.assertEqual(json.loads(out)["metainfo"]["superseded-by"], "abc123")

    def test_tasklist_is_deferred(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            code, _out, err = run(["--root", root, "tasklist"])
            self.assertEqual(code, 1)
            self.assertIn("not yet specified", err)

    def test_add_with_wrong_path_depth_for_command_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            code, _out, err = run(["--root", root, "add-component", "OnlyOneSegment"])
            self.assertEqual(code, 1)
            self.assertIn("2-segment", err)


if __name__ == "__main__":
    unittest.main()
