import unittest

from lib.spec_document import SpecDocumentError, parse_document, render_document
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
    def test_preamble_preserved(self):
        preamble, _sections = parse_document(_DOC)
        self.assertEqual(preamble, "# Design Criteria\n\nSome intro text about the document.")

    def test_section_count_and_order(self):
        _preamble, sections = parse_document(_DOC)
        self.assertEqual([s.name for s in sections], [
            "Concurrency", "Locking", "Timeout Behaviour", "Index Files",
        ])

    def test_ancestor_levels_track_nesting(self):
        _preamble, sections = parse_document(_DOC)
        by_name = {s.name: s for s in sections}
        self.assertEqual(by_name["Concurrency"].ancestor_levels, ())
        self.assertEqual(by_name["Locking"].ancestor_levels, ("001-Concurrency",))
        self.assertEqual(
            by_name["Timeout Behaviour"].ancestor_levels, ("001-Concurrency", "001-Locking")
        )
        # sibling of Locking under the same parent, not nested under it
        self.assertEqual(by_name["Index Files"].ancestor_levels, ("001-Concurrency",))

    def test_levels(self):
        _preamble, sections = parse_document(_DOC)
        by_name = {s.name: s for s in sections}
        self.assertEqual(by_name["Concurrency"].level, 1)
        self.assertEqual(by_name["Locking"].level, 2)
        self.assertEqual(by_name["Timeout Behaviour"].level, 3)
        self.assertEqual(by_name["Index Files"].level, 2)

    def test_content_and_metadata(self):
        _preamble, sections = parse_document(_DOC)
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

    def test_skipped_depth_raises(self):
        bad = """## Concurrency

<!-- specctl id=a1a1a1 type=Co____ nr=001 status=draft -->

Content.

#### Timeout Behaviour

<!-- specctl id=f00d21 type=CoLoTi nr=001 status=draft -->

Content.
"""
        with self.assertRaises(SpecDocumentError):
            parse_document(bad)

    def test_duplicate_id_raises(self):
        bad = """## Concurrency

<!-- specctl id=a1a1a1 type=Co____ nr=001 status=draft -->

Content.

## Another

<!-- specctl id=a1a1a1 type=An____ nr=002 status=draft -->

Content.
"""
        with self.assertRaises(SpecDocumentError):
            parse_document(bad)

    def test_missing_comment_raises(self):
        bad = "## Concurrency\n\nContent without a metadata comment.\n"
        with self.assertRaises(SpecDocumentError):
            parse_document(bad)

    def test_empty_document_no_headings(self):
        preamble, sections = parse_document("Just plain text, no headings at all.\n")
        self.assertEqual(preamble, "Just plain text, no headings at all.\n")
        self.assertEqual(sections, [])


class TestRenderDocument(unittest.TestCase):
    def test_round_trip(self):
        preamble, sections = parse_document(_DOC)
        rendered = render_document(preamble, sections)
        reparsed_preamble, reparsed_sections = parse_document(rendered)
        self.assertEqual(reparsed_preamble, preamble)
        self.assertEqual([s.name for s in reparsed_sections], [s.name for s in sections])
        self.assertEqual(
            [s.ancestor_levels for s in reparsed_sections], [s.ancestor_levels for s in sections]
        )
        self.assertEqual(
            [s.description() for s in reparsed_sections], [s.description() for s in sections]
        )

    def test_render_empty_document(self):
        self.assertEqual(render_document("", []), "\n")

    def test_render_single_section_no_description(self):
        section = SpecSection(
            object_id="f00d21", object_type="Pa____", number=1, name="Empty Part", status="draft",
        )
        rendered = render_document("", [section])
        self.assertEqual(
            rendered,
            "## Empty Part\n\n<!-- specctl id=f00d21 type=Pa____ nr=001 status=draft -->\n",
        )


if __name__ == "__main__":
    unittest.main()
