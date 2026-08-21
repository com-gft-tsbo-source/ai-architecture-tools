import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from lib.cliapp import CliError, main
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


class TestSetContentBlock(unittest.TestCase):
    def test_set_description_changes_content_and_shows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup",
                 "--description", "Original"]
            )
            object_id = json.loads(out)["id"]

            code, _out, _err = run(["--root", root, "set-description", object_id, "Revised"])
            self.assertEqual(code, 0)

            _c, out, _e = run(["--root", root, "--json", "show", object_id])
            self.assertEqual(json.loads(out)["content"]["Description"], "Revised")


class TestDeleteCommand(unittest.TestCase):
    def test_delete_removes_object_from_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup"]
            )
            object_id = json.loads(out)["id"]

            code, _out, _err = run(["--root", root, "delete", object_id])
            self.assertEqual(code, 0)

            code, out, _err = run(["--root", root, "list"])
            self.assertEqual(code, 0)
            self.assertEqual(out.strip(), "")

    def test_delete_unknown_id_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            code, _out, err = run(["--root", root, "delete", "nope"])
            self.assertEqual(code, 1)
            self.assertIn("nope", err)


RULECTL_LIKE_SPEC = ToolSpec(
    name="rulectl",
    metagroup_levels=(MetagroupLevelSpec(type="Language"), MetagroupLevelSpec(type="Context")),
    metainfo=(MetainfoSpec(type="weight"),),
    status=StatusSpec(codes=("draft", "active"), initial="active"),
    user_content_blocks=("Description",),
    root_name="rules",
    default_mode="directory",
)


def run_rulectl_like(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(RULECTL_LIKE_SPEC, argv)
    return code, out.getvalue(), err.getvalue()


class TestListFilters(unittest.TestCase):
    def test_metagroup_filter_includes_descendants(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            run_rulectl_like(["--root", root, "add-language", "Python"])
            run_rulectl_like(["--root", root, "add-context", "Python/backend"])
            run_rulectl_like(
                ["--root", root, "add", "--name", "In backend", "--context", "Python/backend"]
            )
            run_rulectl_like(["--root", root, "add-language", "Go"])
            run_rulectl_like(["--root", root, "add-context", "Go/server"])
            run_rulectl_like(
                ["--root", root, "add", "--name", "In go server", "--context", "Go/server"]
            )

            code, out, _err = run_rulectl_like(["--root", root, "list", "--language", "Python"])
            self.assertEqual(code, 0)
            self.assertIn("In_backend", out)
            self.assertNotIn("In_go_server", out)

    def test_metainfo_filter_exact_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            run_rulectl_like(["--root", root, "add-language", "Python"])
            run_rulectl_like(["--root", root, "add-context", "Python/backend"])
            run_rulectl_like(
                ["--root", root, "add", "--name", "Heavy", "--context", "Python/backend",
                 "--weight", "high"]
            )
            run_rulectl_like(
                ["--root", root, "add", "--name", "Light", "--context", "Python/backend",
                 "--weight", "low"]
            )

            code, out, _err = run_rulectl_like(["--root", root, "list", "--weight", "high"])
            self.assertEqual(code, 0)
            self.assertIn("Heavy", out)
            self.assertNotIn("Light", out)

    def test_more_than_one_metagroup_filter_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "rules")
            code, _out, err = run_rulectl_like(
                ["--root", root, "list", "--language", "Python", "--context", "Python/backend"]
            )
            self.assertEqual(code, 1)
            self.assertIn("at most one", err)


class TestInfoCommand(unittest.TestCase):
    def test_info_sets_metainfo_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup"]
            )
            object_id = json.loads(out)["id"]

            code, _out, _err = run(["--root", root, "info-review", object_id, "user"])
            self.assertEqual(code, 0)

            _c, out, _e = run(["--root", root, "--json", "show", object_id])
            self.assertEqual(json.loads(out)["metainfo"]["review"], "user")


class TestGroupCommand(unittest.TestCase):
    def test_group_moves_object_and_rederives_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            run(["--root", root, "add-phase", "002-Implementation"])
            run(["--root", root, "add", "--name", "Existing", "--phase", "002-Implementation"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup"]
            )
            object_id = json.loads(out)["id"]

            code, _out, _err = run(["--root", root, "group-phase", object_id, "002-Implementation"])
            self.assertEqual(code, 0)

            _c, out, _e = run(["--root", root, "--json", "show", object_id])
            data = json.loads(out)
            self.assertEqual(data["metagroup"], ["002-Implementation"])
            self.assertEqual(data["number"], 2)

    def test_group_noop_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup"]
            )
            object_id = json.loads(out)["id"]

            code, _out, err = run(["--root", root, "group-phase", object_id, "001-Setup"])
            self.assertEqual(code, 1)
            self.assertIn("reorder", err)

    def test_group_unknown_path_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            _c, out, _e = run(
                ["--root", root, "--json", "add", "--name", "Task", "--phase", "001-Setup"]
            )
            object_id = json.loads(out)["id"]

            code, _out, err = run(["--root", root, "group-phase", object_id, "Nonexistent"])
            self.assertEqual(code, 1)


class TestAfterDispatch(unittest.TestCase):
    def test_called_with_spec_store_args_and_result_on_success(self):
        calls = []

        def hook(spec, store, args, result):
            calls.append((spec, store, args, result))

        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(
                    SPEC,
                    ["--root", root, "add", "--name", "Task", "--phase", "001-Setup"],
                    after_dispatch=hook,
                )
            self.assertEqual(code, 0)
            self.assertEqual(len(calls), 1)
            spec, store, args, result = calls[0]
            self.assertIs(spec, SPEC)
            self.assertEqual(args.command, "add")
            self.assertEqual(result.name, "Task")

    def test_not_called_when_dispatch_itself_fails(self):
        calls = []

        def hook(spec, store, args, result):
            calls.append(result)

        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(SPEC, ["--root", root, "add", "--name", "No phase"], after_dispatch=hook)
            self.assertEqual(code, 1)
            self.assertEqual(calls, [])

    def test_error_raised_by_hook_aborts_with_exit_code_1(self):
        def hook(spec, store, args, result):
            raise CliError("propagation failed")

        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(
                    SPEC,
                    ["--root", root, "add", "--name", "Task", "--phase", "001-Setup"],
                    after_dispatch=hook,
                )
            self.assertEqual(code, 1)
            self.assertIn("propagation failed", err.getvalue())


if __name__ == "__main__":
    unittest.main()
