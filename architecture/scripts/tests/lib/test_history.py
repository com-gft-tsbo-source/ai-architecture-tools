import unittest

from lib.history import HistoryEntry, format_entry, format_log, parse_history

EXAMPLE_LOG = (
    "- 2026-08-17T15:45:48: M [draft] -> [active] | Status set to active\n"
    "- 2026-08-17T15:46:02: T [~] -> [~] |\n"
    "  > Research on signature escaping complete,\n"
    "  > proposal is in review.\n"
    "- 2026-08-17T16:01:10: M | Description refined"
)


class TestParseHistory(unittest.TestCase):
    def test_parses_example_log_from_design_doc(self):
        entries = parse_history(EXAMPLE_LOG)
        self.assertEqual(len(entries), 3)

        first = entries[0]
        self.assertEqual(first.timestamp, "2026-08-17T15:45:48")
        self.assertEqual(first.prefix, "M")
        self.assertEqual(first.old_status, "draft")
        self.assertEqual(first.new_status, "active")
        self.assertEqual(first.message, "Status set to active")

        second = entries[1]
        self.assertEqual(second.prefix, "T")
        self.assertEqual(second.old_status, "~")
        self.assertEqual(second.new_status, "~")
        self.assertEqual(
            second.message,
            "Research on signature escaping complete,\nproposal is in review.",
        )

        third = entries[2]
        self.assertFalse(third.has_transition)
        self.assertEqual(third.message, "Description refined")

    def test_round_trip(self):
        entries = parse_history(EXAMPLE_LOG)
        self.assertEqual(format_log(entries), EXAMPLE_LOG)

    def test_continuation_without_entry_raises(self):
        with self.assertRaises(ValueError):
            parse_history("  > orphan continuation")

    def test_malformed_line_raises(self):
        with self.assertRaises(ValueError):
            parse_history("not a history line at all")


class TestFormatEntry(unittest.TestCase):
    def test_m_omits_transition_when_unchanged(self):
        entry = HistoryEntry(timestamp="2026-08-17T00:00:00", prefix="M", message="edited")
        self.assertEqual(
            format_entry(entry), "- 2026-08-17T00:00:00: M | edited"
        )

    def test_t_always_shows_transition_even_if_unchanged(self):
        entry = HistoryEntry(
            timestamp="2026-08-17T00:00:00", prefix="T",
            old_status="~", new_status="~", message="progress",
        )
        self.assertEqual(
            format_entry(entry),
            "- 2026-08-17T00:00:00: T [~] -> [~] | progress",
        )

    def test_empty_message_no_trailing_space(self):
        entry = HistoryEntry(timestamp="2026-08-17T00:00:00", prefix="M")
        self.assertEqual(format_entry(entry), "- 2026-08-17T00:00:00: M |")

    def test_multiline_message_uses_continuation(self):
        entry = HistoryEntry(
            timestamp="2026-08-17T00:00:00", prefix="M", message="line one\nline two",
        )
        self.assertEqual(
            format_entry(entry),
            "- 2026-08-17T00:00:00: M |\n  > line one\n  > line two",
        )

    def test_message_starting_with_dash_rejected(self):
        entry = HistoryEntry(
            timestamp="2026-08-17T00:00:00", prefix="M", message="ok\n- looks like an entry",
        )
        with self.assertRaises(ValueError):
            format_entry(entry)

    def test_message_starting_with_continuation_prefix_rejected(self):
        entry = HistoryEntry(
            timestamp="2026-08-17T00:00:00", prefix="M", message="ok\n  > looks like continuation",
        )
        with self.assertRaises(ValueError):
            format_entry(entry)


if __name__ == "__main__":
    unittest.main()
