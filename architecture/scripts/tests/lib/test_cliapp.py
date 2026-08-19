import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from lib.cliapp import main, register_deferred
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec

SPEC = ToolSpec(
    name="taskctl",
    metagroup_levels=(MetagroupLevelSpec(type="Phase"),),
    metainfo=(MetainfoSpec(type="review"),),
    status=StatusSpec(codes=(" ", "~", "X"), initial=" "),
    user_content_blocks=("Description",),
    root_name="tasks",
    default_mode="directory",
)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(SPEC, argv)
    return code, out.getvalue(), err.getvalue()


class TestBasicFlow(unittest.TestCase):
    def test_add_phase_then_add_then_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            code, out, _err = run(["--root", root, "add-phase", "001-Setup"])
            self.assertEqual(code, 0)
            self.assertIn("Phase 001-Setup", out)

            code, out, _err = run(
                ["--root", root, "add", "--name", "First task", "--phase", "001-Setup",
                 "--description", "Do it."]
            )
            self.assertEqual(code, 0)
            self.assertIn("First_task", out)

            code, out, _err = run(["--root", root, "list"])
            self.assertEqual(code, 0)
            self.assertIn("First_task", out)

    def test_add_without_metagroup_flag_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            code, _out, err = run(["--root", root, "add", "--name", "No phase"])
            self.assertEqual(code, 1)
            self.assertIn("--phase", err)

    def test_show_metagroups(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            code, out, _err = run(["--root", root, "show-metagroups"])
            self.assertEqual(code, 0)
            self.assertIn("001-Setup", out)

    def test_set_status_and_show_with_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            run(["--root", root, "add", "--name", "Task", "--phase", "001-Setup"])
            _code, out, _err = run(["--root", root, "--json", "list"])
            object_id = json.loads(out)[0]["id"]

            code, out, _err = run(
                ["--root", root, "set-status", object_id, "~", "--message", "Starting"]
            )
            self.assertEqual(code, 0)

            code, out, _err = run(["--root", root, "show", object_id, "--history"])
            self.assertEqual(code, 0)
            self.assertIn("Starting", out)

    def test_reorder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            run(["--root", root, "add", "--name", "First", "--phase", "001-Setup"])
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Second", "--phase", "001-Setup"])
            second_id = json.loads(out)["id"]
            code, _out, _err = run(["--root", root, "reorder", second_id, "--after", "0"])
            self.assertEqual(code, 0)
            _c, out, _e = run(["--root", root, "--json", "show", second_id])
            self.assertEqual(json.loads(out)["number"], 1)

    def test_reindex(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            run(["--root", root, "add", "--name", "Task", "--phase", "001-Setup"])
            code, _out, _err = run(["--root", root, "reindex"])
            self.assertEqual(code, 0)

    def test_history_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            run(["--root", root, "add", "--name", "Task", "--phase", "001-Setup"])
            code, out, _err = run(["--root", root, "history"])
            self.assertEqual(code, 0)
            self.assertIn("Object created", out)

    def test_json_output_for_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            code, out, _err = run(
                ["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup"]
            )
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["name"], "Task")

    def test_invalid_status_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            _code, out, _err = run(["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup"])
            object_id = json.loads(out)["id"]
            code, _out, err = run(["--root", root, "set-status", object_id, "NOPE"])
            self.assertEqual(code, 1)
            self.assertIn("NOPE", err)


class TestDeferredStub(unittest.TestCase):
    def test_deferred_command_fails_with_message(self):
        extra_handlers = {}

        def configure(parser, subparsers):
            register_deferred(subparsers, "tasklist", extra_handlers)

        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(SPEC, ["--root", root, "tasklist"], extra_handlers=extra_handlers,
                            configure_parser=configure)
            self.assertEqual(code, 1)
            self.assertIn("not yet specified", err.getvalue())


if __name__ == "__main__":
    unittest.main()
