import tempfile
import unittest
from pathlib import Path

from lib.adrctl_spec import build_spec as build_adrctl_spec
from lib.spec_store import SpecStore, SpecStoreError
from lib.store import Store as GenericStore


def make_store(tmp_dir: str, title: str = "Design Doc") -> SpecStore:
    store = SpecStore(root=Path(tmp_dir) / "design.md")
    store.init(title)
    return store


def reopen_store(tmp_dir: str) -> SpecStore:
    """Reopen an already-initialized store from a previous invocation --
    unlike make_store, does not call init() again (init rejects running
    twice on the same document)."""
    return SpecStore(root=Path(tmp_dir) / "design.md")


def make_adr(tmp_dir: str, adr_id: str = "b1c2d3") -> str:
    """Create a real ADR sharing tmp_dir's root, for tests exercising
    specctl's ADR-existence validation (lib/adr_lookup.py) -- a bare string
    no longer satisfies `set_status`/`set_description`/`set_open_questions`."""
    store = GenericStore(spec=build_adrctl_spec(), root=Path(tmp_dir))
    store.add_metagroup_path(["Backend"])
    store.add(metagroup_path=["Backend"], name="Test ADR", object_id=adr_id)
    return adr_id


class TestInit(unittest.TestCase):
    def test_init_sets_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            title = store.init("Design Doc")
            self.assertEqual(title, "Design Doc")

    def test_init_sets_preamble(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            store.init("Design Doc", preamble="Some intro text.")
            content = store.root.read_text(encoding="utf-8")
            self.assertEqual(content, "# Design Doc\n\nSome intro text.\n")

    def test_init_without_preamble(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            store.init("Design Doc")
            content = store.root.read_text(encoding="utf-8")
            self.assertEqual(content, "# Design Doc\n")

    def test_init_twice_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.init("Different Title")

    def test_init_empty_title_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.init("   ")

    def test_init_multiline_title_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.init("Line one\nLine two")

    def test_init_preamble_with_heading_line_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.init("Design Doc", preamble="## Looks like a Section")

    def test_init_directory_mode_writes_title_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
            self.assertEqual((root / "_title.md").read_text(encoding="utf-8").strip(), "Design Doc")
            self.assertFalse((root / "_preamble.md").exists())  # optional, empty here

    def test_init_directory_mode_writes_preamble_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc", preamble="Some intro text.")
            self.assertEqual(
                (root / "_preamble.md").read_text(encoding="utf-8"), "Some intro text.\n"
            )


class TestSetTitle(unittest.TestCase):
    def test_changes_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.set_title("New Title")
            content = store.root.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("# New Title\n"))

    def test_before_init_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.set_title("New Title")

    def test_empty_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.set_title("")

    def test_preserves_preamble_and_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp, title="Original")
            section = store.add(1, ["Concurrency"])
            store.set_title("Renamed Doc")
            after = store.resolve_id(section.object_id)
            self.assertEqual(after.name, "Concurrency")


class TestSetPreamble(unittest.TestCase):
    def test_changes_preamble(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.set_preamble("New intro text.")
            content = store.root.read_text(encoding="utf-8")
            self.assertIn("New intro text.", content)

    def test_before_init_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.set_preamble("New intro text.")

    def test_heading_line_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.set_preamble("## Looks like a Section")

    def test_preserves_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.set_preamble("New intro.")
            after = store.resolve_id(section.object_id)
            self.assertEqual(after.name, "Concurrency")


class TestRequiresInitialization(unittest.TestCase):
    """Every mutating operation must reject running on an uninitialized
    store (design-specctl.md, "Store") -- spot-checked across a
    representative subset, not exhaustively every method."""

    def test_add_before_init_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.add(1, ["Concurrency"])

    def test_delete_before_init_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.delete("nope")

    def test_rename_before_init_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.rename("nope", "New Name")

    def test_move_before_init_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            with self.assertRaises(SpecStoreError):
                store.move("nope", 1, [])

    def test_read_operations_tolerate_uninitialized_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SpecStore(root=Path(tmp) / "design.md")
            self.assertEqual(store.list_all(), [])
            self.assertEqual(store.combined_history(), [])
            self.assertEqual(store.render_plain(), "\n")


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

    def test_explicit_object_id_collision_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Concurrency"], object_id="dup-id")
            with self.assertRaises(SpecStoreError):
                store.add(1, ["Other"], object_id="dup-id")

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
            store2 = reopen_store(tmp)
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
            adr_id = make_adr(tmp)
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            updated = store.set_status(section.object_id, "stable", adr=adr_id)
            self.assertEqual(updated.status, "stable")
            self.assertEqual(updated.adr, adr_id)

    def test_draft_to_stable_with_preset_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            adr_id = make_adr(tmp)
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.set_adr(section.object_id, adr_id)
            updated = store.set_status(section.object_id, "stable")
            self.assertEqual(updated.status, "stable")

    def test_stable_to_draft_requires_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            adr_id = make_adr(tmp)
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.set_status(section.object_id, "stable", adr=adr_id)
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
            adr_id = make_adr(tmp)
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.set_status(section.object_id, "stable", adr=adr_id)
            after = store.resolve_id(section.object_id)
            self.assertEqual(len(after.history), 2)  # Add + status change
            self.assertEqual(after.history[-1].old_status, "draft")
            self.assertEqual(after.history[-1].new_status, "stable")


class TestReceiveAdrLink(unittest.TestCase):
    def test_updates_adr_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            updated = store.receive_adr_link(section.object_id, "b1c2d3")
            self.assertEqual(updated.adr, "b1c2d3")

    def test_logs_history_entry_with_default_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            before = len(section.history)
            store.receive_adr_link(section.object_id, "b1c2d3")
            after = store.resolve_id(section.object_id)
            self.assertEqual(len(after.history), before + 1)
            self.assertEqual(after.history[-1].prefix, "M")
            self.assertEqual(after.history[-1].message, "adr=b1c2d3")

    def test_logs_history_entry_with_custom_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            store.receive_adr_link(section.object_id, "b1c2d3", message="adr=b1c2d3")
            after = store.resolve_id(section.object_id)
            self.assertEqual(after.history[-1].message, "adr=b1c2d3")

    def test_unlike_set_adr_receive_adr_link_is_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            manual = len(store.resolve_id(section.object_id).history)
            store.set_adr(section.object_id, "aaaaaa")
            after_manual = len(store.resolve_id(section.object_id).history)
            self.assertEqual(after_manual, manual)
            store.receive_adr_link(section.object_id, "bbbbbb")
            after_automatic = len(store.resolve_id(section.object_id).history)
            self.assertEqual(after_automatic, manual + 1)

    def test_unknown_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.receive_adr_link("nope", "b1c2d3")


class TestAdrValidation(unittest.TestCase):
    def test_set_status_rejects_nonexistent_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            with self.assertRaises(SpecStoreError):
                store.set_status(section.object_id, "stable", adr="doesnotexist")

    def test_set_description_rejects_nonexistent_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], initial_status="stable")
            with self.assertRaises(SpecStoreError):
                store.set_description(section.object_id, "v2", adr="doesnotexist")

    def test_set_open_questions_rejects_nonexistent_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], initial_status="stable")
            with self.assertRaises(SpecStoreError):
                store.set_open_questions(section.object_id, "q?", adr="doesnotexist")

    def test_set_open_questions_succeeds_with_real_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            adr_id = make_adr(tmp)
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"])
            updated = store.set_open_questions(section.object_id, "Thread-safe?", adr=None)
            self.assertEqual(updated.open_questions, "Thread-safe?")  # draft: no adr needed

            store.set_status(section.object_id, "stable", adr=adr_id)
            updated = store.set_open_questions(section.object_id, "Revised?")
            self.assertEqual(updated.open_questions, "Revised?")
            self.assertEqual(updated.adr, adr_id)


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
            adr_id = make_adr(tmp, "c4d5e6")
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], description="v1", initial_status="stable")
            self.assertIsNone(section.adr)
            with self.assertRaises(SpecStoreError):
                store.set_description(section.object_id, "v2")
            updated = store.set_description(section.object_id, "v2", adr=adr_id)
            self.assertEqual(updated.description(), "v2")
            self.assertEqual(updated.adr, adr_id)

    def test_stable_content_change_reuses_already_set_adr(self):
        with tempfile.TemporaryDirectory() as tmp:
            adr_id = make_adr(tmp)
            store = make_store(tmp)
            section = store.add(1, ["Concurrency"], description="v1")
            store.set_status(section.object_id, "stable", adr=adr_id)
            updated = store.set_description(section.object_id, "v2")
            self.assertEqual(updated.description(), "v2")
            self.assertEqual(updated.adr, adr_id)


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


class TestMove(unittest.TestCase):
    def test_move_reparents_and_renumbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            sub = store.add(2, ["A", "Sub"])
            store.add(1, ["B"])
            store.add(2, ["B", "Existing"])

            moved = store.move(sub.object_id, 2, ["B"])
            self.assertEqual(moved.ancestor_levels, ("002-B",))
            self.assertEqual(moved.number, 2)  # after B's existing child

    def test_move_carries_subtree_and_cascades_ancestor_levels(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            sub = store.add(2, ["A", "Sub"])
            store.add(3, ["A", "Sub", "Grand"])
            store.add(1, ["B"])

            store.move(sub.object_id, 2, ["B"])

            sections = store.list_all()
            by_name = {s.name: s for s in sections}
            self.assertEqual(by_name["Sub"].ancestor_levels, ("002-B",))
            self.assertEqual(by_name["Grand"].ancestor_levels, ("002-B", "001-Sub"))
            self.assertEqual([s.name for s in sections], ["A", "B", "Sub", "Grand"])

    def test_move_rederives_object_type_for_whole_subtree(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            sub = store.add(2, ["A", "Sub"])
            grand = store.add(3, ["A", "Sub", "Grand"])
            store.add(1, ["B"])
            sub_type_before, grand_type_before = sub.object_type, grand.object_type

            store.move(sub.object_id, 2, ["B"])

            sections = store.list_all()
            by_name = {s.name: s for s in sections}
            self.assertNotEqual(by_name["Sub"].object_type, sub_type_before)
            self.assertNotEqual(by_name["Grand"].object_type, grand_type_before)
            self.assertTrue(by_name["Sub"].object_type.startswith("B"))
            self.assertTrue(by_name["Grand"].object_type.startswith("B"))

    def test_move_to_root_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            sub = store.add(2, ["A", "Sub"])

            promoted = store.move(sub.object_id, 1, [])
            self.assertEqual(promoted.level, 1)
            self.assertEqual(promoted.ancestor_levels, ())

    def test_move_logs_single_history_entry_on_root_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            sub = store.add(2, ["A", "Sub"])
            grand = store.add(3, ["A", "Sub", "Grand"])
            store.add(1, ["B"])

            store.move(sub.object_id, 2, ["B"])

            after = store.list_all()
            by_name = {s.name: s for s in after}
            self.assertEqual(len(by_name["Sub"].history), 2)  # Add + Move
            self.assertEqual(by_name["Sub"].history[-1].message, "Move to B")
            self.assertEqual(len(by_name["Grand"].history), 1)  # Add only, no Move entry

    def test_move_into_own_subtree_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            a = store.add(1, ["A"])
            store.add(2, ["A", "Sub"])
            with self.assertRaises(SpecStoreError):
                store.move(a.object_id, 3, ["A", "Sub"])

    def test_move_to_current_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            sub = store.add(2, ["A", "Sub"])
            with self.assertRaises(SpecStoreError):
                store.move(sub.object_id, 2, ["A"])

    def test_move_exceeding_depth_cap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            store.add(2, ["A", "A1"])
            store.add(3, ["A", "A1", "A2"])
            a1 = next(s for s in store.list_all() if s.name == "A1")  # depth 2, subtree reaches depth 3
            store.add(1, ["B"])
            store.add(2, ["B", "C"])
            store.add(3, ["B", "C", "D"])
            store.add(4, ["B", "C", "D", "E"])  # depth 4 parent path -> target level 5

            with self.assertRaises(SpecStoreError):
                store.move(a1.object_id, 5, ["B", "C", "D", "E"])  # A1's Grandchild would land at depth 6

    def test_move_wrong_path_length_for_level_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            b = store.add(1, ["B"])
            with self.assertRaises(SpecStoreError):
                store.move(b.object_id, 3, ["OnlyOneSegment"])

    def test_move_missing_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            b = store.add(1, ["B"])
            with self.assertRaises(SpecStoreError):
                store.move(b.object_id, 2, ["Nonexistent"])


class TestDelete(unittest.TestCase):
    def test_deletes_leaf_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            leaf = store.add(2, ["A", "Sub"])
            deleted = store.delete(leaf.object_id)
            self.assertEqual(deleted.object_id, leaf.object_id)
            names = [s.name for s in store.list_all()]
            self.assertEqual(names, ["A"])

    def test_rejects_deleting_section_with_children_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            parent = store.add(1, ["A"])
            store.add(2, ["A", "Sub"])
            with self.assertRaises(SpecStoreError):
                store.delete(parent.object_id)
            # nothing was removed
            self.assertEqual(len(store.list_all()), 2)

    def test_force_delete_cascades_whole_subtree(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            parent = store.add(1, ["A"])
            store.add(2, ["A", "Sub"])
            store.add(3, ["A", "Sub", "Grand"])
            store.add(1, ["B"])

            store.delete(parent.object_id, cascade=True)

            names = [s.name for s in store.list_all()]
            self.assertEqual(names, ["B"])

    def test_unknown_id_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaises(SpecStoreError):
                store.delete("nope")

    def test_leaves_numbering_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            first = store.add(1, ["First"])
            store.add(1, ["Second"])
            store.delete(first.object_id)
            third = store.add(1, ["Third"])
            self.assertEqual(third.number, 3)


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
            adr_id = make_adr(tmp)
            store = make_store(tmp)
            a = store.add(1, ["A"])
            store.add(1, ["B"])
            store.set_status(a.object_id, "stable", adr=adr_id)
            entries = store.combined_history()
            self.assertEqual(entries[0][1].prefix, "M")
            self.assertGreaterEqual(len(entries), 3)


class TestDirectoryMode(unittest.TestCase):
    def test_root_directory_detected_and_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"  # does not exist yet, no file suffix
            store = SpecStore(root=root)
            self.assertEqual(store.mode, "directory")
            self.assertTrue(root.is_dir())

    def test_add_creates_nested_directories_with_content_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
            part = store.add(1, ["Concurrency"], description="Intro.")
            chapter = store.add(2, ["Concurrency", "Locking"], description="A lock.")

            part_dir = root / f"001-{part.object_type}-{part.object_id}-concurrency"
            chapter_dir = part_dir / f"001-{chapter.object_type}-{chapter.object_id}-locking"
            self.assertTrue((part_dir / "_content.md").is_file())
            self.assertTrue((chapter_dir / "_content.md").is_file())

    def test_persists_and_reads_back_across_invocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            first_store = SpecStore(root=root)
            first_store.init("Design Doc")
            first_store.add(1, ["Concurrency"], description="Intro.")
            store2 = SpecStore(root=root)
            sections = store2.list_all()
            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0].name, "Concurrency")
            self.assertEqual(sections[0].description(), "Intro.")

    def test_hand_authored_preamble_file_is_read_and_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            root.mkdir()
            (root / "_title.md").write_text("Design Doc\n", encoding="utf-8")
            (root / "_preamble.md").write_text("Some intro text.\n", encoding="utf-8")

            store = SpecStore(root=root)
            self.assertEqual(store.list_all(), [])
            # A write (e.g. `add`) must not drop the hand-authored preamble.
            store.add(1, ["Concurrency"])
            preamble_text = (root / "_preamble.md").read_text(encoding="utf-8")
            self.assertEqual(preamble_text, "Some intro text.\n")

    def test_nested_add_resolve_status_rename_reorder(self):
        with tempfile.TemporaryDirectory() as tmp:
            adr_id = make_adr(tmp)
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
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
            updated = store.set_status(b.object_id, "stable", adr=adr_id)
            self.assertEqual(updated.status, "stable")

    def test_render_and_combined_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
            store.add(1, ["Concurrency"], description="Locking and friends.")
            rendered = store.render_plain()
            self.assertNotIn("<!--", rendered)
            self.assertIn("## Concurrency", rendered)

            entries = store.combined_history()
            self.assertEqual(len(entries), 1)

    def test_rewritten_tree_drops_stale_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
            first = store.add(1, ["First"])
            old_dir = root / f"001-{first.object_type}-{first.object_id}-first"
            self.assertTrue(old_dir.is_dir())

            store.rename(first.object_id, "Renamed")
            self.assertFalse(old_dir.is_dir())
            new_dir = root / f"001-{first.object_type}-{first.object_id}-renamed"
            self.assertTrue(new_dir.is_dir())

    def test_force_delete_removes_directory_and_descendants_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
            parent = store.add(1, ["Concurrency"])
            store.add(2, ["Concurrency", "Locking"])
            parent_dir = root / f"001-{parent.object_type}-{parent.object_id}-concurrency"
            self.assertTrue(parent_dir.is_dir())

            store.delete(parent.object_id, cascade=True)
            self.assertFalse(parent_dir.is_dir())
            self.assertEqual(store.list_all(), [])

    def test_move_relocates_directory_and_descendants_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
            store.add(1, ["A"])
            sub = store.add(2, ["A", "Sub"])
            store.add(3, ["A", "Sub", "Grand"])
            store.add(1, ["B"])

            store.move(sub.object_id, 2, ["B"])

            sections = store.list_all()
            by_name = {s.name: s for s in sections}
            b_dir = root / next(
                p.name for p in root.iterdir() if p.is_dir() and "-b" in p.name.lower()
            )
            sub_dir = b_dir / f"{by_name['Sub'].number:03d}-{by_name['Sub'].object_type}-{by_name['Sub'].object_id}-sub"
            grand_dir = sub_dir / f"{by_name['Grand'].number:03d}-{by_name['Grand'].object_type}-{by_name['Grand'].object_id}-grand"
            self.assertTrue(sub_dir.is_dir())
            self.assertTrue((sub_dir / "_content.md").is_file())
            self.assertTrue(grand_dir.is_dir())
            self.assertTrue((grand_dir / "_content.md").is_file())

    def test_duplicate_id_across_content_files_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "spec"
            store = SpecStore(root=root)
            store.init("Design Doc")
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

    def test_shares_root_with_another_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared_root = Path(tmp) / "project"
            spec_store = SpecStore(root=shared_root)
            spec_store.init("Design Doc")
            spec_store.add(1, ["Concurrency"])
            # specctl defaults to single-file mode when nothing exists yet.
            self.assertEqual(spec_store.root, shared_root / "spec.md")

    def test_explicit_directory_candidate_forces_directory_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            shared_root = Path(tmp) / "project"
            store = SpecStore(root=shared_root / "spec")  # matches store name, not yet existing
            self.assertEqual(store.mode, "directory")
            self.assertEqual(store.root, shared_root / "spec")


if __name__ == "__main__":
    unittest.main()


class TestLevelSkipping(unittest.TestCase):
    """design-specctl.md, "Metagroups": a branch may skip levels -- e.g. a
    Chapter holding Points directly -- with only Parts at the root."""

    def _assert_skipping_roundtrip(self, root: Path) -> None:
        store = SpecStore(root=root)
        store.init("Design Doc")
        store.add(1, ["Architektur"])
        store.add(2, ["Architektur", "Komponenten"])
        point = store.add(5, ["Architektur", "Komponenten", "Fehlerfall"], description="Exit 1.")

        self.assertEqual(point.level, 5)
        self.assertEqual(point.level_type, "Point")
        # Level-aligned Object Type: '__' for the skipped Section/Subsection.
        self.assertEqual(point.object_type, "ArKo____Fe")

        reread = {s.object_id: s for s in SpecStore(root=root).list_all()}[point.object_id]
        self.assertEqual(reread.level, 5)
        self.assertEqual(reread.ancestor_levels, ("001-Architektur", "001-Komponenten"))
        self.assertEqual(reread.description(), "Exit 1.")
        self.assertIn("###### Fehlerfall", store.render_plain())

    def test_add_point_directly_under_chapter_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_skipping_roundtrip(Path(tmp) / "design.md")

    def test_add_point_directly_under_chapter_directory_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._assert_skipping_roundtrip(Path(tmp) / "spec")

    def test_unskipped_object_types_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["Architektur"])
            chapter = store.add(2, ["Architektur", "Komponenten"])
            self.assertEqual(chapter.object_type, "ArcKom")

    def test_root_must_be_a_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaisesRegex(SpecStoreError, "only a Part can sit at the root"):
                store.add(3, ["Orphan"])

    def test_child_must_be_deeper_than_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            store.add(3, ["A", "Section"])
            with self.assertRaisesRegex(SpecStoreError, "must be deeper"):
                store.add(3, ["A", "Section", "Other Section"])

    def test_path_longer_than_level_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            with self.assertRaisesRegex(SpecStoreError, "1 to 2 segment"):
                store.add(2, ["A", "B", "C"])

    def test_move_to_point_with_short_parent_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            store.add(2, ["A", "Chapter"])
            loose = store.add(1, ["Loose"])
            moved = store.move(loose.object_id, 5, ["A", "Chapter"])
            self.assertEqual(moved.level, 5)
            self.assertEqual(moved.ancestor_levels, ("001-A", "001-Chapter"))
            self.assertEqual(moved.object_type, "ACh____Lo_")

    def test_move_shifts_subtree_keeping_level_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            section = store.add(3, ["A", "Sec"])
            point = store.add(5, ["A", "Sec", "Pt"])
            store.add(1, ["B"])
            store.move(section.object_id, 2, ["B"])
            by_id = {s.object_id: s for s in store.list_all()}
            self.assertEqual(by_id[section.object_id].level, 2)
            self.assertEqual(by_id[point.object_id].level, 4)
            self.assertEqual(by_id[point.object_id].ancestor_levels, ("002-B", "001-Sec"))

    def test_move_rejects_parent_not_shallower(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = make_store(tmp)
            store.add(1, ["A"])
            store.add(3, ["A", "Sec"])
            other = store.add(1, ["B"])
            with self.assertRaisesRegex(SpecStoreError, "must be deeper"):
                store.move(other.object_id, 3, ["A", "Sec"])


class TestSkippedLevelSiblingOrder(unittest.TestCase):
    """Under one parent, sibling levels must never increase in document
    order -- otherwise Markdown nesting re-parents the deeper Section on the
    next read (design-specctl.md, "Metagroups")."""

    def _store(self, tmp: str, mode: str) -> SpecStore:
        store = SpecStore(root=Path(tmp) / ("design.md" if mode == "file" else "spec"))
        store.init("Design Doc")
        return store

    def test_add_deeper_after_shallower_sibling_rejected_and_unchanged(self):
        for mode in ("file", "directory"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                store = self._store(tmp, mode)
                store.add(1, ["Arch"])
                store.add(2, ["Arch", "Chap"])
                store.add(3, ["Arch", "Chap", "Sec"])
                before = [(s.object_id, s.path_levels) for s in store.list_all()]
                with self.assertRaisesRegex(SpecStoreError, "can't follow the shallower Section"):
                    store.add(5, ["Arch", "Chap", "Direct"])
                self.assertEqual([(s.object_id, s.path_levels) for s in store.list_all()], before)

    def test_deeper_before_shallower_sibling_allowed_and_stable_on_reread(self):
        for mode in ("file", "directory"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                store = self._store(tmp, mode)
                store.add(1, ["Arch"])
                store.add(2, ["Arch", "Chap"])
                point = store.add(5, ["Arch", "Chap", "Direct"])
                store.add(3, ["Arch", "Chap", "Sec"])
                reread = {s.object_id: s for s in store.list_all()}[point.object_id]
                self.assertEqual(reread.ancestor_levels, ("001-Arch", "001-Chap"))

    def test_move_to_end_behind_shallower_sibling_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, "file")
            store.add(1, ["P"])
            store.add(3, ["P", "S"])
            loose = store.add(1, ["Loose"])
            with self.assertRaisesRegex(SpecStoreError, "can't follow"):
                store.move(loose.object_id, 5, ["P"])

    def test_reorder_putting_shallower_first_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, "file")
            store.add(1, ["P"])
            store.add(2, ["P", "C"])
            store.add(5, ["P", "C", "Pt"])
            sec = store.add(3, ["P", "C", "S"])
            with self.assertRaisesRegex(SpecStoreError, "can't follow"):
                store.reorder(sec.object_id, 0)
            by_name = {s.name: s for s in store.list_all()}
            self.assertEqual(by_name["Pt"].ancestor_levels, ("001-P", "001-C"))
