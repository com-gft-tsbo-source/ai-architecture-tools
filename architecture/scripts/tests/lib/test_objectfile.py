import unittest

from lib.history import HistoryEntry
from lib.model import MetainfoEntry, ObjectRecord
from lib.objectfile import ObjectFileError, parse_object, render_object
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec

TASKCTL_SPEC = ToolSpec(
    name="taskctl",
    metagroup_levels=(MetagroupLevelSpec(type="Phase"),),
    metainfo=(
        MetainfoSpec(type="review"),
        MetainfoSpec(type="assignee-type"),
        MetainfoSpec(type="assignee-name"),
    ),
    status=StatusSpec(codes=("[ ]", "[~]", "[X]"), initial="[ ]"),
    user_content_blocks=("Description",),
)

RULECTL_SPEC = ToolSpec(
    name="rulectl",
    metagroup_levels=(
        MetagroupLevelSpec(type="Language"),
        MetagroupLevelSpec(type="Context"),
        MetagroupLevelSpec(type="Category"),
    ),
    metainfo=(MetainfoSpec(type="weight"), MetainfoSpec(type="tool")),
    status=StatusSpec(codes=("draft", "active", "obsolete"), initial="active"),
    user_content_blocks=("Description", "Procedure"),
)

ADRCTL_SPEC = ToolSpec(
    name="adrctl",
    metagroup_levels=(MetagroupLevelSpec(type="Domain"), MetagroupLevelSpec(type="Component")),
    metainfo=(MetainfoSpec(type="superseded-by"),),
    status=StatusSpec(codes=("proposed", "accepted"), initial="proposed"),
    user_content_blocks=("Motivation", "Description", "Rationale"),
)


class TestRoundTrip(unittest.TestCase):
    def test_taskctl_minimal(self):
        record = ObjectRecord(
            object_id="a3f9c2",
            object_type="2",
            number=5,
            name="Configure database connection",
            status="[ ]",
            metagroup_levels=("002-Implementation",),
            content={"Description": "Do the thing."},
        )
        text = render_object(record, TASKCTL_SPEC)
        parsed = parse_object(text, TASKCTL_SPEC)
        self.assertEqual(parsed, record)

    def test_rulectl_three_levels_and_metainfo(self):
        record = ObjectRecord(
            object_id="a3f9c2",
            object_type="baclok",
            number=1,
            name="No bare except",
            status="active",
            metagroup_levels=("Python", "001-backend", "002-validation"),
            metainfo=[MetainfoEntry(type="weight", value="high"), MetainfoEntry(type="tool", value="ruff")],
            content={"Description": "Explain the rule.", "Procedure": "Run ruff check."},
        )
        text = render_object(record, RULECTL_SPEC)
        parsed = parse_object(text, RULECTL_SPEC)
        self.assertEqual(parsed, record)

    def test_adrctl_with_history(self):
        record = ObjectRecord(
            object_id="beefee",
            object_type="baco",
            number=2,
            name="Use event sourcing",
            status="accepted",
            metagroup_levels=("Backend", "001-orders"),
            metainfo=[],
            content={
                "Motivation": "We need an audit trail.",
                "Description": "Adopt event sourcing for orders.",
                "Rationale": "Simplifies replay and debugging.",
            },
            history=[
                HistoryEntry(timestamp="2026-08-17T10:00:00", prefix="M", message="Object created"),
                HistoryEntry(
                    timestamp="2026-08-17T11:00:00", prefix="M",
                    old_status="proposed", new_status="accepted", message="Accepted after review",
                ),
            ],
        )
        text = render_object(record, ADRCTL_SPEC)
        parsed = parse_object(text, ADRCTL_SPEC)
        self.assertEqual(parsed, record)

    def test_empty_description_round_trips(self):
        record = ObjectRecord(
            object_id="a3f9c2", object_type="2", number=1, name="Empty",
            status="[ ]", metagroup_levels=("001-Setup",),
        )
        text = render_object(record, TASKCTL_SPEC)
        parsed = parse_object(text, TASKCTL_SPEC)
        self.assertEqual(parsed.content.get("Description", ""), "")

    def test_multiline_description_round_trips(self):
        record = ObjectRecord(
            object_id="a3f9c2", object_type="2", number=1, name="Multi",
            status="[ ]", metagroup_levels=("001-Setup",),
            content={"Description": "line one\n\nline three"},
        )
        text = render_object(record, TASKCTL_SPEC)
        parsed = parse_object(text, TASKCTL_SPEC)
        self.assertEqual(parsed.content["Description"], "line one\n\nline three")


class TestParseErrors(unittest.TestCase):
    def test_missing_h1_raises(self):
        with self.assertRaises(ObjectFileError):
            parse_object("## Meta\n\n- ID: x\n", TASKCTL_SPEC)

    def test_missing_meta_section_raises(self):
        text = "# sig\n\n## Some Name\n\n> desc\n\n## History\n"
        with self.assertRaises(ObjectFileError):
            parse_object(text, TASKCTL_SPEC)

    def test_missing_fixed_meta_field_raises(self):
        text = (
            "# sig\n\n## Meta\n\n- ID: a3f9c2\n- Type: 2\n- Number: 001\n"
            "- Phase: 001-Setup\n\n## Some Name\n\n> desc\n\n## History\n"
        )
        with self.assertRaises(ObjectFileError):
            parse_object(text, TASKCTL_SPEC)  # missing Status

    def test_two_name_sections_raises(self):
        text = (
            "# sig\n\n## Meta\n\n- ID: a3f9c2\n- Type: 2\n- Number: 001\n"
            "- Status: [ ]\n- Phase: 001-Setup\n\n"
            "## First\n\n> a\n\n## Second\n\n> b\n\n## History\n"
        )
        with self.assertRaises(ObjectFileError):
            parse_object(text, TASKCTL_SPEC)


if __name__ == "__main__":
    unittest.main()
