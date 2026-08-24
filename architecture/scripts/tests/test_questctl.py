import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import questctl


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = questctl.main(argv)
        except SystemExit as exc:  # argparse itself exits(2) on a usage error
            code = exc.code
    return code, out.getvalue(), err.getvalue()


class TestDepthZero(unittest.TestCase):
    def test_add_without_group_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            code, out, _err = run(["--root", root, "--json", "add", "--name", "Q1"])
            self.assertEqual(code, 0)
            record = json.loads(out)
            self.assertEqual(record["metagroup"], [])
            self.assertEqual(record["type"], "______")

    def test_add_group_rejected_once_ungrouped_is_established(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            run(["--root", root, "add", "--name", "Q1"])
            code, _out, err = run(["--root", root, "add-group", "Backend"])
            self.assertEqual(code, 1)
            self.assertIn("depth", err)


class TestDepthOne(unittest.TestCase):
    def test_add_with_group_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            run(["--root", root, "add-group", "Backend"])
            code, out, _err = run(["--root", root, "--json", "add", "--name", "Q1", "--group", "Backend"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["metagroup"], ["001-Backend"])

    def test_add_subgroup_rejected_once_group_only_is_established(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            run(["--root", root, "add-group", "Backend"])
            run(["--root", root, "add", "--name", "Q1", "--group", "Backend"])
            code, _out, err = run(["--root", root, "add-subgroup", "Backend/Auth"])
            self.assertEqual(code, 1)
            self.assertIn("depth", err)

    def test_more_groups_still_buildable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            run(["--root", root, "add-group", "Backend"])
            run(["--root", root, "add", "--name", "Q1", "--group", "Backend"])
            code, _out, _err = run(["--root", root, "add-group", "Frontend"])
            self.assertEqual(code, 0)


class TestDepthTwo(unittest.TestCase):
    def _fresh_root(self, tmp) -> str:
        root = str(Path(tmp) / "questions")
        run(["--root", root, "add-group", "Backend"])
        run(["--root", root, "add-subgroup", "Backend/Auth"])
        return root

    def test_add_at_subgroup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            code, out, _err = run(
                ["--root", root, "--json", "add", "--name", "Q1", "--subgroup", "Backend/Auth"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["metagroup"], ["001-Backend", "001-Auth"])

    def test_add_group_only_rejected_once_subgroup_depth_established(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            run(["--root", root, "add", "--name", "Q1", "--subgroup", "Backend/Auth"])
            code, _out, err = run(["--root", root, "add", "--name", "Q2", "--group", "Backend"])
            self.assertEqual(code, 1)
            self.assertIn("depth", err)

    def test_new_group_and_subgroup_still_buildable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            run(["--root", root, "add", "--name", "Q1", "--subgroup", "Backend/Auth"])
            self.assertEqual(run(["--root", root, "add-group", "Frontend"])[0], 0)
            self.assertEqual(run(["--root", root, "add-subgroup", "Frontend/UI"])[0], 0)

    def test_add_subgroup_alone_locks_depth_before_any_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._fresh_root(tmp)
            code, _out, err = run(["--root", root, "add", "--name", "Q1"])
            self.assertEqual(code, 1)
            self.assertIn("depth", err)


class TestAnswer(unittest.TestCase):
    def _new_question(self, root) -> str:
        _c, out, _e = run(["--root", root, "--json", "add", "--name", "Q1", "--description", "What?"])
        return json.loads(out)["id"]

    def test_answer_writes_answer_section_and_logs_t(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            qid = self._new_question(root)
            code, _out, _err = run(["--root", root, "answer", qid, "42", "--message", "first pass"])
            self.assertEqual(code, 0)
            code, out, _err = run(["--root", root, "--json", "show", qid])
            record = json.loads(out)
            self.assertEqual(record["content"]["Answer"], "42")
            t_entries = [h for h in record["history"] if h["prefix"] == "T"]
            self.assertEqual(len(t_entries), 1)
            self.assertEqual(t_entries[0]["message"], "first pass")

    def test_answer_requires_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            qid = self._new_question(root)
            code, _out, err = run(["--root", root, "answer", qid, "42"])
            self.assertEqual(code, 2)  # argparse usage error: --message required

    def test_answer_overwrites_previous_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            qid = self._new_question(root)
            run(["--root", root, "answer", qid, "first", "--message", "m1"])
            run(["--root", root, "answer", qid, "second", "--message", "m2"])
            code, out, _err = run(["--root", root, "--json", "show", qid])
            record = json.loads(out)
            self.assertEqual(record["content"]["Answer"], "second")
            t_entries = [h for h in record["history"] if h["prefix"] == "T"]
            self.assertEqual(len(t_entries), 2)

    def test_answer_does_not_change_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            qid = self._new_question(root)
            run(["--root", root, "set-status", qid, "~"])
            run(["--root", root, "answer", qid, "42", "--message", "m"])
            code, out, _err = run(["--root", root, "--json", "show", qid])
            self.assertEqual(json.loads(out)["status"], "~")

    def test_no_generic_set_answer_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            qid = self._new_question(root)
            code, _out, _err = run(["--root", root, "set-answer", qid, "hack"])
            self.assertEqual(code, 2)  # argparse: unknown subcommand

    def test_no_inline_answer_flag_on_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            code, _out, _err = run(
                ["--root", root, "add", "--name", "Q", "--answer", "hack"]
            )
            self.assertEqual(code, 2)  # argparse: unrecognized argument


class TestParallelProcessingGate(unittest.TestCase):
    def _two_questions(self, root):
        _c, o1, _e = run(["--root", root, "--json", "add", "--name", "Q1"])
        _c, o2, _e = run(["--root", root, "--json", "add", "--name", "Q2"])
        return json.loads(o1)["id"], json.loads(o2)["id"]

    def test_next_returns_open_question_when_nothing_in_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            self._two_questions(root)
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["name"], "Q1")

    def test_next_blocked_by_in_progress_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id1, _id2 = self._two_questions(root)
            run(["--root", root, "set-status", id1, "~"])
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "in_progress")

    def test_next_all_blocked_by_in_progress_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id1, _id2 = self._two_questions(root)
            run(["--root", root, "set-status", id1, "~"])
            code, out, _err = run(["--root", root, "--json", "next-all"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "in_progress")

    def test_blocked_status_releases_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id1, _id2 = self._two_questions(root)
            run(["--root", root, "set-status", id1, "~"])
            run(["--root", root, "set-status", id1, "B", "--message", "waiting on user"])
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["name"], "Q2")

    def test_all_answered_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id1, id2 = self._two_questions(root)
            for qid in (id1, id2):
                run(["--root", root, "set-status", qid, "~"])
                run(["--root", root, "set-status", qid, "X"])
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "all_answered")

    def test_empty_store_is_all_answered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "all_answered")

    def test_awaiting_interaction_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id1, id2 = self._two_questions(root)
            run(["--root", root, "set-status", id1, "~"])
            run(["--root", root, "set-status", id1, "B", "--message", "blocked"])
            run(["--root", root, "set-status", id2, "~"])
            run(["--root", root, "set-status", id2, "X"])
            code, out, _err = run(["--root", root, "--json", "next-all"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "awaiting_interaction")

    def test_next_all_returns_open_questions_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            self._two_questions(root)
            code, out, _err = run(["--root", root, "--json", "next-all"])
            self.assertEqual(code, 0)
            names = [r["name"] for r in json.loads(out)]
            self.assertEqual(names, ["Q1", "Q2"])

    def test_non_json_reason_goes_to_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id1, _id2 = self._two_questions(root)
            run(["--root", root, "set-status", id1, "~"])
            code, out, err = run(["--root", root, "next"])
            self.assertEqual(code, 1)
            self.assertEqual(out, "")
            self.assertIn("in progress", err)


class TestReusedStatusMachine(unittest.TestCase):
    """design-questctl.md, "Status": unchanged from taskctl."""

    def test_review_user_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Q", "--review", "user"])
            qid = json.loads(out)["id"]
            run(["--root", root, "set-status", qid, "~"])
            code, _out, err = run(["--root", root, "set-status", qid, "X"])
            self.assertEqual(code, 1)
            self.assertIn("invalid status transition", err)
            self.assertEqual(run(["--root", root, "set-status", qid, "R"])[0], 0)
            self.assertEqual(run(["--root", root, "set-status", qid, "X"])[0], 0)

    def test_blocking_requires_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Q"])
            qid = json.loads(out)["id"]
            code, _out, err = run(["--root", root, "set-status", qid, "B"])
            self.assertEqual(code, 1)
            self.assertIn("--message", err)


class TestSourceMetainfo(unittest.TestCase):
    """design-questctl.md, "Metainfo": traceability, same convention as
    rulectl's own `source` field."""

    def test_inline_on_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            code, out, _err = run(
                ["--root", root, "--json", "add", "--name", "Q", "--source", "req.md#3"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["metainfo"]["source"], "req.md#3")

    def test_info_source_sets_after_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Q"])
            qid = json.loads(out)["id"]
            code, _out, _err = run(["--root", root, "info-source", qid, "https://example.com#Intro"])
            self.assertEqual(code, 0)
            code, out, _err = run(["--root", root, "--json", "show", qid])
            self.assertEqual(json.loads(out)["metainfo"]["source"], "https://example.com#Intro")

    def test_left_unset_when_not_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Q"])
            self.assertNotIn("source", json.loads(out)["metainfo"])


class TestNextScopeFilter(unittest.TestCase):
    """design-questctl.md, "CLI Contract additions": optional --group/
    --subgroup filter on next/next-all; the [~] gate itself stays unscoped."""

    def _two_groups(self, root):
        run(["--root", root, "add-group", "Backend"])
        run(["--root", root, "add-group", "Frontend"])
        _c, o1, _e = run(["--root", root, "--json", "add", "--name", "Q-Backend", "--group", "Backend"])
        _c, o2, _e = run(["--root", root, "--json", "add", "--name", "Q-Frontend", "--group", "Frontend"])
        return json.loads(o1)["id"], json.loads(o2)["id"]

    def test_next_scoped_to_group_skips_other_groups_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            self._two_groups(root)
            code, out, _err = run(["--root", root, "--json", "next", "--group", "Frontend"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["name"], "Q-Frontend")

    def test_next_all_scoped_returns_only_that_groups_questions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            self._two_groups(root)
            code, out, _err = run(["--root", root, "--json", "next-all", "--group", "Backend"])
            self.assertEqual(code, 0)
            names = [r["name"] for r in json.loads(out)]
            self.assertEqual(names, ["Q-Backend"])

    def test_both_flags_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            self._two_groups(root)
            code, _out, err = run(
                ["--root", root, "next", "--group", "Backend", "--subgroup", "Backend/Auth"]
            )
            self.assertEqual(code, 1)
            self.assertIn("at most one", err)

    def test_global_gate_blocks_scoped_next_even_outside_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id_backend, _id_frontend = self._two_groups(root)
            run(["--root", root, "set-status", id_backend, "~"])
            code, out, _err = run(["--root", root, "--json", "next", "--group", "Frontend"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "in_progress")

    def test_scoped_all_answered_even_though_other_scope_still_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            id_backend, _id_frontend = self._two_groups(root)
            run(["--root", root, "set-status", id_backend, "~"])
            run(["--root", root, "set-status", id_backend, "X"])
            code, out, _err = run(["--root", root, "--json", "next", "--group", "Backend"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(out)["reason"], "all_answered")

    def test_unscoped_next_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            self._two_groups(root)
            code, out, _err = run(["--root", root, "--json", "next"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["name"], "Q-Backend")


class TestAnnotate(unittest.TestCase):
    def test_annotate_logs_t_without_touching_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "questions")
            _c, out, _e = run(["--root", root, "--json", "add", "--name", "Q"])
            qid = json.loads(out)["id"]
            run(["--root", root, "answer", qid, "42", "--message", "m"])
            code, _out, _err = run(["--root", root, "annotate", qid, "--message", "still working"])
            self.assertEqual(code, 0)
            code, out, _err = run(["--root", root, "--json", "show", qid])
            record = json.loads(out)
            self.assertEqual(record["content"]["Answer"], "42")
            self.assertEqual(len(record["history"]), 3)  # created, answered, annotated


if __name__ == "__main__":
    unittest.main()
