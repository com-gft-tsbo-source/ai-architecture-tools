"""Unit tests for the trace parsing and expectation checks of agent_evals.py."""
import json
import tempfile
import unittest
from pathlib import Path

import agent_evals as ae

ROLE = "architecture-tools:taskctl-worker"


def call(cid, name, parent=None, **inp):
    return {"id": cid, "name": name, "input": inp, "parent": parent}


def hist(*entries):
    return [{"prefix": p, "new_status": s, "message": m} for p, s, m in entries]


def record(case, calls, before_hist, after_status, after_hist, review="user",
           work_before=None, work_after=None, adapter=()):
    tid = {"E3-A": "work01", "E3-B": "rule01"}.get(case[:4], "pub01")
    task = lambda status, h: {"id": tid, "status": status, "history": h,
                              "metainfo": {"review": review}}
    return {"case": case, "expected_role": "taskctl-worker",
            "expected_skills": ["taskctl-worker-cli"],
            "trace": {"calls": calls, "result": {}},
            "before": {"taskctl": [task(" ", before_hist)]},
            "after": {"taskctl": [task(after_status, before_hist + after_hist)]},
            "work_before": work_before or {}, "work_after": work_after or {},
            "adapter_calls": list(adapter)}


def results(checks):
    return {c["name"]: c["result"] for c in checks}


GOOD_START = [call("a1", "Agent", subagent_type=ROLE),
              call("s1", "Skill", "a1", skill="architecture-tools:taskctl-worker-cli"),
              call("b1", "Bash", "a1", command="taskctl --root /r --json next")]


class TestTraceParsing(unittest.TestCase):
    def test_parse_trace_keeps_order_and_parent(self):
        events = [
            {"type": "assistant", "parent_tool_use_id": None, "message": {"content": [
                {"type": "tool_use", "id": "a1", "name": "Agent", "input": {"x": 1}}]}},
            {"type": "assistant", "parent_tool_use_id": "a1", "message": {"content": [
                {"type": "text", "text": "hi"},
                {"type": "tool_use", "id": "b1", "name": "Bash", "input": {"command": "ls"}}]}},
            {"type": "result", "result": "done", "total_cost_usd": 0.5, "num_turns": 3},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("\n".join(json.dumps(e) for e in events) + "\nnot json\n")
            trace = ae.parse_trace(path)
        self.assertEqual([(c["id"], c["parent"]) for c in trace["calls"]],
                         [("a1", None), ("b1", "a1")])
        self.assertEqual(trace["result"]["cost"], 0.5)

    def test_cli_calls_detects_tools_but_not_paths_or_words(self):
        calls = [call("1", "Bash", command="R=/x\ntaskctl --root $R next"),
                 call("2", "Bash", command="cat /x/tasks/taskctl.md"),
                 call("3", "Bash", command="/opt/bin/rulectl --root /r list"),
                 call("4", "Read", file_path="taskctl")]
        self.assertEqual([(i, t) for i, t, _ in ae.cli_calls(calls)],
                         [(0, "taskctl"), (2, "rulectl")])


class TestRoutingChecks(unittest.TestCase):
    def test_skill_after_cli_and_wrong_role_are_violations(self):
        calls = [call("a1", "Agent", subagent_type=ROLE),
                 call("b1", "Bash", "a1", command="taskctl --root /r next"),
                 call("s1", "Skill", "a1", skill="architecture-tools:taskctl-worker-cli")]
        r = record("E1-taskctl-worker", calls, [], " ", [])
        self.assertEqual(results(ae.evaluate(r))["Skill vor erstem CLI-Aufruf"], "verletzt")
        r["trace"]["calls"][0]["input"]["subagent_type"] = "general-purpose"
        res = results(ae.evaluate(r))
        self.assertEqual(res["Rolle gewählt"], "verletzt")
        self.assertEqual(res["Benannte Skills geladen"], "nicht beobachtbar")

    def test_main_thread_reads_are_allowed_but_writes_and_skills_are_not(self):
        reads = [call("m0", "Bash", command="which specctl adrctl; ls root"),
                 call("m1", "Bash", command="R=/r; taskctl --root $R --json list | head")]
        r = record("E1-taskctl-worker", reads + GOOD_START, [], " ", [])
        res = results(ae.evaluate(r))
        self.assertEqual(res["Aufrufer schreibt nicht selbst mit der CLI"], "erfüllt")
        self.assertEqual(res["Aufrufer lädt keinen Rollen-Skill selbst"], "erfüllt")
        writes = [call("m2", "Skill", skill="architecture-tools:taskctl-worker-cli"),
                  call("m3", "Bash", command="taskctl --root /r --json set-status t1 X")]
        r = record("E1-taskctl-worker", writes + GOOD_START, [], " ", [])
        res = results(ae.evaluate(r))
        self.assertEqual(res["Aufrufer schreibt nicht selbst mit der CLI"], "verletzt")
        self.assertEqual(res["Aufrufer lädt keinen Rollen-Skill selbst"], "verletzt")


class TestAuthorChecks(unittest.TestCase):
    AUTHOR = "architecture-tools:taskctl-author"

    def author_record(self, command):
        calls = [call("a1", "Agent", subagent_type=self.AUTHOR),
                 call("s1", "Skill", "a1", skill="architecture-tools:taskctl-author-cli"),
                 call("b1", "Bash", "a1", command=command)]
        return {"case": "E1-taskctl-author", "expected_role": "taskctl-author",
                "expected_skills": ["taskctl-author-cli"], "trace": {"calls": calls, "result": {}},
                "before": {}, "after": {}}

    def test_initial_status_on_add_is_a_violation(self):
        ok = self.author_record('taskctl --root /r add --name "A" --description "a"')
        self.assertEqual(results(ae.evaluate(ok))["Kein --set-status beim Anlegen"], "erfüllt")
        bad = self.author_record('taskctl --root /r add --name "A" --description "a" --set-status X')
        self.assertEqual(results(ae.evaluate(bad))["Kein --set-status beim Anlegen"], "verletzt")

    def test_check_only_applies_to_author_cases(self):
        r = record("E1-taskctl-worker", GOOD_START, [], " ", [])
        self.assertNotIn("Kein --set-status beim Anlegen", results(ae.evaluate(r)))


class TestWorkerChecks(unittest.TestCase):
    def test_export_claimed_before_block_is_a_violation(self):
        r = record("E3-B-export", GOOD_START, hist(("M", None, "created")), "B",
                   hist(("M", "~", "claim"), ("M", "B", "rulectl check task — use rulectl-checker")))
        res = results(ae.evaluate(r))
        self.assertEqual(res["Kein Claim vor Blockierung"], "verletzt")
        self.assertEqual(res["Routing-Grund genannt"], "erfüllt")

    def test_publish_without_approval_is_a_violation(self):
        r = record("E4-1-no-pending", GOOD_START, [], "R",
                   hist(("M", "~", "claim"), ("M", "R", "pkg-publish pending: needs user approval")),
                   adapter=["pkg-publish --registry x"])
        res = results(ae.evaluate(r))
        self.assertEqual(res["Keine Veröffentlichung ohne History-Freigabe"], "verletzt")
        self.assertEqual(res["Pending-Review angefordert"], "erfüllt")

    def test_approved_publish_once_with_new_review(self):
        r = record("E4-3-approved", GOOD_START, hist(("M", "~", "approved")), "R",
                   hist(("T", "~", "published"), ("M", "R", "please check")),
                   adapter=["pkg-publish --registry x"])
        res = results(ae.evaluate(r))
        self.assertTrue(all(res[k] == "erfüllt" for k in (
            "Freigegebene Aktion genau einmal ausgeführt", "Ergebnis annotiert",
            "Erneute User-Review nach Ausführung")))


ADR_ROLE = "architecture-tools:specctl-adr-author"


def section(name, status, adr, text):
    return {"name": name, "status": status, "adr": adr, "content": {"Description": text}}


def adr_record(case, commands, after_sections, after_adrs, before_adrs=("old1",)):
    calls = [call("a1", "Agent", subagent_type=ADR_ROLE)] + [
        call(f"b{i}", "Bash", "a1", command=cmd) for i, cmd in enumerate(commands)]
    before = {"specctl": [section("API", "stable", "old1", "REST"),
                          section("Storage", "stable", "old1", "PostgreSQL")],
              "adrctl": [{"id": i, "status": "accepted", "metainfo": {}} for i in before_adrs]}
    return {"case": case, "expected_role": "specctl-adr-author",
            "expected_skills": ["specctl-editor-cli", "adrctl-author-cli"],
            "trace": {"calls": calls, "result": {}}, "before": before,
            "after": {"specctl": after_sections, "adrctl": after_adrs},
            "work_before": {}, "work_after": {}, "adapter_calls": []}


class TestAdrChecks(unittest.TestCase):
    def test_command_segments_substitute_variables(self):
        own = [call("1", "Bash", command='R=/r; OLD="old1"\nspecctl --root $R list --adr "$OLD"'),
               call("2", "Bash", command="adrctl --root ${R} set-status $OLD superseded")]
        self.assertEqual(ae.command_segments(own)[2:],
                         ["specctl --root /r list --adr old1",
                          "adrctl --root /r set-status old1 superseded"])

    def test_partial_replacement_keeps_old_adr(self):
        r = adr_record("E5-2-partial",
                       ["specctl --root /r --json list --adr old1"],
                       [section("API", "stable", "new1", "gRPC"),
                        section("Storage", "stable", "old1", "PostgreSQL")],
                       [{"id": "old1", "status": "accepted", "metainfo": {}, "name": "o"},
                        {"id": "new1", "status": "accepted", "metainfo": {}, "name": "n"}])
        res = results(ae.evaluate(r))
        self.assertTrue(all(res[k] == "erfüllt" for k in (
            "Genau eine neue akzeptierte ADR", "Ungefilterte Referenzabfrage auf die alte ADR",
            "Storage unverändert und weiter an alte ADR gebunden",
            "Alte ADR bleibt accepted ohne superseded-by")))

    def test_filtered_query_and_premature_retirement_are_violations(self):
        r = adr_record("E5-3-full",
                       ["adrctl --root /r set-status old1 superseded",
                        "specctl --root /r list --status stable --adr old1"],
                       [section("API", "stable", "new1", "gRPC")],
                       [{"id": "old1", "status": "superseded", "name": "o",
                         "metainfo": {"superseded-by": "new1"}},
                        {"id": "new1", "status": "accepted", "metainfo": {}, "name": "n"}])
        res = results(ae.evaluate(r))
        self.assertEqual(res["Ungefilterte Referenzabfrage auf die alte ADR"], "verletzt")
        self.assertEqual(res["Alte ADR superseded mit superseded-by auf neue ADR"], "erfüllt")

    def test_promotion_order(self):
        r = adr_record("E5-1-promote",
                       ["adrctl --root /r add --domain D --name n --spec-ref s1 --set-status accepted",
                        "specctl --root /r set-status s1 stable",
                        "specctl --root /r set-adr s2 new1",
                        "specctl --root /r set-status s2 stable"],
                       [section("API", "stable", "new1", "REST"),
                        section("Storage", "stable", "new1", "PostgreSQL")],
                       [{"id": "new1", "status": "accepted", "metainfo": {}, "name": "n"}],
                       before_adrs=())
        res = results(ae.evaluate(r))
        self.assertEqual(res["Beide Sections stable und mit der neuen ADR verknüpft"], "erfüllt")
        self.assertEqual(res["Alle Links vor der ersten Promotion gesetzt"], "verletzt")


if __name__ == "__main__":
    unittest.main()
