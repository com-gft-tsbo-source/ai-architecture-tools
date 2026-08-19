import tempfile
import unittest
from pathlib import Path

from lib.spec_store import SpecStore, SpecStoreError


def make_store(tmp_dir: str) -> SpecStore:
    return SpecStore(root=Path(tmp_dir) / "design.md")


class TestAdd(unittest.TestCase):
    def test_add_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], description="Locking and friends.")
            self.assertEqual(section.name, "Concurrency")
            self.assertEqual(section.number, 1)
            self.assertEqual(section.level, 1)
            self.assertEqual(section.status, "draft")
            self.assertEqual(section.description(), "Locking and friends.")

    def test_add_nested_chapter_resolves_parent_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Concurrency"])
            chapter = store.add(2, ["Concurrency", "Locking"])
            self.assertEqual(chapter.level, 2)
            self.assertEqual(chapter.ancestor_levels, ("001-Concurrency",))

    def test_add_nested_chapter_resolves_parent_by_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Concurrency"])
            chapter = store.add(2, ["1", "Locking"])
            self.assertEqual(chapter.ancestor_levels, ("001-Concurrency",))

    def test_add_missing_parent_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.add(2, ["Nonexistent", "Locking"])

    def test_add_wrong_depth_for_level_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.add(2, ["OnlyOneSegment"])

    def test_add_auto_numbers_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            first = store.add(1, ["First"])
            second = store.add(1, ["Second"])
            self.assertEqual(first.number, 1)
            self.assertEqual(second.number, 2)

    def test_add_persists_across_invocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_store(tmp).add(1, ["Concurrency"])
            store2 = make_store(tmp)
            sections = store2.list_all()
            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0].name, "Concurrency")

    def test_object_type_collision_resolved_across_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Part"])
            a = store.add(2, ["Part", "Locking"])
            b = store.add(2, ["Part", "Locking Two"])
            self.assertNotEqual(a.object_type, b.object_type)


class TestResolveAndList(unittest.TestCase):
    def test_resolve_by_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            found = store.resolve_id(section.object_id)
            self.assertEqual(found.name, "Concurrency")

    def test_resolve_by_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            found = store.resolve_id(section.signature)
            self.assertEqual(found.object_id, section.object_id)

    def test_resolve_by_path_selector(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Concurrency"])
            found = store.resolve_id("/1")
            self.assertEqual(found.name, "Concurrency")

    def test_resolve_unknown_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.resolve_id("nope")


class TestStatusAndAdr(unittest.TestCase):
    def test_draft_to_stable_requires_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            with self.assertRaises(SpecStoreError):
                store.set_status(section.object_id, "stable")

    def test_draft_to_stable_with_inline_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            updated = store.set_status(section.object_id, "stable", adr="b1c2d3")
            self.assertEqual(updated.status, "stable")
            self.assertEqual(updated.adr, "b1c2d3")

    def test_draft_to_stable_with_preset_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.set_adr(section.object_id, "b1c2d3")
            updated = store.set_status(section.object_id, "stable")
            self.assertEqual(updated.status, "stable")

    def test_stable_to_draft_requires_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.set_status(section.object_id, "stable", adr="b1c2d3")
            with self.assertRaises(SpecStoreError):
                store.set_status(section.object_id, "draft")
            updated = store.set_status(section.object_id, "draft", force=True)
            self.assertEqual(updated.status, "draft")

    def test_set_adr_not_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            before = len(section.history)
            store.set_adr(section.object_id, "b1c2d3")
            after = store.resolve_id(section.object_id)
            self.assertEqual(len(after.history), before)

    def test_status_change_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.set_status(section.object_id, "stable", adr="b1c2d3")
            after = store.resolve_id(section.object_id)
            self.assertEqual(len(after.history), 2)  # Add + status change
            self.assertEqual(after.history[-1].old_status, "draft")
            self.assertEqual(after.history[-1].new_status, "stable")


class TestSetDescription(unittest.TestCase):
    def test_draft_content_change_untracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], description="v1")
            store.set_description(section.object_id, "v2")
            after = store.resolve_id(section.object_id)
            self.assertEqual(after.description(), "v2")
            self.assertEqual(len(after.history), 1)  # only Add

    def test_stable_without_adr_content_change_rejected(self):
        # A section can reach 'stable' directly at creation time via
        # --set-status (design.md: an initial-value choice, not a
        # transition, so it never needs --force / an adr) -- but its `adr`
        # field is then still unset, so a content change must still supply
        # one.
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], description="v1", initial_status="stable")
            self.assertIsNone(section.adr)
            with self.assertRaises(SpecStoreError):
                store.set_description(section.object_id, "v2")
            updated = store.set_description(section.object_id, "v2", adr="c4d5e6")
            self.assertEqual(updated.description(), "v2")
            self.assertEqual(updated.adr, "c4d5e6")

    def test_stable_content_change_reuses_already_set_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], description="v1")
            store.set_status(section.object_id, "stable", adr="b1c2d3")
            updated = store.set_description(section.object_id, "v2")
            self.assertEqual(updated.description(), "v2")
            self.assertEqual(updated.adr, "b1c2d3")


class TestRename(unittest.TestCase):
    def test_rename_updates_name_and_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            renamed = store.rename(section.object_id, "Concurrency & Locking")
            self.assertEqual(renamed.name, "Concurrency & Locking")
            self.assertIn("Concurrency___Locking", renamed.signature)

    def test_rename_cascades_to_descendants(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Concurrency"])
            store.add(2, ["Concurrency", "Locking"])
            store.add(3, ["Concurrency", "Locking", "Timeout"])
            part = store.list_all()[0]
            store.rename(part.object_id, "Concurrency Renamed")

            sections = store.list_all()
            by_name = {s.name: s for s in sections}
            self.assertEqual(by_name["Locking"].ancestor_levels, ("001-Concurrency Renamed",))
            self.assertEqual(
                by_name["Timeout"].ancestor_levels,
                ("001-Concurrency Renamed", "001-Locking"),
            )

    def test_rename_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.rename(section.object_id, "Renamed")
            after = store.resolve_id(section.object_id)
            self.assertEqual(len(after.history), 2)


class TestReorder(unittest.TestCase):
    def test_reorder_moves_sibling_and_number_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            a = store.add(1, ["A"])
            b = store.add(1, ["B"])
            c = store.add(1, ["C"])

            store.reorder(c.object_id, insert_after=0)  # move C before A

            sections = store.list_all()
            self.assertEqual([s.name for s in sections], ["C", "A", "B"])
            self.assertEqual([s.number for s in sections], [1, 2, 3])

    def test_reorder_carries_subtree_along(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            store.add(2, ["A", "A1"])
            b = store.add(1, ["B"])

            store.reorder(b.object_id, insert_after=0)  # move B before A (and A1)

            sections = store.list_all()
            self.assertEqual([s.name for s in sections], ["B", "A", "A1"])
            by_name = {s.name: s for s in sections}
            self.assertEqual(by_name["A1"].ancestor_levels, ("002-A",))

    def test_reorder_noop_when_already_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            a = store.add(1, ["A"])
            store.add(1, ["B"])
            result = store.reorder(a.object_id, insert_after=0)
            self.assertEqual(result.number, 1)
            sections = store.list_all()
            self.assertEqual([s.name for s in sections], ["A", "B"])


class TestRenderAndHistory(unittest.TestCase):
    def test_render_strips_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Concurrency"], description="Locking and friends.")
            rendered = store.render_plain()
            self.assertNotIn("<!--", rendered)
            self.assertIn("## Concurrency", rendered)
            self.assertIn("Locking and friends.", rendered)

    def test_combined_history_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            a = store.add(1, ["A"])
            store.add(1, ["B"])
            store.set_status(a.object_id, "stable", adr="b1c2d3")
            entries = store.combined_history()
            self.assertEqual(entries[0][1].prefix, "M")
            self.assertGreaterEqual(len(entries), 3)


class TestMergedModeReadOnly(unittest.TestCase):
    def test_write_operations_rejected_in_merged_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            path_a = Path(tmp) / "a.md"
            path_b = Path(tmp) / "b.md"
            SpecStore(root=path_a).add(1, ["FromA"])
            SpecStore(root=path_b).add(1, ["FromB"])

            merged = SpecStore(root=[path_a, path_b])
            self.assertEqual(len(merged.list_all()), 2)
            with self.assertRaises(SpecStoreError):
                merged.add(1, ["New"])


class TestDirectoryMode(unittest.TestCase):
    def test_root_directory_detected_and_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"  # does not exist yet, no file suffix
            store = SpecStore(root=root)
            self.assertEqual(store.mode, "directory")
            self.assertTrue(root.is_dir())

    def test_add_creates_nested_directories_with_content_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            store = SpecStore(root=root)
            part = store.add(1, ["Concurrency"], description="Intro.")
            chapter = store.add(2, ["Concurrency", "Locking"], description="A lock.")

            part_dir = root / f"001-{part.object_type}-{part.object_id}-concurrency"
            chapter_dir = part_dir / f"001-{chapter.object_type}-{chapter.object_id}-locking"
            self.assertTrue((part_dir / "_content.md").is_file())
            self.assertTrue((chapter_dir / "_content.md").is_file())

    def test_persists_and_reads_back_across_invocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            SpecStore(root=root).add(1, ["Concurrency"], description="Intro.")
            store2 = SpecStore(root=root)
            sections = store2.list_all()
            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0].name, "Concurrency")
            self.assertEqual(sections[0].description(), "Intro.")

    def test_hand_authored_preamble_file_is_read_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            root.mkdir()
            (root / "_preamble.md").write_text("# Design Doc\n\nSome intro text.\n", encoding="utf-8")

            store = SpecStore(root=root)
            self.assertEqual(store.list_all(), [])
            # A write (e.g. `add`) must not drop the hand-authored preamble.
            store.add(1, ["Concurrency"])
            preamble_text = (root / "_preamble.md").read_text(encoding="utf-8")
            self.assertEqual(preamble_text, "# Design Doc\n\nSome intro text.\n")

    def test_nested_add_resolve_status_rename_reorder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            store = SpecStore(root=root)
            store.add(1, ["A"])
            store.add(2, ["A", "A1"])
            b = store.add(1, ["B"])
            c = store.add(1, ["C"])

            store.reorder(c.object_id, insert_after=0)
            sections = store.list_all()
            self.assertEqual([s.name for s in sections], ["C", "A", "A1", "B"])

            a = next(s for s in sections if s.name == "A")
            store.rename(a.object_id, "A Renamed")
            sections = store.list_all()
            by_name = {s.name: s for s in sections}
            self.assertEqual(by_name["A1"].ancestor_levels, ("002-A Renamed",))

            with self.assertRaises(SpecStoreError):
                store.set_status(b.object_id, "stable")
            updated = store.set_status(b.object_id, "stable", adr="b1c2d3")
            self.assertEqual(updated.status, "stable")

    def test_render_and_combined_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            store = SpecStore(root=root)
            store.add(1, ["Concurrency"], description="Locking and friends.")
            rendered = store.render_plain()
            self.assertNotIn("<!--", rendered)
            self.assertIn("## Concurrency", rendered)

            entries = store.combined_history()
            self.assertEqual(len(entries), 1)

    def test_rewritten_tree_drops_stale_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            store = SpecStore(root=root)
            first = store.add(1, ["First"])
            old_dir = root / f"001-{first.object_type}-{first.object_id}-first"
            self.assertTrue(old_dir.is_dir())

            store.rename(first.object_id, "Renamed")
            self.assertFalse(old_dir.is_dir())
            new_dir = root / f"001-{first.object_type}-{first.object_id}-renamed"
            self.assertTrue(new_dir.is_dir())

    def test_duplicate_id_across_content_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "design"
            store = SpecStore(root=root)
            store.add(1, ["A"])
            second_dir = root / "002-XX____-dupe1d-b"
            second_dir.mkdir()
            (second_dir / "_content.md").write_text(
                "## B\n\n<!-- specctl id=dupe1d type=XX____ nr=002 status=draft -->\n", encoding="utf-8"
            )
            # Reuse the same ID as the first section to trigger the check.
            first = store.list_all()[0]
            (second_dir / "_content.md").write_text(
                f"## B\n\n<!-- specctl id={first.object_id} type=XX____ nr=002 status=draft -->\n",
                encoding="utf-8",
            )
            with self.assertRaises(SpecStoreError):
                store.list_all()

    def test_merged_mode_across_file_and_directory_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_root = Path(tmp) / "a.md"
            dir_root = Path(tmp) / "b"
            SpecStore(root=file_root).add(1, ["FromFile"])
            SpecStore(root=dir_root).add(1, ["FromDir"])

            merged = SpecStore(root=[file_root, dir_root])
            names = {s.name for s in merged.list_all()}
            self.assertEqual(names, {"FromFile", "FromDir"})
            with self.assertRaises(SpecStoreError):
                merged.add(1, ["New"])


if __name__ == "__main__":
    unittest.main()
