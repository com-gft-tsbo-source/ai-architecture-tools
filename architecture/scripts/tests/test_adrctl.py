import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import adrctl
import specctl


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = adrctl.main(argv)
    return code, out.getvalue(), err.getvalue()


def run_specctl(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = specctl.main(argv)
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
            code, _out, _err = run(["--root", root, "info-superseded-by", old_id, "abc123"])
            self.assertEqual(code, 0)
            code, out, _err = run(["--root", root, "--json", "show", old_id])
            self.assertEqual(json.loads(out)["metainfo"]["superseded-by"], "abc123")

    def test_add_with_wrong_path_depth_for_command_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            code, _out, err = run(["--root", root, "add-component", "OnlyOneSegment"])
            self.assertEqual(code, 1)
            self.assertIn("2-segment", err)


class TestSpecRefLinkage(unittest.TestCase):
    def test_add_with_spec_ref_propagates_adr_into_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            run_specctl(["--root", root, "init", "Design Doc"])
            _c, out, _e = run_specctl(["--root", root, "--json", "add-part", "Concurrency"])
            section_id = json.loads(out)["id"]

            run(["--root", root, "add-domain", "Backend"])
            code, out, _err = run(
                [
                    "--root", root, "--json", "add", "--name", "Use locks",
                    "--domain", "Backend", "--spec-ref", section_id,
                ]
            )
            self.assertEqual(code, 0)
            adr_id = json.loads(out)["id"]

            code, out, _err = run_specctl(["--root", root, "--json", "show", section_id])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["adr"], adr_id)

            code, out, _err = run_specctl(["--root", root, "show", section_id, "--history"])
            self.assertEqual(code, 0)
            self.assertIn(f"adr={adr_id}", out)

    def test_set_status_re_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            run_specctl(["--root", root, "init", "Design Doc"])
            _c, out, _e = run_specctl(["--root", root, "--json", "add-part", "Concurrency"])
            section_id = json.loads(out)["id"]

            run(["--root", root, "add-domain", "Backend"])
            _c, out, _e = run(
                [
                    "--root", root, "--json", "add", "--name", "Use locks",
                    "--domain", "Backend", "--spec-ref", section_id,
                ]
            )
            adr_id = json.loads(out)["id"]

            code, _out, _err = run(["--root", root, "set-status", adr_id, "accepted"])
            self.assertEqual(code, 0)

            code, out, _err = run_specctl(["--root", root, "show", section_id, "--history"])
            self.assertEqual(code, 0)
            self.assertEqual(out.count(f"adr={adr_id}"), 2)

    def test_superseding_keeps_section_on_new_adr(self):
        # design-specctl.md, "ADR Linkage": superseding moves the Section to
        # the superseding ADR -- marking the old one superseded must not
        # point the Section back at it.
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            run_specctl(["--root", root, "init", "Design Doc"])
            _c, out, _e = run_specctl(["--root", root, "--json", "add-part", "Concurrency"])
            section_id = json.loads(out)["id"]
            run(["--root", root, "add-domain", "Backend"])

            def add_adr(name):
                _c, out, _e = run(
                    [
                        "--root", root, "--json", "add", "--name", name, "--domain", "Backend",
                        "--spec-ref", section_id, "--set-status", "accepted",
                    ]
                )
                return json.loads(out)["id"]

            old_id = add_adr("Use locks")
            new_id = add_adr("Use lock-free queues")
            self.assertEqual(run(["--root", root, "info-superseded-by", old_id, new_id])[0], 0)
            for status in ("superseded", "deprecated", "rejected"):
                code, _out, err = run(["--root", root, "set-status", old_id, status, "--force", "--user-approved", "test"])
                self.assertEqual(code, 0, err)
                _c, out, _e = run_specctl(["--root", root, "--json", "show", section_id])
                self.assertEqual(json.loads(out)["adr"], new_id, status)

    def test_set_spec_ref_retroactively_attaches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            run_specctl(["--root", root, "init", "Design Doc"])
            _c, out, _e = run_specctl(["--root", root, "--json", "add-part", "Concurrency"])
            section_id = json.loads(out)["id"]

            run(["--root", root, "add-domain", "Backend"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Use locks", "--domain", "Backend"]
            )
            adr_id = json.loads(out)["id"]

            code, _out, _err = run(["--root", root, "info-spec-ref", adr_id, section_id])
            self.assertEqual(code, 0)

            code, out, _err = run_specctl(["--root", root, "--json", "show", section_id])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["adr"], adr_id)

    def test_missing_spec_ref_target_aborts_adrctl_but_adr_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "adrs")
            run(["--root", root, "add-domain", "Backend"])
            code, _out, err = run(
                [
                    "--root", root, "--json", "add", "--name", "Use locks",
                    "--domain", "Backend", "--spec-ref", "doesnotexist",
                ]
            )
            self.assertEqual(code, 1)
            self.assertIn("doesnotexist", err)

            code, out, _err = run(["--root", root, "list"])
            self.assertEqual(code, 0)
            self.assertIn("Use_locks", out)


if __name__ == "__main__":
    unittest.main()
