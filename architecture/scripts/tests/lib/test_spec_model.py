import unittest

from lib.spec_model import HEADING_MARKS, LEVEL_TYPES, MAX_LEVEL, SpecModelError, SpecSection


def make_section(**overrides):
    defaults = dict(
        object_id="a3f9c2",
        object_type="Lo____",
        number=3,
        name="Locking",
        status="draft",
        ancestor_levels=("001-Design",),
    )
    defaults.update(overrides)
    return SpecSection(**defaults)


class TestSpecSection(unittest.TestCase):
    def test_level_from_ancestor_count(self):
        section = make_section()
        self.assertEqual(section.level, 2)
        self.assertEqual(section.level_type, "Chapter")

    def test_level_one_has_no_ancestors(self):
        section = make_section(ancestor_levels=())
        self.assertEqual(section.level, 1)
        self.assertEqual(section.level_type, "Part")

    def test_heading_mark_matches_level(self):
        section = make_section()
        self.assertEqual(section.heading_mark, "###")

    def test_own_name_and_path_levels(self):
        section = make_section()
        self.assertEqual(section.own_name, "003-Locking")
        self.assertEqual(section.path_levels, ("001-Design", "003-Locking"))

    def test_signature_escapes_name(self):
        section = make_section(name="Locking & Timeouts")
        self.assertEqual(section.signature, "Lo____-003-a3f9c2-Locking___Timeouts")

    def test_description_defaults_to_empty(self):
        section = make_section()
        self.assertEqual(section.description(), "")
        section.content["Description"] = "A lock is held..."
        self.assertEqual(section.description(), "A lock is held...")

    def test_depth_beyond_max_level_rejected(self):
        with self.assertRaises(SpecModelError):
            make_section(ancestor_levels=("1", "2", "3", "4", "5"))

    def test_level_types_and_marks_cover_five_levels(self):
        self.assertEqual(len(LEVEL_TYPES), 5)
        self.assertEqual(MAX_LEVEL, 5)
        self.assertEqual(HEADING_MARKS[1], "##")
        self.assertEqual(HEADING_MARKS[5], "######")


if __name__ == "__main__":
    unittest.main()
