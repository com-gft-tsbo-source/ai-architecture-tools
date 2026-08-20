import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lib.adr_lookup import AdrLookupError, check_adr_exists
from lib.adrctl_spec import build_spec as build_adrctl_spec
from lib.store import Store


class TestCheckAdrExists(unittest.TestCase):
    def test_existing_adr_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=build_adrctl_spec(), root=Path(tmp))
            store.add_metagroup_path(["Backend"])
            record = store.add(metagroup_path=["Backend"], name="Use locks")

            check_adr_exists(Path(tmp), record.object_id)  # does not raise

    def test_unknown_adr_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=build_adrctl_spec(), root=Path(tmp))
            store.add_metagroup_path(["Backend"])
            store.add(metagroup_path=["Backend"], name="Use locks")

            with self.assertRaises(AdrLookupError):
                check_adr_exists(Path(tmp), "doesnotexist")

    def test_no_adrctl_data_yet_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AdrLookupError):
                check_adr_exists(Path(tmp), "anything")

            # The check must fail fast via resolve_root, before a Store is
            # ever constructed -- Store.__post_init__ would otherwise create
            # this directory even on a failed, purely-validating call.
            self.assertFalse((Path(tmp) / "adrs").exists())

    def test_lock_held_during_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=build_adrctl_spec(), root=Path(tmp))
            store.add_metagroup_path(["Backend"])
            record = store.add(metagroup_path=["Backend"], name="Use locks")

            lock_path = Path(tmp) / "adrs" / ".lock"
            original_get = Store.get
            lock_present_during_get = []

            def spying_get(self, object_id):
                lock_present_during_get.append(lock_path.exists())
                return original_get(self, object_id)

            with patch.object(Store, "get", spying_get):
                check_adr_exists(Path(tmp), record.object_id)

            self.assertEqual(lock_present_during_get, [True])
            self.assertFalse(lock_path.exists())  # released afterwards

    def test_single_file_mode_adrctl_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=build_adrctl_spec(), root=Path(tmp) / "adrs.md")
            store.add_metagroup_path(["Backend"])
            record = store.add(metagroup_path=["Backend"], name="Use locks")

            check_adr_exists(Path(tmp), record.object_id)


if __name__ == "__main__":
    unittest.main()
