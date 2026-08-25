import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import taskctl


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = taskctl.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestEndToEnd(unittest.TestCase):
    def _fresh_root(self, tmp) -> str:
        root = str(Path(tmp) / "tasks")
        run(["--root", root, "add-phase", "001-Setup"])
        run(["--root", root, "add-phase", "002-Implementation"])
        return root

    def test_object_type_is_unpadded_phase_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            code, out, _err = run(
                ["--root", root, "--json", "add", "--name", "First", "--phase", "001-Setup"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["type"], "1")

            code, out, _err = run(
                ["--root", root, "--json", "add", "--name", "Second", "--phase", "002-Implementation"]
            )
            self.assertEqual(json.loads(out)["type"], "2")

    def test_next_orders_by_phase_then_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            run(["--root", root, "add", "--name", "B-task", "--phase", "002-Implementation"])
            run(["--root", root, "add", "--name", "A-task", "--phase", "001-Setup"])
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["name"], "A-task")

    def test_next_skips_done_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Only", "--phase", "001-Setup"])
            object_id = json.loads(out)["id"]
            run(["--root", root, "set-status", object_id, "~"])
            run(["--root", root, "set-status", object_id, "X"])
            code, _out, err = run(["--root", root, "next"])
            self.assertEqual(code, 1)
            self.assertIn("no open tasks", err)

    def test_next_no_work_available_is_json_structured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 1)
            payload = json.loads(out)
            self.assertEqual(payload["reason"], "all_done")
            self.assertIn("no open tasks", payload["message"])

    def test_annotate_appends_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "T", "--phase", "001-Setup"])
            object_id = json.loads(out)["id"]
            code, out, _err = run(["--root", root, "annotate", object_id, "--message", "progress made"])
            self.assertEqual(code, 0)
            code, out, _err = run(["--root", root, "show", object_id, "--history"])
            self.assertIn("progress made", out)

    def test_source_metainfo_settable_inline_and_via_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            code, out, _err = run(
                ["--root", root, "--json", "add", "--name", "T", "--phase", "001-Setup",
                 "--source", "design.md#Installation"]
            )
            self.assertEqual(code, 0)
            record = json.loads(out)
            object_id = record["id"]
            self.assertEqual(record["metainfo"]["source"], "design.md#Installation")

            code, out, _err = run(["--root", root, "info-source", object_id, "design.md#Compile"])
            self.assertEqual(code, 0)
            code, out, _err = run(["--root", root, "--json", "show", object_id])
            self.assertEqual(json.loads(out)["metainfo"]["source"], "design.md#Compile")


class TestCorrections(unittest.TestCase):
    """corrections.md: auto-numbering on add-phase, flexible --phase
    reference on add, and multi-root --root."""

    def test_add_phase_auto_numbers_without_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            code, out, _err = run(["--root", root, "add-phase", "Setup"])
            self.assertEqual(code, 0)
            self.assertIn("Phase Setup:", out)
            code, out, _err = run(["--root", root, "show-metagroups"])
            self.assertIn("001-Setup", out)

    def test_add_phase_explicit_number_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "005-Setup"])
            code, out, _err = run(["--root", root, "show-metagroups"])
            self.assertIn("005-Setup", out)

    def test_add_accepts_bare_number_and_bare_name_for_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "Setup"])
            code1, out1, _e = run(["--root", root, "--json", "add", "--name", "A", "--phase", "1"])
            code2, out2, _e = run(["--root", root, "--json", "add", "--name", "B", "--phase", "Setup"])
            self.assertEqual(code1, 0)
            self.assertEqual(code2, 0)
            self.assertEqual(json.loads(out1)["metagroup"], ["001-Setup"])
            self.assertEqual(json.loads(out2)["metagroup"], ["001-Setup"])

    def test_shares_root_with_another_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared_root = str(Path(tmp) / "project")
            run(["--root", shared_root, "add-phase", "Setup"])
            run(["--root", shared_root, "add", "--name", "FromTasks", "--phase", "Setup"])
            self.assertTrue((Path(tmp) / "project" / "tasks").is_dir())

            code, out, _err = run(["--root", shared_root, "list"])
            self.assertEqual(code, 0)
            self.assertIn("FromTasks", out)


class TestStatusTransitions(unittest.TestCase):
    def _new_task(self, root, review=None) -> str:
        args = ["--root", root, "--json", "add", "--name", "T", "--phase", "001-Setup"]
        if review is not None:
            args += ["--review", review]
        _c, out, _e = run(args)
        return json.loads(out)["id"]

    def test_none_review_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            task_id = self._new_task(root, review="none")
            self.assertEqual(run(["--root", root, "set-status", task_id, "~"])[0], 0)
            self.assertEqual(run(["--root", root, "set-status", task_id, "X"])[0], 0)

    def test_user_review_path_requires_review_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            task_id = self._new_task(root, review="user")
            run(["--root", root, "set-status", task_id, "~"])
            code, _out, err = run(["--root", root, "set-status", task_id, "X"])
            self.assertEqual(code, 1)
            self.assertIn("invalid status transition", err)
            self.assertEqual(run(["--root", root, "set-status", task_id, "R"])[0], 0)
            self.assertEqual(run(["--root", root, "set-status", task_id, "X"])[0], 0)

    def test_rework_from_review_back_to_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            task_id = self._new_task(root, review="user")
            run(["--root", root, "set-status", task_id, "~"])
            run(["--root", root, "set-status", task_id, "R"])
            code, _out, _err = run(["--root", root, "set-status", task_id, "~"])
            self.assertEqual(code, 0)

    def test_blocking_requires_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            task_id = self._new_task(root)
            code, _out, err = run(["--root", root, "set-status", task_id, "B"])
            self.assertEqual(code, 1)
            self.assertIn("--message", err)
            code, _out, _err = run(["--root", root, "set-status", task_id, "B", "--message", "waiting on X"])
            self.assertEqual(code, 0)

    def test_unblock_into_non_terminal_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            task_id = self._new_task(root)
            run(["--root", root, "set-status", task_id, "B", "--message", "blocked"])
            code, _out, _err = run(["--root", root, "set-status", task_id, "~"])
            self.assertEqual(code, 0)

    def test_cannot_block_done_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            task_id = self._new_task(root)
            run(["--root", root, "set-status", task_id, "~"])
            run(["--root", root, "set-status", task_id, "X"])
            code, _out, err = run(["--root", root, "set-status", task_id, "B", "--message", "x"])
            self.assertEqual(code, 1)
            self.assertIn("already done", err)

    def test_invalid_transition_allowed_with_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "001-Setup"])
            task_id = self._new_task(root, review="none")
            code, _out, _err = run(["--root", root, "set-status", task_id, "X", "--force"])
            self.assertEqual(code, 0)


class TestPhaselessMode(unittest.TestCase):
    """design-taskctl.md, "Metagroups": taskctl's variable depth (0 or 1) --
    a store either uses Phases for every Task, or none at all."""

    def test_add_without_phase_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            code, out, _err = run(["--root", root, "--json", "add", "--name", "Only task"])
            self.assertEqual(code, 0)
            record = json.loads(out)
            self.assertEqual(record["metagroup"], [])
            self.assertEqual(record["type"], "______")

    def test_add_phase_rejected_once_phaseless_is_established(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add", "--name", "First"])
            code, _out, err = run(["--root", root, "add-phase", "Setup"])
            self.assertEqual(code, 1)
            self.assertIn("depth", err)

    def test_add_phase_alone_locks_depth_before_any_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "Setup"])
            code, _out, err = run(["--root", root, "add", "--name", "No phase given"])
            self.assertEqual(code, 1)
            self.assertIn("depth", err)

    def test_next_works_in_phaseless_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add", "--name", "A"])
            run(["--root", root, "add", "--name", "B"])
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["name"], "A")

    def test_next_shows_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add", "--name", "A"])
            code, out, _err = run(["--root", root, "next"])
            self.assertEqual(code, 0)
            self.assertIn("Object created", out)

    def test_phaseless_store_round_trips_across_invocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "A"])
            object_id = json.loads(out)["id"]
            run(["--root", root, "set-status", object_id, "~"])
            code, out, _err = run(["--root", root, "--json", "show", object_id])
            self.assertEqual(json.loads(out)["status"], "~")


if __name__ == "__main__":
    unittest.main()
