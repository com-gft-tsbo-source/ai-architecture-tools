import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import specctl


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = specctl.main(argv)
    return code, out.getvalue(), err.getvalue()


class TestAddAndShow(unittest.TestCase):
    def test_nested_add_and_json_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            self.assertEqual(
                run(["--root", root, "add-part", "Concurrency", "--description", "Intro."])[0], 0
            )
            self.assertEqual(
                run(["--root", root, "add-chapter", "Concurrency/Locking", "--description", "A lock."])[0],
                0,
            )
            code, out, _err = run(["--root", root, "--json", "show", "001-Concurrency/1"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["name"], "Locking")
            self.assertEqual(data["level_type"], "Chapter")
            self.assertEqual(data["content"]["Description"], "A lock.")

    def test_wrong_path_depth_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            code, _out, err = run(["--root", root, "add-chapter", "OnlyOneSegment"])
            self.assertEqual(code, 1)
            self.assertIn("2-segment", err)

    def test_missing_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            code, _out, err = run(["--root", root, "add-chapter", "Nonexistent/Locking"])
            self.assertEqual(code, 1)
            self.assertIn("no metagroup segment matches", err)


class TestStatusAndAdrFlow(unittest.TestCase):
    def test_stable_requires_adr_then_succeeds_with_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            _c, out, _e = run(["--root", root, "--json", "add-part", "Concurrency"])
            object_id = json.loads(out)["id"]

            code, _out, err = run(["--root", root, "set-status", object_id, "stable"])
            self.assertEqual(code, 1)
            self.assertIn("adr", err)

            code, out, _err = run(["--root", root, "set-status", object_id, "stable", "--adr", "b1c2d3"])
            self.assertEqual(code, 0)
            self.assertIn("stable", out)

    def test_backward_transition_requires_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            _c, out, _e = run(["--root", root, "--json", "add-part", "Concurrency"])
            object_id = json.loads(out)["id"]
            run(["--root", root, "set-status", object_id, "stable", "--adr", "b1c2d3"])

            code, _out, err = run(["--root", root, "set-status", object_id, "draft"])
            self.assertEqual(code, 1)
            self.assertIn("--force", err)

            code, _out, _err = run(["--root", root, "set-status", object_id, "draft", "--force"])
            self.assertEqual(code, 0)

    def test_set_adr_then_status_transition_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            _c, out, _e = run(["--root", root, "--json", "add-part", "Concurrency"])
            object_id = json.loads(out)["id"]
            self.assertEqual(run(["--root", root, "set-adr", object_id, "b1c2d3"])[0], 0)
            self.assertEqual(run(["--root", root, "set-status", object_id, "stable"])[0], 0)


class TestDescriptionEditing(unittest.TestCase):
    def test_draft_content_change_untracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            _c, out, _e = run(["--root", root, "--json", "add-part", "Concurrency", "--description", "v1"])
            object_id = json.loads(out)["id"]
            self.assertEqual(run(["--root", root, "set-description", object_id, "v2"])[0], 0)
            _c, out, _e = run(["--root", root, "--json", "show", object_id])
            data = json.loads(out)
            self.assertEqual(data["content"]["Description"], "v2")
            self.assertEqual(len(data["history"]), 1)

    def test_stable_content_change_requires_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            _c, out, _e = run(["--root", root, "--json", "add-part", "Concurrency"])
            object_id = json.loads(out)["id"]
            run(["--root", root, "set-status", object_id, "stable", "--adr", "b1c2d3"])

            code, _out, _err = run(["--root", root, "set-description", object_id, "v2"])
            self.assertEqual(code, 0)  # already-set adr satisfies it


class TestRenameAndReorder(unittest.TestCase):
    def test_rename_updates_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            _c, out, _e = run(["--root", root, "--json", "add-part", "Concurrency"])
            object_id = json.loads(out)["id"]
            code, out, _err = run(["--root", root, "--json", "rename", object_id, "Renamed"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["name"], "Renamed")

    def test_reorder_moves_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            run(["--root", root, "add-part", "A"])
            run(["--root", root, "add-part", "B"])
            _c, out, _e = run(["--root", root, "--json", "add-part", "C"])
            object_id = json.loads(out)["id"]

            self.assertEqual(run(["--root", root, "reorder", object_id, "--after", "0"])[0], 0)
            _c, out, _e = run(["--root", root, "list"])
            names_in_order = [line.split("-", 4)[-1] for line in out.strip().splitlines()]
            self.assertEqual(names_in_order, ["C", "A", "B"])


class TestMove(unittest.TestCase):
    def test_move_reparents_section_and_subtree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            run(["--root", root, "add-part", "A"])
            _c, out, _e = run(["--root", root, "--json", "add-chapter", "A/Sub"])
            sub_id = json.loads(out)["id"]
            run(["--root", root, "add-section", "A/Sub/Grand"])
            run(["--root", root, "add-part", "B"])

            code, out, _err = run(["--root", root, "--json", "move-to-chapter", sub_id, "B"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["path"], ["002-B", "001-Sub"])

            _c, out, _e = run(["--root", root, "list"])
            names_in_order = [line.split("-", 4)[-1] for line in out.strip().splitlines()]
            self.assertEqual(names_in_order, ["A", "B", "Sub", "Grand"])

    def test_move_to_part_needs_no_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            run(["--root", root, "add-part", "A"])
            _c, out, _e = run(["--root", root, "--json", "add-chapter", "A/Sub"])
            sub_id = json.loads(out)["id"]

            code, out, _err = run(["--root", root, "--json", "move-to-part", sub_id])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["path"], ["002-Sub"])

    def test_move_rejects_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            _c, out, _e = run(["--root", root, "--json", "add-part", "A"])
            a_id = json.loads(out)["id"]
            run(["--root", root, "add-chapter", "A/Sub"])

            code, _out, err = run(["--root", root, "move-to-section", a_id, "A/Sub"])
            self.assertEqual(code, 1)
            self.assertIn("own subtree", err)

    def test_move_rejects_depth_cap_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            run(["--root", root, "add-part", "A"])
            _c, out, _e = run(["--root", root, "--json", "add-chapter", "A/A1"])
            a1_id = json.loads(out)["id"]
            run(["--root", root, "add-section", "A/A1/A2"])
            run(["--root", root, "add-part", "B"])
            run(["--root", root, "add-chapter", "B/C"])
            run(["--root", root, "add-section", "B/C/D"])
            run(["--root", root, "add-subsection", "B/C/D/E"])

            code, _out, err = run(["--root", root, "move-to-point", a1_id, "B/C/D/E"])
            self.assertEqual(code, 1)
            self.assertIn("5-level cap", err)


class TestListAndRender(unittest.TestCase):
    def test_list_filters_by_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            run(["--root", root, "add-part", "A"])
            _c, out, _e = run(["--root", root, "--json", "add-part", "B"])
            b_id = json.loads(out)["id"]
            run(["--root", root, "set-status", b_id, "stable", "--adr", "x"])

            _c, out, _e = run(["--root", root, "list", "--status", "stable"])
            self.assertEqual(out.strip(), f"stable B_____-002-{b_id}-B")

    def test_render_strips_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design.md")
            run(["--root", root, "add-part", "Concurrency", "--description", "Intro."])
            _code, out, _err = run(["--root", root, "render"])
            self.assertNotIn("<!--", out)
            self.assertIn("## Concurrency", out)
            self.assertIn("Intro.", out)


class TestMultiRootMergedReadOnly(unittest.TestCase):
    def test_write_rejected_with_multiple_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_a = str(Path(tmp) / "a.md")
            root_b = str(Path(tmp) / "b.md")
            run(["--root", root_a, "add-part", "FromA"])
            run(["--root", root_b, "add-part", "FromB"])

            code, out, _err = run(["--root", root_a, "--root", root_b, "list"])
            self.assertEqual(code, 0)
            self.assertEqual(len(out.strip().splitlines()), 2)

            code, _out, err = run(["--root", root_a, "--root", root_b, "add-part", "New"])
            self.assertEqual(code, 1)
            self.assertIn("read-only", err)


class TestDirectoryMode(unittest.TestCase):
    def test_nested_add_and_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design")
            self.assertEqual(
                run(["--root", root, "add-part", "Concurrency", "--description", "Intro."])[0], 0
            )
            self.assertEqual(
                run(["--root", root, "add-chapter", "Concurrency/Locking", "--description", "A lock."])[0],
                0,
            )
            code, out, _err = run(["--root", root, "--json", "show", "001-Concurrency/1"])
            self.assertEqual(code, 0)
            data = json.loads(out)
            self.assertEqual(data["name"], "Locking")
            self.assertEqual(data["content"]["Description"], "A lock.")

    def test_creates_directory_tree_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            run(["--root", str(root), "add-part", "Concurrency"])
            self.assertTrue(root.is_dir())
            children = [p for p in root.iterdir() if p.is_dir()]
            self.assertEqual(len(children), 1)
            self.assertTrue((children[0] / "_content.md").is_file())

    def test_status_rename_reorder_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = str(Path(tmp) / "design")
            run(["--root", root, "add-part", "A"])
            _c, out, _e = run(["--root", root, "--json", "add-part", "B"])
            b_id = json.loads(out)["id"]

            code, _out, err = run(["--root", root, "set-status", b_id, "stable"])
            self.assertEqual(code, 1)
            self.assertIn("adr", err)
            self.assertEqual(run(["--root", root, "set-status", b_id, "stable", "--adr", "b1c2d3"])[0], 0)

            self.assertEqual(run(["--root", root, "rename", b_id, "B Renamed"])[0], 0)
            _c, out, _e = run(["--root", root, "list"])
            self.assertIn("B_Renamed", out)

            _c, out, _e = run(["--root", root, "render"])
            self.assertNotIn("<!--", out)
            self.assertIn("## A", out)


if __name__ == "__main__":
    unittest.main()
