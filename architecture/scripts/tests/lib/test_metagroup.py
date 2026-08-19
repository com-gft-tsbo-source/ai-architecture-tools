import tempfile
import unittest
from pathlib import Path

from lib.metagroup import (
    MetagroupDeclaration,
    MetagroupError,
    assign_leaf_name,
    dir_collect_known_types,
    dir_create_path,
    dir_object_type_for,
    dir_path_exists,
    dir_sibling_names,
    parse_metagroups_section,
    render_metagroups_section,
    resolve_segment,
    sf_create_path,
    sf_object_type_for,
    sf_path_exists,
    sf_sibling_names,
)


class TestDirectoryMode(unittest.TestCase):
    def test_create_top_level_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            object_type = dir_create_path(root, ["001-Setup"])
            self.assertTrue(dir_path_exists(root, ["001-Setup"]))
            self.assertEqual(dir_object_type_for(root, ["001-Setup"]), object_type)

    def test_creating_child_before_parent_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(MetagroupError):
                dir_create_path(root, ["Python", "001-backend"])

    def test_creating_existing_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dir_create_path(root, ["Python"])
            with self.assertRaises(MetagroupError):
                dir_create_path(root, ["Python"])

    def test_referencing_missing_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(MetagroupError):
                dir_object_type_for(root, ["Nonexistent"])

    def test_two_level_path_collision_resolution_matches_design_doc_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dir_create_path(root, ["backend"])
            login_type = dir_create_path(root, ["backend", "login"])
            self.assertEqual(login_type, "baclog")
            logik_type = dir_create_path(root, ["backend", "logik"])
            self.assertEqual(logik_type, "baclok")

    def test_collision_resolution_with_prefixed_ancestor(self):
        # Regression: dir_collect_known_types must feed derive_object_type
        # STRIPPED source names, even when the ancestor level itself carries
        # a <nr>- sort prefix (e.g. auto-numbered, see corrections.md).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dir_create_path(root, ["001-backend"])
            login_type = dir_create_path(root, ["001-backend", "login"])
            self.assertEqual(login_type, "baclog")
            logik_type = dir_create_path(root, ["001-backend", "logik"])
            self.assertEqual(logik_type, "baclok")

    def test_explicit_abbrev_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            object_type = dir_create_path(root, ["Python"], abbrev_override="py")
            self.assertEqual(object_type, "py____")

    def test_object_type_fn_override_bypasses_abbrev_scheme(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def phase_number(level_names):
                return str(int(level_names[-1].split("-", 1)[0]))

            object_type = dir_create_path(root, ["002-Implementation"], object_type_fn=phase_number)
            self.assertEqual(object_type, "2")

    def test_collect_known_types_walks_whole_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dir_create_path(root, ["Python"])
            dir_create_path(root, ["Python", "001-backend"])
            known = dir_collect_known_types(root)
            self.assertEqual(len(known), 2)
            self.assertIn(("Python",), known.values())
            self.assertIn(("Python", "001-backend"), known.values())


class TestSingleFileMode(unittest.TestCase):
    def test_create_and_lookup(self):
        declarations, object_type = sf_create_path([], "Phase", ["001-Setup"])
        self.assertEqual(sf_object_type_for(declarations, ["001-Setup"]), object_type)

    def test_creating_child_before_parent_raises(self):
        with self.assertRaises(MetagroupError):
            sf_create_path([], "Context", ["Python", "001-backend"])

    def test_creating_existing_path_raises(self):
        declarations, _ = sf_create_path([], "Language", ["Python"])
        with self.assertRaises(MetagroupError):
            sf_create_path(declarations, "Language", ["Python"])

    def test_referencing_missing_path_raises(self):
        with self.assertRaises(MetagroupError):
            sf_object_type_for([], ["Nonexistent"])

    def test_collision_resolution_matches_design_doc_example(self):
        declarations, _ = sf_create_path([], "Context", ["backend"])
        declarations, login_type = sf_create_path(declarations, "Category", ["backend", "login"])
        self.assertEqual(login_type, "baclog")
        declarations, logik_type = sf_create_path(declarations, "Category", ["backend", "logik"])
        self.assertEqual(logik_type, "baclok")

    def test_section_round_trip(self):
        declarations, _ = sf_create_path([], "Phase", ["001-Setup"])
        declarations, _ = sf_create_path(declarations, "Phase", ["002-Implementation"])
        text = render_metagroups_section(declarations)
        body_lines = text.split("\n")[2:]  # drop heading + blank line
        parsed = parse_metagroups_section(body_lines)
        self.assertEqual(parsed, declarations)

    def test_malformed_line_raises(self):
        with self.assertRaises(MetagroupError):
            parse_metagroups_section(["- not a valid line"])


class TestAssignLeafName(unittest.TestCase):
    def test_explicit_prefix_used_verbatim(self):
        self.assertEqual(assign_leaf_name([], "001-Setup"), "001-Setup")

    def test_auto_numbers_first_sibling(self):
        self.assertEqual(assign_leaf_name([], "Setup"), "001-Setup")

    def test_auto_numbers_max_plus_one(self):
        self.assertEqual(assign_leaf_name(["001-Setup", "002-Implementation"], "Testing"), "003-Testing")

    def test_auto_numbering_ignores_non_prefixed_siblings(self):
        self.assertEqual(assign_leaf_name(["Setup"], "Testing"), "001-Testing")


class TestResolveSegment(unittest.TestCase):
    SIBLINGS = ["001-Setup", "002-Implementation"]

    def test_exact_form(self):
        self.assertEqual(resolve_segment(self.SIBLINGS, "001-Setup"), "001-Setup")

    def test_bare_number(self):
        self.assertEqual(resolve_segment(self.SIBLINGS, "2"), "002-Implementation")

    def test_bare_name(self):
        self.assertEqual(resolve_segment(self.SIBLINGS, "Setup"), "001-Setup")

    def test_no_match_raises(self):
        with self.assertRaises(MetagroupError):
            resolve_segment(self.SIBLINGS, "Nonexistent")

    def test_ambiguous_name_raises(self):
        siblings = ["001-Setup", "002-Setup"]
        with self.assertRaises(MetagroupError):
            resolve_segment(siblings, "Setup")


class TestSiblingNames(unittest.TestCase):
    def test_dir_sibling_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dir_create_path(root, ["001-Setup"])
            dir_create_path(root, ["002-Implementation"])
            self.assertEqual(set(dir_sibling_names(root, [])), {"001-Setup", "002-Implementation"})

    def test_dir_sibling_names_missing_parent_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dir_sibling_names(Path(tmp), ["Nonexistent"]), [])

    def test_sf_sibling_names(self):
        declarations, _ = sf_create_path([], "Phase", ["001-Setup"])
        declarations, _ = sf_create_path(declarations, "Phase", ["002-Implementation"])
        self.assertEqual(set(sf_sibling_names(declarations, [])), {"001-Setup", "002-Implementation"})

    def test_sf_sibling_names_nested(self):
        declarations, _ = sf_create_path([], "Language", ["Python"])
        declarations, _ = sf_create_path(declarations, "Context", ["Python", "001-backend"])
        declarations, _ = sf_create_path(declarations, "Context", ["Python", "002-frontend"])
        self.assertEqual(set(sf_sibling_names(declarations, ["Python"])), {"001-backend", "002-frontend"})
        self.assertEqual(sf_sibling_names(declarations, []), ["Python"])


if __name__ == "__main__":
    unittest.main()
