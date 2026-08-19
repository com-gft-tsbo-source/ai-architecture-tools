import unittest

from lib.text import decode_block, encode_block, escape_signature_text


class TestEscapeSignatureText(unittest.TestCase):
    def test_alnum_untouched(self):
        self.assertEqual(escape_signature_text("Backend123"), "Backend123")

    def test_non_alnum_replaced(self):
        self.assertEqual(escape_signature_text("Configure database connection!"),
                          "Configure_database_connection_")

    def test_empty_string(self):
        self.assertEqual(escape_signature_text(""), "")


class TestBlockEncoding(unittest.TestCase):
    def test_round_trip_multiline(self):
        original = "First line.\nSecond line.\n\nFourth line after blank."
        encoded = encode_block(original)
        self.assertEqual(decode_block(encoded), original)

    def test_encode_prefixes_every_line(self):
        encoded = encode_block("a\nb")
        self.assertEqual(encoded, "> a\n> b")

    def test_encode_blank_line_has_no_trailing_space(self):
        encoded = encode_block("a\n\nb")
        self.assertEqual(encoded, "> a\n>\n> b")

    def test_decode_single_line(self):
        self.assertEqual(decode_block("> hello"), "hello")


if __name__ == "__main__":
    unittest.main()
