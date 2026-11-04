import json
import unittest

from lib.history import HistoryEntry
from lib.model import MetainfoEntry, ObjectRecord
from lib.render import (
    combined_history, full_display, render_list, short_line, short_with_history, to_json,
)
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec

SPEC = ToolSpec(
    name="rulectl",
    metagroup_levels=(MetagroupLevelSpec(type="Language"),),
    metainfo=(MetainfoSpec(type="weight"),),
    status=StatusSpec(codes=("draft", "active"), initial="active"),
    user_content_blocks=("Description", "Procedure"),
    root_name="rules",
    default_mode="directory",
)


def make_record(**overrides) -> ObjectRecord:
    defaults = dict(
        object_id="a3f9c2", object_type="Python_", number=1, name="No bare except",
        status="active", metagroup_levels=("Python",),
        metainfo=[MetainfoEntry(type="weight", value="high")],
        content={"Description": "Explain the rule.", "Procedure": "Run ruff."},
    )
    defaults.update(overrides)
    return ObjectRecord(**defaults)


class TestShortLine(unittest.TestCase):
    def test_includes_status_and_signature(self):
        record = make_record()
        line = short_line(record)
        self.assertIn(record.status, line)
        self.assertIn(record.signature, line)


class TestFullDisplay(unittest.TestCase):
    def test_includes_metainfo_and_blocks(self):
        record = make_record()
        text = full_display(record, SPEC)
        self.assertIn("weight: high", text)
        self.assertIn("Explain the rule.", text)
        self.assertIn("Procedure:", text)
        self.assertIn("Run ruff.", text)

    def test_omits_empty_blocks(self):
        record = make_record(content={"Description": "Only description."})
        text = full_display(record, SPEC)
        self.assertNotIn("Procedure:", text)


class TestShortWithHistory(unittest.TestCase):
    def test_no_history_omits_section(self):
        record = make_record(history=[])
        text = short_with_history(record)
        self.assertEqual(text, short_line(record))

    def test_includes_history_entries(self):
        record = make_record(
            history=[HistoryEntry(timestamp="2026-08-17T10:00:00", prefix="M", message="Object created")]
        )
        text = short_with_history(record)
        self.assertIn("Object created", text)


class TestCombinedHistory(unittest.TestCase):
    def test_sorted_newest_first_across_objects(self):
        older = make_record(
            object_id="aaaaaa",
            history=[HistoryEntry(timestamp="2026-08-17T10:00:00", prefix="M", message="First created")],
        )
        newer = make_record(
            object_id="bbbbbb",
            history=[HistoryEntry(timestamp="2026-08-17T12:00:00", prefix="M", message="Second created")],
        )
        text = combined_history([older, newer])
        lines = text.split("\n")
        self.assertTrue(lines[0].endswith("Second created"))
        self.assertTrue(lines[-1].endswith("First created"))
        self.assertTrue(lines[0].startswith(newer.signature))


class TestToJson(unittest.TestCase):
    def test_single_record(self):
        record = make_record()
        data = json.loads(to_json(record))
        self.assertEqual(data["id"], "a3f9c2")
        self.assertEqual(data["metainfo"], {"weight": "high"})

    def test_list_of_records(self):
        records = [make_record(object_id="aaaaaa"), make_record(object_id="bbbbbb")]
        data = json.loads(to_json(records))
        self.assertEqual(len(data), 2)
        self.assertEqual({d["id"] for d in data}, {"aaaaaa", "bbbbbb"})


class TestRenderList(unittest.TestCase):
    def test_list_line_followed_by_indented_description(self):
        record = make_record(content={"Description": "First line.\n\n- item", "Procedure": "Run ruff."})
        self.assertEqual(
            render_list([record], SPEC),
            f"{short_line(record)}\n    First line.\n\n    - item",
        )

    def test_entries_separated_by_blank_line_and_other_blocks_omitted(self):
        with_desc = make_record(object_id="aaaaaa")
        without_desc = make_record(object_id="bbbbbb", number=2, content={"Procedure": "Run ruff."})
        out = render_list([with_desc, without_desc], SPEC)
        self.assertEqual(
            out, f"{short_line(with_desc)}\n    Explain the rule.\n\n{short_line(without_desc)}",
        )
        self.assertNotIn("Run ruff.", out)

    def test_empty(self):
        self.assertEqual(render_list([], SPEC), "")

    def test_meta_shows_set_metainfo_before_description(self):
        record = make_record(metainfo=[MetainfoEntry(type="weight", value="high"),
                                       MetainfoEntry(type="tool", value="")])
        self.assertEqual(
            render_list([record], SPEC, meta=True),
            f"{short_line(record)}\n    weight: high\n    Explain the rule.",
        )

    def test_full_labels_every_block_in_spec_order_and_adds_history(self):
        entry = HistoryEntry(timestamp="2026-11-04T10:00:00", prefix="M", message="Object created")
        record = make_record(history=[entry])
        self.assertEqual(
            render_list([record], SPEC, full=True),
            f"{short_line(record)}\n"
            "    Description:\n        Explain the rule.\n"
            "    Procedure:\n        Run ruff.\n"
            "    History:\n        - 2026-11-04T10:00:00: M | Object created",
        )

    def test_full_without_meta_omits_metainfo(self):
        self.assertNotIn("weight: high", render_list([make_record()], SPEC, full=True))


if __name__ == "__main__":
    unittest.main()
