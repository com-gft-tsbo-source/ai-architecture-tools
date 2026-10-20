import tempfile
import unittest
from pathlib import Path

import rulectl
from lib import tasklist
from lib.store import Store, StoreError
from lib.taskctl_spec import DONE, OPEN, build_spec as build_taskctl_spec


def make_rulectl_store(root: Path) -> Store:
    return Store(spec=rulectl.build_spec(), root=root)


def make_taskctl_store(root: Path) -> Store:
    return Store(spec=build_taskctl_spec(), root=root)


def _ensure_metagroup_path(store: Store, segments: list[str]) -> None:
    """add_metagroup_path always creates a new leaf -- unlike add-<type> at
    the CLI (called once per path), a test helper adding several Rules
    under the same path must only create each segment the first time."""
    for depth in range(1, len(segments) + 1):
        prefix = segments[:depth]
        try:
            store.resolve_metagroup_path(prefix)
        except StoreError:
            store.add_metagroup_path(prefix)


def add_rule(
    store: Store, *, language="Python", context="backend", category="validation",
    name="No bare except", description="Explain the rule.", procedure="",
    checkable="llm", tool="", tool_rule="", status="active", object_id=None,
) -> object:
    _ensure_metagroup_path(store, [language])
    _ensure_metagroup_path(store, [language, context])
    _ensure_metagroup_path(store, [language, context, category])
    metainfo = {"checkable": checkable}
    if tool:
        metainfo["tool"] = tool
    if tool_rule:
        metainfo["tool-rule"] = tool_rule
    return store.add(
        metagroup_path=[language, context, category], name=name, description=description,
        content={"Procedure": procedure} if procedure else None,
        metainfo=metainfo, initial_status=status, object_id=object_id,
    )


class TestFieldMapping(unittest.TestCase):
    def test_origin_is_persisted_and_repairs_legacy_exports(self):
        for store_name in ("tasks", "tasks.md"):
            with self.subTest(store=store_name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                tasks = make_taskctl_store(root / store_name)
                tasks.add_metagroup_path(["Existing"])
                rules = make_rulectl_store(root / "rules")
                rule = add_rule(rules, object_id="rule01")
                tasklist.run(root, rules)
                expected = f"rulectl:{rule.object_id}"
                self.assertEqual(tasks.get(rule.object_id).metainfo_value("origin"), expected)

                # Simulate a legacy export without the new provenance marker.
                tasks.set_metainfo(rule.object_id, "origin", "")
                tasklist.run(root, rules)
                persisted = make_taskctl_store(root / store_name)
                self.assertEqual(persisted.get(rule.object_id).metainfo_value("origin"), expected)
                self.assertEqual(len(persisted.list_all()), 1)

    def test_llm_checkable_rule_embeds_description_and_procedure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, description="Explain it.", procedure="Do the thing.", checkable="llm")

            tasks = tasklist.run(root, rules)
            self.assertEqual(len(tasks), 1)
            task = tasks[0]
            self.assertEqual(task.metainfo_value("assignee-type"), "agent")
            self.assertIn("Explain it.", task.content["Description"])
            self.assertIn("### Procedure", task.content["Description"])
            self.assertIn("Do the thing.", task.content["Description"])

    def test_llm_checkable_rule_without_procedure_omits_subsection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, description="Explain it.", procedure="", checkable="llm")

            tasks = tasklist.run(root, rules)
            self.assertNotIn("### Procedure", tasks[0].content["Description"])

    def test_tool_checkable_rule_gets_tool_assignee_and_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, checkable="ruff", tool="ruff", tool_rule="E722")

            tasks = tasklist.run(root, rules)
            task = tasks[0]
            self.assertEqual(task.metainfo_value("assignee-type"), "tool")
            self.assertEqual(task.metainfo_value("assignee-name"), "ruff")
            self.assertIn("ruff", task.content["Description"])
            self.assertIn("E722", task.content["Description"])


class TestPhaseMapping(unittest.TestCase):
    def test_two_rules_same_path_share_one_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, name="Rule A", object_id="rulea1")
            add_rule(rules, name="Rule B", object_id="ruleb2")

            tasklist.run(root, rules)
            tasks_store = make_taskctl_store(root / "tasks")
            self.assertEqual(len(tasks_store.metagroup_paths()), 1)
            self.assertEqual(len(tasks_store.list_all()), 2)

    def test_phase_name_uses_double_colon_separator_and_strips_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, language="Python", context="backend", category="validation")

            tasklist.run(root, rules)
            tasks_store = make_taskctl_store(root / "tasks")
            [phase_path] = tasks_store.metagroup_paths()
            from lib.abbrev import strip_sort_prefix
            self.assertEqual(strip_sort_prefix(phase_path[0]), "Python::backend::validation")


class TestScope(unittest.TestCase):
    def test_draft_and_obsolete_rules_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, name="Active", object_id="active1", status="active")
            add_rule(rules, name="Draft", object_id="draft01", status="draft")
            add_rule(rules, name="Obsolete", object_id="obsolet", status="obsolete")

            tasks = tasklist.run(root, rules)
            self.assertEqual([t.object_id for t in tasks], ["active1"])

    def test_under_filter_scopes_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, language="Python", object_id="pyrule")
            add_rule(rules, language="Go", context="backend", category="validation", object_id="gorule")

            resolved_under = rules.resolve_metagroup_path(["Python"])
            tasks = tasklist.run(root, rules, under=resolved_under)
            self.assertEqual([t.object_id for t in tasks], ["pyrule"])


class TestTaskIdentity(unittest.TestCase):
    def test_task_id_equals_rule_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            rule = add_rule(rules)

            [task] = tasklist.run(root, rules)
            self.assertEqual(task.object_id, rule.object_id)


class TestReExport(unittest.TestCase):
    def test_rerun_updates_existing_task_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, object_id="rule001", description="v1")

            tasklist.run(root, rules)
            rules.set_content("rule001", "Description", "v2")
            tasklist.run(root, rules)

            tasks_store = make_taskctl_store(root / "tasks")
            all_tasks = tasks_store.list_all()
            self.assertEqual(len(all_tasks), 1)
            self.assertIn("v2", all_tasks[0].content["Description"])

    def test_rerun_without_field_changes_only_adds_annotate_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, object_id="rule001")

            tasklist.run(root, rules)
            tasks_store = make_taskctl_store(root / "tasks")
            before = len(tasks_store.get("rule001").history)

            tasklist.run(root, rules)
            tasks_store = make_taskctl_store(root / "tasks")
            after_task = tasks_store.get("rule001")
            self.assertEqual(len(after_task.history), before + 1)
            self.assertEqual(after_task.history[-1].prefix, "T")

    def test_rerun_resets_done_status_and_annotates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, object_id="rule001")

            tasklist.run(root, rules)
            tasks_store = make_taskctl_store(root / "tasks")
            tasks_store.set_status("rule001", DONE, force=True)

            tasklist.run(root, rules)
            tasks_store = make_taskctl_store(root / "tasks")
            task = tasks_store.get("rule001")
            self.assertEqual(task.status, OPEN)
            prefixes = [entry.prefix for entry in task.history]
            self.assertIn("T", prefixes)
            status_changes = [
                e for e in task.history if e.prefix == "M" and e.new_status == OPEN
            ]
            self.assertTrue(status_changes)

    def test_rerun_moves_task_when_rule_metagroup_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = make_rulectl_store(root / "rules")
            add_rule(rules, object_id="rule001", language="Python", context="backend", category="validation")
            rules.add_metagroup_path(["Python", "backend", "other"])

            tasklist.run(root, rules)
            rules.set_metagroup("rule001", ["Python", "backend", "other"])
            tasklist.run(root, rules)

            tasks_store = make_taskctl_store(root / "tasks")
            self.assertEqual(len(tasks_store.metagroup_paths()), 2)
            task = tasks_store.get("rule001")
            from lib.abbrev import strip_sort_prefix
            self.assertEqual(strip_sort_prefix(task.metagroup_levels[0]), "Python::backend::other")


if __name__ == "__main__":
    unittest.main()
