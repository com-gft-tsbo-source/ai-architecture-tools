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
    def test_origin_cli_round_trip_and_assignment_independence(self):
        for store_name in ("tasks", "tasks.md"):
            with self.subTest(store=store_name), tempfile.TemporaryDirectory() as tmp:
                root = str(Path(tmp) / store_name)
                code, out, err = run([
                    "--root", root, "--json", "add", "--name", "Ordinary work",
                    "--assignee-type", "agent", "--source", "design.md",
                ])
                self.assertEqual(code, 0, err)
                ordinary = json.loads(out)
                self.assertFalse(ordinary["metainfo"].get("origin"))
                code, out, err = run([
                    "--root", root, "--json", "add", "--name", "Exported check",
                    "--assignee-type", "agent", "--origin", "rulectl:rule01",
                ])
                self.assertEqual(code, 0, err)
                exported_id = json.loads(out)["id"]
                code, out, err = run([
                    "--root", root, "--json", "list", "--origin", "rulectl:rule01",
                ])
                self.assertEqual(code, 0, err)
                self.assertEqual([record["id"] for record in json.loads(out)], [exported_id])
                code, _, err = run(["--root", root, "info-origin", exported_id, "rulectl:rule02"])
                self.assertEqual(code, 0, err)
                code, out, err = run(["--root", root, "--json", "show", exported_id])
                self.assertEqual(code, 0, err)
                self.assertEqual(json.loads(out)["metainfo"]["origin"], "rulectl:rule02")

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

    def test_show_metagroups_json_is_a_list_of_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "tasks")
            run(["--root", root, "add-phase", "Setup"])
            run(["--root", root, "add-phase", "Build"])
            code, out, _err = run(["--root", root, "--json", "show-metagroups"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out), [["001-Setup"], ["002-Build"]])
            code, out, _err = run(["--root", root, "show-metagroups"])
            self.assertEqual(out.splitlines(), ["001-Setup", "002-Build"])

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
            code, _out, err = run(["--root", root, "set-status", task_id, "X"])
            self.assertEqual(code, 1)
            self.assertIn("completes a user review", err)
            self.assertEqual(run([
                "--root", root, "set-status", task_id, "X", "--user-approved", "user accepted it",
            ])[0], 0)

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
            code, _out, err = run(["--root", root, "set-status", task_id, "X", "--force"])
            self.assertEqual(code, 1)
            self.assertIn("--force requires --user-approved", err)
            code, _out, err = run([
                "--root", root, "set-status", task_id, "X", "--force", "--user-approved", "skip it",
            ])
            self.assertEqual(code, 0, err)


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


class TestGuards(unittest.TestCase):
    """design-taskctl.md, "Guards": sequence and review guards, each lifted
    only by --user-approved (recorded in the History)."""

    def _store(self, tmp, store_name="tasks"):
        root = str(Path(tmp) / store_name)
        run(["--root", root, "add-phase", "001-Setup"])
        run(["--root", root, "add-phase", "002-Build"])
        return root

    def _add(self, root, name, phase="001-Setup", *extra):
        code, out, err = run(["--root", root, "--json", "add", "--name", name, "--phase", phase, *extra])
        self.assertEqual(code, 0, err)
        return json.loads(out)["id"]

    def _show(self, root, task_id):
        _c, out, _e = run(["--root", root, "--json", "show", task_id])
        return json.loads(out)

    def _to_review(self, root, task_id):
        run(["--root", root, "set-status", task_id, "~"])
        self.assertEqual(run(["--root", root, "set-status", task_id, "R"])[0], 0)

    def test_later_task_cannot_start_while_earlier_in_review(self):
        for store_name in ("tasks", "tasks.md"):
            with self.subTest(store=store_name), tempfile.TemporaryDirectory() as tmp:
                root = self._store(tmp, store_name)
                first = self._add(root, "First", "001-Setup", "--review", "user")
                second = self._add(root, "Second", "002-Build")
                self._to_review(root, first)

                code, out, _err = run(["--root", root, "--json", "set-status", second, "~"])
                self.assertEqual(code, 1)
                data = json.loads(out)
                self.assertEqual(data["reason"], "sequence_blocked")
                self.assertEqual(data["blocking_task"], first)
                code, _out, err = run(["--root", root, "set-status", second, "~"])
                self.assertIn(first, err)
                self.assertIn("review by user", err)
                self.assertEqual(self._show(root, second)["status"], " ")

    def test_every_unresolved_status_blocks_and_done_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            first = self._add(root, "First")
            second = self._add(root, "Second")
            # open, in progress and blocked all hold the queue
            self.assertEqual(run(["--root", root, "set-status", second, "~"])[0], 1)
            run(["--root", root, "set-status", first, "~"])
            self.assertEqual(run(["--root", root, "set-status", second, "~"])[0], 1)
            run(["--root", root, "set-status", first, "B", "--message", "waiting"])
            self.assertEqual(run(["--root", root, "set-status", second, "~"])[0], 1)
            run(["--root", root, "set-status", first, "~"])
            run(["--root", root, "set-status", first, "X"])
            code, _out, err = run(["--root", root, "set-status", second, "~"])
            self.assertEqual(code, 0, err)

    def test_blocking_a_later_task_stays_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            self._add(root, "First")
            second = self._add(root, "Second")
            code, _out, err = run(["--root", root, "set-status", second, "B", "--message", "needs input"])
            self.assertEqual(code, 0, err)

    def test_user_approved_lifts_sequence_guard_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            self._add(root, "First")
            second = self._add(root, "Second")
            code, _out, err = run([
                "--root", root, "set-status", second, "~", "--message", "starting",
                "--user-approved", "User: start Second now",
            ])
            self.assertEqual(code, 0, err)
            _c, out, _e = run(["--root", root, "show", second, "--history"])
            self.assertIn("USER-APPROVED: User: start Second now", out)
            self.assertIn("starting", out)

    def test_empty_user_approved_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            self._add(root, "First")
            second = self._add(root, "Second")
            code, _out, err = run(["--root", root, "set-status", second, "~", "--user-approved", " "])
            self.assertEqual(code, 1)
            self.assertIn("--user-approved requires", err)

    def test_self_approval_of_user_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            task = self._add(root, "Only", "001-Setup", "--review", "user")
            self._to_review(root, task)
            code, out, _err = run(["--root", root, "--json", "set-status", task, "X"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "approval_required")
            code, _out, err = run(["--root", root, "set-status", task, "X", "--user-approved", "LGTM"])
            self.assertEqual(code, 0, err)

    def test_subagent_review_completion_stays_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            task = self._add(root, "Only", "001-Setup", "--review", "subagent")
            run(["--root", root, "set-status", task, "~"])
            run(["--root", root, "set-status", task, "C"])
            code, _out, err = run(["--root", root, "set-status", task, "X"])
            self.assertEqual(code, 0, err)

    def test_review_cannot_change_while_in_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            task = self._add(root, "Only", "001-Setup", "--review", "subagent")
            run(["--root", root, "set-status", task, "~"])
            run(["--root", root, "set-status", task, "C"])
            code, _out, err = run(["--root", root, "info-review", task, "none"])
            self.assertEqual(code, 1)
            self.assertIn("while in [C]", err)
            code, _out, err = run(["--root", root, "info-review", task, "none", "--user-approved", "drop it"])
            self.assertEqual(code, 0, err)

    def test_lowering_user_review_requires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            task = self._add(root, "Only", "001-Setup", "--review", "user")
            run(["--root", root, "set-status", task, "~"])
            for value in ("none", "subagent"):
                code, out, _err = run(["--root", root, "--json", "info-review", task, value])
                self.assertEqual(code, 1, value)
                self.assertEqual(json.loads(out)["reason"], "approval_required")
            self.assertEqual(self._show(root, task)["metainfo"]["review"], "user")

    def test_raising_or_lowering_subagent_review_stays_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            task = self._add(root, "Only")
            run(["--root", root, "set-status", task, "~"])
            self.assertEqual(run(["--root", root, "info-review", task, "subagent"])[0], 0)
            self.assertEqual(run(["--root", root, "info-review", task, "none"])[0], 0)
            self.assertEqual(run(["--root", root, "info-review", task, "user"])[0], 0)

    def test_add_with_working_status_respects_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            self._add(root, "First")
            code, out, _err = run([
                "--root", root, "--json", "add", "--name", "Second", "--phase", "001-Setup", "--set-status", "~",
            ])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "sequence_blocked")
            self._add(root, "Parked", "001-Setup", "--set-status", "B")
            code, _out, err = run([
                "--root", root, "add", "--name", "Third", "--phase", "001-Setup", "--set-status", "X",
                "--user-approved", "already done by hand",
            ])
            self.assertEqual(code, 0, err)

    def test_gate_none_task_neither_blocks_nor_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            check = self._add(root, "Check", "001-Setup", "--gate", "none", "--review", "user")
            later_check = self._add(root, "Later check", "001-Setup", "--gate", "none")
            work = self._add(root, "Work", "002-Build")
            self._to_review(root, check)
            code, _out, err = run(["--root", root, "set-status", later_check, "~"])
            self.assertEqual(code, 0, err)
            run(["--root", root, "set-status", later_check, "B", "--message", "cannot check"])
            # next skips the non-gating Tasks waiting on interaction
            _c, out, _e = run(["--root", root, "--json", "next"])
            self.assertEqual(json.loads(out)["id"], work)
            code, _out, err = run(["--root", root, "set-status", work, "~"])
            self.assertEqual(code, 0, err)

    def test_gate_is_fixed_after_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            task = self._add(root, "Only")
            code, _out, err = run(["--root", root, "info-gate", task, "none"])
            self.assertEqual(code, 1)
            self.assertIn("gate is fixed", err)
            code, _out, err = run(["--root", root, "info-gate", task, "none", "--user-approved", "independent"])
            self.assertEqual(code, 0, err)

    def test_unrelated_operations_need_no_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._store(tmp)
            first = self._add(root, "First", "001-Setup", "--review", "user")
            second = self._add(root, "Second")
            self._to_review(root, first)
            for argv in (
                ["set-description", second, "updated"],
                ["info-assignee-name", second, "someone"],
                ["group-phase", second, "002-Build"],
                ["annotate", second, "--message", "note"],
                ["set-status", first, "~", "--message", "rework"],
            ):
                code, _out, err = run(["--root", root, *argv])
                self.assertEqual(code, 0, (argv, err))
