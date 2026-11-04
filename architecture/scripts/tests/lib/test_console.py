import io
import sys
import unittest
from unittest.mock import patch

from lib.console import use_utf8_streams


class TestUseUtf8Streams(unittest.TestCase):
    def test_reconfigures_text_streams_to_utf8(self):
        out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        err = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            use_utf8_streams()
            print("→", end="")
            sys.stdout.flush()
        self.assertEqual((out.encoding, err.encoding), ("utf-8", "utf-8"))
        self.assertEqual(out.buffer.getvalue(), "→".encode("utf-8"))

    def test_streams_without_reconfigure_are_left_alone(self):
        out = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", io.StringIO()):
            use_utf8_streams()  # does not raise
            self.assertIs(sys.stdout, out)


if __name__ == "__main__":
    unittest.main()
