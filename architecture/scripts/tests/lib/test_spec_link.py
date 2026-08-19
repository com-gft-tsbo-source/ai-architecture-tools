import tempfile
import unittest
from pathlib import Path

from lib.spec_link import SpecLinkError, propagate
from lib.spec_store import SpecStore


class TestPropagate(unittest.TestCase):
    def test_updates_adr_field_and_logs_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SpecStore(root=root)
            section = store.add(1, ["Concurrency"])
            before = len(section.history)

            propagate(root, section.object_id, "b1c2d3", message="adr=b1c2d3")

            updated = SpecStore(root=root).resolve_id(section.object_id)
            self.assertEqual(updated.adr, "b1c2d3")
            self.assertEqual(len(updated.history), before + 1)
            self.assertEqual(updated.history[-1].prefix, "M")
            self.assertEqual(updated.history[-1].message, "adr=b1c2d3")

    def test_default_message_when_none_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            section = SpecStore(root=root).add(1, ["Concurrency"])

            propagate(root, section.object_id, "b1c2d3")

            updated = SpecStore(root=root).resolve_id(section.object_id)
            self.assertEqual(updated.history[-1].message, "adr=b1c2d3")

    def test_directory_mode_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "spec").mkdir()
            store = SpecStore(root=root)
            self.assertEqual(store.mode, "directory")
            section = store.add(1, ["Concurrency"])

            propagate(root, section.object_id, "b1c2d3")

            updated = SpecStore(root=root).resolve_id(section.object_id)
            self.assertEqual(updated.adr, "b1c2d3")

    def test_missing_target_raises_spec_link_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            SpecStore(root=root).add(1, ["Concurrency"])

            with self.assertRaises(SpecLinkError):
                propagate(root, "doesnotexist", "b1c2d3")

    def test_error_message_names_the_spec_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            SpecStore(root=root).add(1, ["Concurrency"])

            with self.assertRaises(SpecLinkError) as ctx:
                propagate(root, "doesnotexist", "b1c2d3")
            self.assertIn("doesnotexist", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
