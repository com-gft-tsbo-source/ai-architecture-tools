import tempfile
import unittest
from pathlib import Path

from lib.atomicio import atomic_write_text


class TestAtomicWriteText(unittest.TestCase):
    def test_writes_content_and_leaves_no_tmp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.md"
            atomic_write_text(target, "hello")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello")
            self.assertFalse((Path(tmp) / "file.md.tmp").exists())

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.md"
            atomic_write_text(target, "first")
            atomic_write_text(target, "second")
            self.assertEqual(target.read_text(encoding="utf-8"), "second")


if __name__ == "__main__":
    unittest.main()
