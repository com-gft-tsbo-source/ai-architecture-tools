import unittest

from lib.model import ObjectRecord
from lib.singlefile import parse_single_file, render_single_file
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


def make_record(**overrides) -> ObjectRecord:
    defaults = dict(
        object_id="a3f9c2", object_type="1", number=1, name="First task",
        status=" ", metagroup_levels=("001-Setup",),
        content={"Description": "Do it."},
    )
    defaults.update(overrides)
    return ObjectRecord(**defaults)


class TestEmptyFile(unittest.TestCase):
    def test_empty_text_round_trips(self):
        declarations, records = parse_single_file("", SPEC)
        self.assertEqual(declarations, [])
        self.assertEqual(records, [])
        self.assertEqual(render_single_file([], [], SPEC), "")


class TestSingleObjectNoMetagroups(unittest.TestCase):
    def test_round_trip(self):
        record = make_record()
        text = render_single_file([], [record], SPEC)
        self.assertNotIn("---", text)  # no separator needed for a single object
        declarations, records = parse_single_file(text, SPEC)
        self.assertEqual(declarations, [])
        self.assertEqual(records, [record])


class TestMultipleObjectsSeparator(unittest.TestCase):
    def test_separator_only_between_objects(self):
        first = make_record(object_id="aaaaaa", number=1, name="First")
        second = make_record(object_id="bbbbbb", number=2, name="Second")
        text = render_single_file([], [first, second], SPEC)
        self.assertFalse(text.startswith("---"))
        self.assertFalse(text.rstrip("\n").endswith("---"))
        self.assertIn("\n\n---\n\n", text)

    def test_round_trip_multiple_objects(self):
        first = make_record(object_id="aaaaaa", number=1, name="First")
        second = make_record(object_id="bbbbbb", number=2, name="Second")
        text = render_single_file([], [first, second], SPEC)
        declarations, records = parse_single_file(text, SPEC)
        self.assertEqual(declarations, [])
        self.assertEqual(records, [first, second])


class TestWithMetagroupsSection(unittest.TestCase):
    def test_round_trip_with_declarations_and_objects(self):
        from lib.metagroup import MetagroupDeclaration

        declarations = [
            MetagroupDeclaration(level_type="Phase", path="001-Setup", abbrev="1"),
            MetagroupDeclaration(level_type="Phase", path="002-Implementation", abbrev="2"),
        ]
        record = make_record()
        text = render_single_file(declarations, [record], SPEC)
        self.assertTrue(text.startswith("## Metagroups"))
        parsed_declarations, parsed_records = parse_single_file(text, SPEC)
        self.assertEqual(parsed_declarations, declarations)
        self.assertEqual(parsed_records, [record])

    def test_declarations_only_no_objects_yet(self):
        from lib.metagroup import MetagroupDeclaration

        declarations = [MetagroupDeclaration(level_type="Phase", path="001-Setup", abbrev="1")]
        text = render_single_file(declarations, [], SPEC)
        parsed_declarations, parsed_records = parse_single_file(text, SPEC)
        self.assertEqual(parsed_declarations, declarations)
        self.assertEqual(parsed_records, [])


if __name__ == "__main__":
    unittest.main()
