import unittest
from collections import namedtuple

from lib import idmatch

Item = namedtuple("Item", "oid sig path nr")

ITEMS = [
    Item("45d2c8", "1-001-45d2c8-Foo_bar", "Setup", 1),
    Item("dd53ef", "1-002-dd53ef-Zweite", "Setup", 2),
    Item("free/id", "2-001-abc123-Other", "Misc", 1),
]


def resolve(token):
    return idmatch.resolve(
        ITEMS, token, kind="object",
        object_id=lambda i: i.oid, signature=lambda i: i.sig,
        by_path=lambda items, path, nr: next((i for i in items if i.path == path and i.nr == nr), None),
    )


class ResolveTest(unittest.TestCase):
    def test_exact_id_signature_and_path(self):
        self.assertEqual(resolve("45d2c8").nr, 1)
        self.assertEqual(resolve("1-002-dd53ef-Zweite").oid, "dd53ef")
        self.assertEqual(resolve("Setup/2").oid, "dd53ef")

    def test_exact_id_with_slash_beats_path_selector(self):
        self.assertEqual(resolve("free/id").sig, "2-001-abc123-Other")

    def test_list_line_with_status_prefix(self):
        self.assertEqual(resolve("  1-001-45d2c8-Foo_bar").oid, "45d2c8")
        self.assertEqual(resolve("~ 1-001-45d2c8-Foo_bar").oid, "45d2c8")
        self.assertEqual(resolve("proposed 1-002-dd53ef-Zweite").oid, "dd53ef")

    def test_fragment_is_case_insensitive(self):
        self.assertEqual(resolve("FOO").oid, "45d2c8")
        self.assertEqual(resolve("53ef").oid, "dd53ef")

    def test_ambiguous_fragment_lists_candidates(self):
        with self.assertRaises(idmatch.IdMatchError) as ctx:
            resolve("1-00")
        message = str(ctx.exception)
        self.assertIn("ambiguous", message)
        self.assertIn("1-001-45d2c8-Foo_bar", message)
        self.assertIn("1-002-dd53ef-Zweite", message)

    def test_no_match_and_empty(self):
        with self.assertRaises(idmatch.IdMatchError):
            resolve("nothing")
        with self.assertRaises(idmatch.IdMatchError):
            resolve("   ")

    def test_unknown_path_falls_through_to_error(self):
        with self.assertRaises(idmatch.IdMatchError):
            resolve("Setup/9")


if __name__ == "__main__":
    unittest.main()
