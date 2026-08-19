import unittest

from lib.history import HistoryEntry
from lib.spec_comment import (
    CommentData,
    SpecCommentError,
    extract_comment,
    parse_comment,
    render_comment,
)


class TestRenderComment(unittest.TestCase):
    def test_minimal_single_line(self):
        data = CommentData(object_id="f00d21", object_type="Pa____", number=1, status="draft")
        self.assertEqual(
            render_comment(data), "<!-- specctl id=f00d21 type=Pa____ nr=001 status=draft -->"
        )

    def test_with_adr(self):
        data = CommentData(
            object_id="a3f9c2", object_type="PaCh__", number=3, status="stable", adr="b1c2d3"
        )
        self.assertEqual(
            render_comment(data),
            "<!-- specctl id=a3f9c2 type=PaCh__ nr=003 status=stable adr=b1c2d3 -->",
        )

    def test_with_history_multiline(self):
        history = [
            HistoryEntry(timestamp="2026-08-17T15:45:48", prefix="M", message="Add"),
            HistoryEntry(
                timestamp="2026-08-18T09:10:00", prefix="M",
                old_status="draft", new_status="stable", message="adr=b1c2d3",
            ),
        ]
        data = CommentData(
            object_id="a3f9c2", object_type="PaCh__", number=3, status="stable",
            adr="b1c2d3", history=history,
        )
        rendered = render_comment(data)
        self.assertEqual(
            rendered,
            "<!-- specctl id=a3f9c2 type=PaCh__ nr=003 status=stable adr=b1c2d3\n"
            "history:\n"
            "- 2026-08-17T15:45:48: M | Add\n"
            "- 2026-08-18T09:10:00: M [draft] -> [stable] | adr=b1c2d3\n"
            "-->",
        )

    def test_with_open_questions(self):
        data = CommentData(
            object_id="f00d21", object_type="Pa____", number=1, status="draft",
            open_questions="Re-check after steal?",
        )
        rendered = render_comment(data)
        self.assertEqual(
            rendered,
            "<!-- specctl id=f00d21 type=Pa____ nr=001 status=draft\n"
            "open-questions:\n"
            "> Re-check after steal?\n"
            "-->",
        )


class TestParseComment(unittest.TestCase):
    def test_round_trips_minimal(self):
        original = CommentData(object_id="f00d21", object_type="Pa____", number=1, status="draft")
        parsed = parse_comment(render_comment(original))
        self.assertEqual(parsed, original)

    def test_round_trips_with_adr_and_history(self):
        history = [
            HistoryEntry(timestamp="2026-08-17T15:45:48", prefix="M", message="Add"),
            HistoryEntry(
                timestamp="2026-08-18T09:10:00", prefix="M",
                old_status="draft", new_status="stable", message="adr=b1c2d3",
            ),
        ]
        original = CommentData(
            object_id="a3f9c2", object_type="PaCh__", number=3, status="stable",
            adr="b1c2d3", history=history,
        )
        parsed = parse_comment(render_comment(original))
        self.assertEqual(parsed, original)

    def test_round_trips_with_open_questions_and_history(self):
        history = [HistoryEntry(timestamp="2026-08-17T15:45:48", prefix="M", message="Add")]
        original = CommentData(
            object_id="f00d21", object_type="Pa____", number=1, status="draft",
            open_questions="Line one.\nLine two.", history=history,
        )
        parsed = parse_comment(render_comment(original))
        self.assertEqual(parsed, original)

    def test_missing_required_attribute_raises(self):
        with self.assertRaises(SpecCommentError):
            parse_comment("<!-- specctl id=f00d21 status=draft -->")

    def test_malformed_nr_raises(self):
        with self.assertRaises(SpecCommentError):
            parse_comment("<!-- specctl id=f00d21 type=Pa____ nr=abc status=draft -->")

    def test_not_a_comment_raises(self):
        with self.assertRaises(SpecCommentError):
            parse_comment("just some text")


class TestExtractComment(unittest.TestCase):
    def test_extracts_single_line_comment_and_remaining_content(self):
        lines = [
            "",
            "<!-- specctl id=f00d21 type=Pa____ nr=001 status=draft -->",
            "",
            "Some prose.",
            "More prose.",
        ]
        comment_text, remaining = extract_comment(lines)
        self.assertEqual(comment_text, "<!-- specctl id=f00d21 type=Pa____ nr=001 status=draft -->")
        self.assertEqual(remaining, ["Some prose.", "More prose."])

    def test_extracts_multiline_comment(self):
        lines = [
            "<!-- specctl id=a3f9c2 type=PaCh__ nr=003 status=stable",
            "history:",
            "- 2026-08-17T15:45:48: M | Add",
            "-->",
            "",
            "A lock is held...",
        ]
        comment_text, remaining = extract_comment(lines)
        self.assertEqual(
            comment_text,
            "<!-- specctl id=a3f9c2 type=PaCh__ nr=003 status=stable\n"
            "history:\n"
            "- 2026-08-17T15:45:48: M | Add\n"
            "-->",
        )
        self.assertEqual(remaining, ["A lock is held..."])

    def test_missing_comment_raises(self):
        with self.assertRaises(SpecCommentError):
            extract_comment(["Just prose, no comment."])

    def test_unterminated_comment_raises(self):
        with self.assertRaises(SpecCommentError):
            extract_comment(["<!-- specctl id=f00d21 type=Pa____ nr=001 status=draft", "still open"])


if __name__ == "__main__":
    unittest.main()
