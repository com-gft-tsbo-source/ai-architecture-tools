import unittest

from lib.spec_document import (
    SpecDocumentError,
    parse_document,
    render_document,
    validate_preamble,
)
from lib.spec_model import SpecSection

_DOC = """# Design Criteria

Some intro text about the document.

## Concurrency

<!-- specctl id=a1a1a1 type=Co____ nr=001 status=draft -->

Top-level chapter content.

### Locking

<!-- specctl id=a3f9c2 type=CoLo__ nr=001 status=stable adr=b1c2d3
history:
- 2026-08-17T15:45:48: M | Add
- 2026-08-18T09:10:00: M [draft] -> [stable] | adr=b1c2d3
-->

A lock is held for the duration of a single invocation only.

#### Timeout Behaviour

<!-- specctl id=f00d21 type=CoLoTi nr=001 status=draft -->

Waiting instances time out after 3 minutes.

### Index Files

<!-- specctl id=b2b2b2 type=CoIn__ nr=002 status=draft -->

Two files per metagroup-path directory.
"""


class TestParseDocument(unittest.TestCase):
    def test_title_extracted(self):
        title, _preamble, _sections = parse_document(_DOC)
        self.assertEqual(title, "Design Criteria")

    def test_preamble_extracted(self):
        _title, preamble, _sections = parse_document(_DOC)
        self.assertEqual(preamble, "Some intro text about the document.")

    def test_section_count_and_order(self):
        _title, _preamble, sections = parse_document(_DOC)
        self.assertEqual([s.name for s in sections], [
            "Concurrency", "Locking", "Timeout Behaviour", "Index Files",
        ])

    def test_ancestor_levels_track_nesting(self):
        _title, _preamble, sections = parse_document(_DOC)
        by_name = {s.name: s for s in sections}
        self.assertEqual(by_name["Concurrency"].ancestor_levels, ())
        self.assertEqual(by_name["Locking"].ancestor_levels, ("001-Concurrency",))
        self.assertEqual(
            by_name["Timeout Behaviour"].ancestor_levels, ("001-Concurrency", "001-Locking")
        )
        # sibling of Locking under the same parent, not nested under it
        self.assertEqual(by_name["Index Files"].ancestor_levels, ("001-Concurrency",))

    def test_levels(self):
        _title, _preamble, sections = parse_document(_DOC)
        by_name = {s.name: s for s in sections}
        self.assertEqual(by_name["Concurrency"].level, 1)
        self.assertEqual(by_name["Locking"].level, 2)
        self.assertEqual(by_name["Timeout Behaviour"].level, 3)
        self.assertEqual(by_name["Index Files"].level, 2)

    def test_content_and_metadata(self):
        _title, _preamble, sections = parse_document(_DOC)
        by_name = {s.name: s for s in sections}
        locking = by_name["Locking"]
        self.assertEqual(locking.object_id, "a3f9c2")
        self.assertEqual(locking.object_type, "CoLo__")
        self.assertEqual(locking.status, "stable")
        self.assertEqual(locking.adr, "b1c2d3")
        self.assertEqual(
            locking.description(), "A lock is held for the duration of a single invocation only."
        )
        self.assertEqual(len(locking.history), 2)

    def test_skipped_depth_parses_under_nearest_shallower_heading(self):
        # design-specctl.md, "Metagroups": a branch may skip levels.
        text = """# Title

## Concurrency

<!-- specctl id=a1a1a1 type=Co____ nr=001 status=draft -->

Content.

#### Timeout Behaviour

<!-- specctl id=f00d21 type=Co__Ti nr=001 status=draft -->

Content.
"""
        _title, _preamble, sections = parse_document(text)
        timeout = sections[1]
        self.assertEqual(timeout.level, 3)
        self.assertEqual(timeout.ancestor_levels, ("001-Concurrency",))
        self.assertEqual(render_document("Title", "", sections), text)

    def test_root_level_heading_must_be_a_part(self):
        bad = """# Title

### Orphan Chapter

<!-- specctl id=a1a1a1 type=__Or__ nr=001 status=draft -->
"""
        with self.assertRaises(SpecDocumentError):
            parse_document(bad)

    def test_sibling_after_skipped_child_attaches_to_shared_parent(self):
        text = """# Title

## A

<!-- specctl id=a1a1a1 type=A_____ nr=001 status=draft -->

###### Deep Point

<!-- specctl id=b2b2b2 type=A_______De nr=001 status=draft -->

### Chapter

<!-- specctl id=c3c3c3 type=A_Ch nr=002 status=draft -->
"""
        _title, _preamble, sections = parse_document(text)
        self.assertEqual([s.level for s in sections], [1, 5, 2])
        self.assertEqual(sections[2].ancestor_levels, ("001-A",))

    def test_duplicate_id_raises(self):
        bad = """# Title

## Concurrency

<!-- specctl id=a1a1a1 type=Co____ nr=001 status=draft -->

Content.

## Another

<!-- specctl id=a1a1a1 type=An____ nr=002 status=draft -->

Content.
"""
        with self.assertRaises(SpecDocumentError):
            parse_document(bad)

    def test_missing_comment_raises(self):
        bad = "# Title\n\n## Concurrency\n\nContent without a metadata comment.\n"
        with self.assertRaises(SpecDocumentError):
            parse_document(bad)

    def test_empty_document_no_headings_but_with_title(self):
        title, preamble, sections = parse_document("# Just a Title\n\nSome plain text, no Sections.\n")
        self.assertEqual(title, "Just a Title")
        self.assertEqual(preamble, "Some plain text, no Sections.")
        self.assertEqual(sections, [])

    def test_missing_title_raises(self):
        with self.assertRaises(SpecDocumentError):
            parse_document("Just plain text, no title heading at all.\n")

    def test_empty_text_raises(self):
        with self.assertRaises(SpecDocumentError):
            parse_document("")


class TestRenderDocument(unittest.TestCase):
    def test_round_trip(self):
        title, preamble, sections = parse_document(_DOC)
        rendered = render_document(title, preamble, sections)
        reparsed_title, reparsed_preamble, reparsed_sections = parse_document(rendered)
        self.assertEqual(reparsed_title, title)
        self.assertEqual(reparsed_preamble, preamble)
        self.assertEqual([s.name for s in reparsed_sections], [s.name for s in sections])
        self.assertEqual(
            [s.ancestor_levels for s in reparsed_sections], [s.ancestor_levels for s in sections]
        )
        self.assertEqual(
            [s.description() for s in reparsed_sections], [s.description() for s in sections]
        )

    def test_render_empty_document(self):
        self.assertEqual(render_document("Empty Doc", "", []), "# Empty Doc\n")

    def test_render_includes_preamble(self):
        rendered = render_document("Doc", "Some intro.", [])
        self.assertEqual(rendered, "# Doc\n\nSome intro.\n")

    def test_render_single_section_no_description(self):
        section = SpecSection(
            object_id="f00d21", object_type="Pa____", number=1, name="Empty Part", status="draft",
        )
        rendered = render_document("Doc", "", [section])
        self.assertEqual(
            rendered,
            "# Doc\n\n## Empty Part\n\n<!-- specctl id=f00d21 type=Pa____ nr=001 status=draft -->\n",
        )


class TestValidatePreamble(unittest.TestCase):
    def test_plain_text_accepted(self):
        validate_preamble("Just some intro text.\n\nMore text.")  # does not raise

    def test_empty_accepted(self):
        validate_preamble("")  # does not raise

    def test_heading_line_rejected(self):
        with self.assertRaises(SpecDocumentError):
            validate_preamble("Some intro.\n\n## Looks like a Section\n\nMore text.")

    def test_deep_heading_line_rejected(self):
        with self.assertRaises(SpecDocumentError):
            validate_preamble("###### Looks like a Point")

    def test_single_hash_line_accepted(self):
        # A single '#' is the Title's own marker, not a Section heading --
        # only '##' through '######' (_HEADING_RE) are dangerous here.
        validate_preamble("# Not a Section heading, just a stray line")


if __name__ == "__main__":
    unittest.main()
