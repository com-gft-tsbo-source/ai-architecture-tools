import tempfile
import unittest
from pathlib import Path

from lib.index import (
    INDEX_JSON_NAME,
    INDEX_MD_NAME,
    IndexEntry,
    IndexError_,
    read_abbrev,
    read_index_json,
    write_abbrev,
    write_index_json,
)
from lib.model import MetainfoEntry, ObjectRecord
from lib.index import index_entry_for, rebuild_index_json


class TestAbbrevWriteOnce(unittest.TestCase):
    def test_write_then_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "backend"
            write_abbrev(directory, "bac")
            self.assertEqual(read_abbrev(directory), "bac")
            self.assertTrue((directory / INDEX_MD_NAME).exists())

    def test_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(read_abbrev(Path(tmp)))

    def test_rewriting_same_value_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_abbrev(directory, "bac")
            write_abbrev(directory, "bac")  # idempotent, must not raise
            self.assertEqual(read_abbrev(directory), "bac")

    def test_rewriting_different_value_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_abbrev(directory, "bac")
            with self.assertRaises(IndexError_):
                write_abbrev(directory, "xyz")
            self.assertEqual(read_abbrev(directory), "bac")


class TestIndexJson(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            entries = {
                "a3f9c2": IndexEntry(
                    object_id="a3f9c2", nr=5, type="baclok", name="Configure db",
                    status="active", file="005-baclok-a3f9c2-configure-db.md",
                    meta={"weight": "high", "tool": "eslint"},
                )
            }
            write_index_json(directory, entries)
            self.assertTrue((directory / INDEX_JSON_NAME).exists())
            loaded = read_index_json(directory)
            self.assertEqual(loaded, entries)

    def test_missing_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_index_json(Path(tmp)), {})


class TestRebuildIndexJson(unittest.TestCase):
    def test_rebuild_from_records_never_touches_index_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            write_abbrev(directory, "bac")
            record = ObjectRecord(
                object_id="a3f9c2", object_type="baclok", number=5,
                name="Configure db", status="active",
                metagroup_levels=("Python", "001-backend"),
                metainfo=[MetainfoEntry(type="weight", value="high")],
            )
            rebuild_index_json(directory, [(record, "005-baclok-a3f9c2-configure-db.md")])
            self.assertEqual(read_abbrev(directory), "bac")
            loaded = read_index_json(directory)
            self.assertEqual(loaded["a3f9c2"].name, "Configure db")
            self.assertEqual(loaded["a3f9c2"].meta, {"weight": "high"})


if __name__ == "__main__":
    unittest.main()
