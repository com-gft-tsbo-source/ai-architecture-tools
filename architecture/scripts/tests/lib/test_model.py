import unittest

from lib.model import (
    InvalidObjectIdError,
    MetainfoEntry,
    ObjectRecord,
    derive_id,
    validate_free_form_id,
)


class TestDeriveId(unittest.TestCase):
    def test_is_deterministic(self):
        self.assertEqual(derive_id("some content"), derive_id("some content"))

    def test_is_six_hex_chars(self):
        object_id = derive_id("some content")
        self.assertEqual(len(object_id), 6)
        int(object_id, 16)  # raises if not valid hex

    def test_different_content_differs(self):
        self.assertNotEqual(derive_id("a"), derive_id("b"))


class TestValidateFreeFormId(unittest.TestCase):
    def test_accepts_plain_string(self):
        self.assertEqual(validate_free_form_id("my-id"), "my-id")

    def test_rejects_slash(self):
        with self.assertRaises(InvalidObjectIdError):
            validate_free_form_id("has/slash")

    def test_rejects_empty(self):
        with self.assertRaises(InvalidObjectIdError):
            validate_free_form_id("")


class TestObjectRecordSignature(unittest.TestCase):
    def _make(self, **overrides):
        defaults = dict(
            object_id="a3f9c2",
            object_type="baclok",
            number=5,
            name="Configure database connection",
            status="active",
            metagroup_levels=("backend", "logik"),
        )
        defaults.update(overrides)
        return ObjectRecord(**defaults)

    def test_signature_format(self):
        record = self._make()
        self.assertEqual(
            record.signature,
            "baclok-005-a3f9c2-Configure_database_connection",
        )

    def test_signature_includes_class_suffix(self):
        record = self._make(class_suffix="urgent")
        self.assertTrue(record.signature.endswith("-urgent"))

    def test_signature_escapes_name(self):
        record = self._make(name="Fix bug #123!")
        self.assertIn("Fix_bug__123_", record.signature)

    def test_metainfo_value_lookup(self):
        record = self._make(metainfo=[MetainfoEntry(type="weight", value="high")])
        self.assertEqual(record.metainfo_value("weight"), "high")
        self.assertIsNone(record.metainfo_value("missing"))


if __name__ == "__main__":
    unittest.main()
