import tempfile
import unittest
from pathlib import Path

from lib import index
from lib.store import Store, StoreError, detect_mode, object_file_name
from lib.toolspec import MetagroupLevelSpec, MetainfoSpec, StatusSpec, ToolSpec


def taskctl_spec(transition_validator=None) -> ToolSpec:
    return ToolSpec(
        name="taskctl",
        metagroup_levels=(MetagroupLevelSpec(type="Phase"),),
        metainfo=(MetainfoSpec(type="review"),),
        status=StatusSpec(codes=(" ", "~", "X"), initial=" ", transition_validator=transition_validator),
        user_content_blocks=("Description",),
    )


class TestDetectMode(unittest.TestCase):
    def test_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tasks.md"
            path.write_text("x", encoding="utf-8")
            self.assertEqual(detect_mode(path), "file")

    def test_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_mode(Path(tmp)), "directory")

    def test_nonexistent_with_suffix_is_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_mode(Path(tmp) / "tasks.md"), "file")

    def test_nonexistent_without_suffix_is_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(detect_mode(Path(tmp) / "tasks"), "directory")


class TestAddAndGet(unittest.TestCase):
    def _new_store(self, tmp) -> Store:
        store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
        store.add_metagroup_path(["001-Setup"])
        return store

    def test_add_requires_existing_metagroup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            with self.assertRaises(Exception):
                store.add(metagroup_path=["001-Setup"], name="First task")

    def test_add_then_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            created = store.add(metagroup_path=["001-Setup"], name="First task", description="Do it.")
            fetched = store.get(created.object_id)
            self.assertEqual(fetched.name, "First task")
            self.assertEqual(fetched.content["Description"], "Do it.")
            self.assertEqual(fetched.status, " ")
            self.assertEqual(fetched.number, 1)

    def test_numbers_increment_within_same_metagroup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            first = store.add(metagroup_path=["001-Setup"], name="First")
            second = store.add(metagroup_path=["001-Setup"], name="Second")
            self.assertEqual(first.number, 1)
            self.assertEqual(second.number, 2)

    def test_numbers_scoped_per_metagroup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            store.add_metagroup_path(["002-Implementation"])
            first = store.add(metagroup_path=["001-Setup"], name="First")
            other = store.add(metagroup_path=["002-Implementation"], name="Other")
            self.assertEqual(first.number, 1)
            self.assertEqual(other.number, 1)

    def test_explicit_object_id_used_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            record = store.add(metagroup_path=["001-Setup"], name="First", object_id="my-id")
            self.assertEqual(record.object_id, "my-id")

    def test_explicit_object_id_with_slash_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            with self.assertRaises(Exception):
                store.add(metagroup_path=["001-Setup"], name="First", object_id="has/slash")

    def test_index_json_written_on_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            record = store.add(metagroup_path=["001-Setup"], name="First")
            directory = store.root / "001-Setup"
            entries = index.read_index_json(directory)
            self.assertIn(record.object_id, entries)
            self.assertEqual(entries[record.object_id].name, "First")

    def test_history_records_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            record = store.add(metagroup_path=["001-Setup"], name="First")
            self.assertEqual(len(record.history), 1)
            self.assertEqual(record.history[0].message, "Object created")
            self.assertFalse(record.history[0].has_transition)


class TestListAndResolveId(unittest.TestCase):
    def _store_with_objects(self, tmp):
        store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
        store.add_metagroup_path(["001-Setup"])
        record = store.add(metagroup_path=["001-Setup"], name="First task")
        return store, record

    def test_list_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, record = self._store_with_objects(tmp)
            all_records = store.list_all()
            self.assertEqual(len(all_records), 1)
            self.assertEqual(all_records[0].object_id, record.object_id)

    def test_resolve_by_raw_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, record = self._store_with_objects(tmp)
            resolved = store.resolve_id(record.object_id)
            self.assertEqual(resolved.object_id, record.object_id)

    def test_resolve_by_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, record = self._store_with_objects(tmp)
            resolved = store.resolve_id(record.signature)
            self.assertEqual(resolved.object_id, record.object_id)

    def test_resolve_by_metagroup_path_and_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, record = self._store_with_objects(tmp)
            resolved = store.resolve_id("001-Setup/1")
            self.assertEqual(resolved.object_id, record.object_id)

    def test_resolve_unknown_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _record = self._store_with_objects(tmp)
            with self.assertRaises(StoreError):
                store.resolve_id("does-not-exist")


class TestSetStatusAndAnnotate(unittest.TestCase):
    def test_set_status_records_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            record = store.add(metagroup_path=["001-Setup"], name="First")
            updated = store.set_status(record.object_id, "~", message="Starting work")
            self.assertEqual(updated.status, "~")
            self.assertEqual(updated.history[-1].old_status, " ")
            self.assertEqual(updated.history[-1].new_status, "~")
            self.assertEqual(updated.history[-1].message, "Starting work")
            # persisted
            reloaded = store.get(record.object_id)
            self.assertEqual(reloaded.status, "~")

    def test_set_status_invalid_status_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            record = store.add(metagroup_path=["001-Setup"], name="First")
            with self.assertRaises(StoreError):
                store.set_status(record.object_id, "NOPE")

    def test_set_status_calls_transition_validator(self):
        calls = []

        def validator(record, target, *, message, force):
            calls.append((record.status, target, message, force))
            if target == "X" and record.status == " " and not force:
                raise ValueError("cannot skip straight to done")

        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(validator), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            record = store.add(metagroup_path=["001-Setup"], name="First")
            with self.assertRaises(ValueError):
                store.set_status(record.object_id, "X")
            self.assertEqual(len(calls), 1)

    def test_annotate_appends_t_entry_with_unchanged_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            record = store.add(metagroup_path=["001-Setup"], name="First")
            updated = store.annotate(record.object_id, "Made progress")
            last = updated.history[-1]
            self.assertEqual(last.prefix, "T")
            self.assertEqual(last.old_status, " ")
            self.assertEqual(last.new_status, " ")
            self.assertEqual(last.message, "Made progress")


class TestSetMetainfo(unittest.TestCase):
    def test_sets_and_overwrites_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            record = store.add(metagroup_path=["001-Setup"], name="First")
            updated = store.set_metainfo(record.object_id, "review", "user")
            self.assertEqual(updated.metainfo_value("review"), "user")
            updated2 = store.set_metainfo(record.object_id, "review", "subagent")
            self.assertEqual(updated2.metainfo_value("review"), "subagent")
            self.assertEqual(len(updated2.metainfo), 1)


class TestSingleFileMode(unittest.TestCase):
    def _new_store(self, tmp) -> Store:
        store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks.md")
        store.add_metagroup_path(["001-Setup"])
        return store

    def test_mode_is_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            self.assertEqual(store.mode, "file")
            self.assertTrue(store.root.exists())  # metagroup creation already wrote the file

    def test_add_then_get_and_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            created = store.add(metagroup_path=["001-Setup"], name="First task", description="Do it.")
            self.assertEqual(store.get(created.object_id).name, "First task")
            self.assertEqual(len(store.list_all()), 1)

    def test_numbers_increment_within_metagroup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            first = store.add(metagroup_path=["001-Setup"], name="First")
            second = store.add(metagroup_path=["001-Setup"], name="Second")
            self.assertEqual((first.number, second.number), (1, 2))

    def test_add_requires_existing_metagroup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks.md")
            with self.assertRaises(Exception):
                store.add(metagroup_path=["001-Setup"], name="First")

    def test_set_status_persists_across_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            record = store.add(metagroup_path=["001-Setup"], name="First")
            store.set_status(record.object_id, "~", message="go")
            self.assertEqual(store.get(record.object_id).status, "~")

    def test_resolve_id_all_three_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            record = store.add(metagroup_path=["001-Setup"], name="First")
            self.assertEqual(store.resolve_id(record.object_id).object_id, record.object_id)
            self.assertEqual(store.resolve_id(record.signature).object_id, record.object_id)
            self.assertEqual(store.resolve_id("001-Setup/1").object_id, record.object_id)

    def test_reorder_within_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            first = store.add(metagroup_path=["001-Setup"], name="First")
            second = store.add(metagroup_path=["001-Setup"], name="Second")
            third = store.add(metagroup_path=["001-Setup"], name="Third")
            updated = store.reorder(third.object_id, insert_after=0)
            self.assertEqual(updated.number, 1)
            self.assertEqual(store.get(first.object_id).number, 2)
            self.assertEqual(store.get(second.object_id).number, 3)

    def test_file_content_is_human_readable_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._new_store(tmp)
            store.add(metagroup_path=["001-Setup"], name="First task")
            text = store.root.read_text(encoding="utf-8")
            self.assertIn("## Metagroups", text)
            self.assertIn("## First task", text)
            self.assertIn("- Phase: 001-Setup", text)


class TestAutoNumberingAndFlexibleReference(unittest.TestCase):
    def test_add_metagroup_path_auto_numbers_leaf(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["Setup"])
            store.add_metagroup_path(["Implementation"])
            paths = sorted(p[0] for p in store.metagroup_paths())
            self.assertEqual(paths, ["001-Setup", "002-Implementation"])

    def test_add_metagroup_path_explicit_number_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["005-Setup"])
            paths = [p[0] for p in store.metagroup_paths()]
            self.assertEqual(paths, ["005-Setup"])

    def test_add_resolves_flexible_phase_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["Setup"])
            by_name = store.add(metagroup_path=["Setup"], name="ByName")
            by_number = store.add(metagroup_path=["1"], name="ByNumber")
            by_full = store.add(metagroup_path=["001-Setup"], name="ByFull")
            self.assertEqual(by_name.metagroup_levels, ("001-Setup",))
            self.assertEqual(by_number.metagroup_levels, ("001-Setup",))
            self.assertEqual(by_full.metagroup_levels, ("001-Setup",))

    def test_ambiguous_name_reference_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            store.add_metagroup_path(["002-Setup"])
            with self.assertRaises(Exception):
                store.add(metagroup_path=["Setup"], name="Ambiguous")

    def test_single_file_mode_auto_numbering_and_flexible_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks.md")
            store.add_metagroup_path(["Setup"])
            record = store.add(metagroup_path=["1"], name="First")
            self.assertEqual(record.metagroup_levels, ("001-Setup",))


class TestMergedMode(unittest.TestCase):
    def test_list_all_merges_across_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_a = Path(tmp) / "a"
            root_b = Path(tmp) / "b"
            store_a = Store(spec=taskctl_spec(), root=root_a)
            store_a.add_metagroup_path(["Setup"])
            store_a.add(metagroup_path=["Setup"], name="FromA")
            store_b = Store(spec=taskctl_spec(), root=root_b)
            store_b.add_metagroup_path(["Setup"])
            store_b.add(metagroup_path=["Setup"], name="FromB")

            merged = Store(spec=taskctl_spec(), root=[root_a, root_b])
            self.assertEqual(merged.mode, "merged")
            names = {r.name for r in merged.list_all()}
            self.assertEqual(names, {"FromA", "FromB"})

    def test_get_finds_object_in_either_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_a = Path(tmp) / "a"
            root_b = Path(tmp) / "b"
            store_a = Store(spec=taskctl_spec(), root=root_a)
            store_a.add_metagroup_path(["Setup"])
            created = store_a.add(metagroup_path=["Setup"], name="FromA")
            store_b = Store(spec=taskctl_spec(), root=root_b)
            store_b.add_metagroup_path(["Setup"])

            merged = Store(spec=taskctl_spec(), root=[root_a, root_b])
            self.assertEqual(merged.get(created.object_id).name, "FromA")

    def test_write_operations_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root_a = Path(tmp) / "a"
            root_b = Path(tmp) / "b"
            Store(spec=taskctl_spec(), root=root_a).add_metagroup_path(["Setup"])
            Store(spec=taskctl_spec(), root=root_b).add_metagroup_path(["Setup"])

            merged = Store(spec=taskctl_spec(), root=[root_a, root_b])
            with self.assertRaises(StoreError):
                merged.add(metagroup_path=["Setup"], name="X")
            with self.assertRaises(StoreError):
                merged.add_metagroup_path(["Other"])
            with self.assertRaises(StoreError):
                merged.set_status("whatever", "~")

    def test_single_root_list_is_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=[Path(tmp) / "tasks"])
            self.assertNotEqual(store.mode, "merged")


class TestReorder(unittest.TestCase):
    def _store_with_three(self, tmp):
        store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
        store.add_metagroup_path(["001-Setup"])
        first = store.add(metagroup_path=["001-Setup"], name="First")
        second = store.add(metagroup_path=["001-Setup"], name="Second")
        third = store.add(metagroup_path=["001-Setup"], name="Third")
        return store, first, second, third

    def test_move_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, first, second, third = self._store_with_three(tmp)
            updated = store.reorder(first.object_id, insert_after=third.number)
            self.assertEqual(updated.number, 4)
            self.assertEqual(store.get(second.object_id).number, 2)
            self.assertEqual(store.get(third.object_id).number, 3)

    def test_move_to_beginning_cascades_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, first, second, third = self._store_with_three(tmp)
            updated = store.reorder(third.object_id, insert_after=0)
            self.assertEqual(updated.number, 1)
            self.assertEqual(store.get(first.object_id).number, 2)
            self.assertEqual(store.get(second.object_id).number, 3)

    def test_noop_reorder_to_same_position_after_last(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, first, second, third = self._store_with_three(tmp)
            updated = store.reorder(third.object_id, insert_after=second.number)
            self.assertEqual(updated.number, third.number)

    def test_file_renamed_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, first, second, third = self._store_with_three(tmp)
            store.reorder(third.object_id, insert_after=0)
            directory = store.root / "001-Setup"
            names = sorted(p.name for p in directory.glob("*.md"))
            self.assertTrue(any(n.startswith("001-") and "third" in n for n in names))

    def test_index_rebuilt_after_reorder(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, first, second, third = self._store_with_three(tmp)
            store.reorder(third.object_id, insert_after=0)
            directory = store.root / "001-Setup"
            entries = index.read_index_json(directory)
            self.assertEqual(entries[third.object_id].nr, 1)
            self.assertEqual(entries[first.object_id].nr, 2)


class TestReindex(unittest.TestCase):
    def test_reindex_rebuilds_index_json_without_touching_index_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            record = store.add(metagroup_path=["001-Setup"], name="First")
            directory = store.root / "001-Setup"
            abbrev_before = index.read_abbrev(directory)

            (directory / index.INDEX_JSON_NAME).unlink()
            reports = store.reindex()

            rebuilt_dirs = [r.directory for r in reports]
            self.assertIn(directory, rebuilt_dirs)
            self.assertTrue(all(r.is_clean for r in reports))
            self.assertEqual(index.read_abbrev(directory), abbrev_before)
            entries = index.read_index_json(directory)
            self.assertIn(record.object_id, entries)

    def test_reindex_removes_orphaned_tmp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            store.add(metagroup_path=["001-Setup"], name="First")
            directory = store.root / "001-Setup"
            orphan = directory / "004-1-deadbe-half-written.md.tmp"
            orphan.write_text("incomplete", encoding="utf-8")

            reports = store.reindex()

            self.assertFalse(orphan.exists())
            report = next(r for r in reports if r.directory == directory)
            self.assertIn(orphan.name, report.removed_tmp_files)
            self.assertFalse(report.is_clean)

    def test_reindex_detects_duplicate_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks")
            store.add_metagroup_path(["001-Setup"])
            first = store.add(metagroup_path=["001-Setup"], name="First")
            directory = store.root / "001-Setup"
            # Simulate an interrupted reorder cascade: a second object left
            # behind claiming the same number as `first`.
            original_path = directory / object_file_name(first)
            duplicate_path = directory / "001-Setup_-dupdup-duplicate.md"
            duplicate_path.write_text(
                original_path.read_text(encoding="utf-8").replace(first.object_id, "dupdup"),
                encoding="utf-8",
            )

            reports = store.reindex()

            report = next(r for r in reports if r.directory == directory)
            self.assertFalse(report.is_clean)
            self.assertIn(1, report.duplicate_numbers)
            self.assertEqual(set(report.duplicate_numbers[1]), {first.object_id, "dupdup"})

    def test_reindex_on_single_file_mode_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(spec=taskctl_spec(), root=Path(tmp) / "tasks.md")
            store.add_metagroup_path(["001-Setup"])
            store.add(metagroup_path=["001-Setup"], name="First")
            self.assertEqual(store.reindex(), [])


if __name__ == "__main__":
    unittest.main()
