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

    def test_main_thread_cli_use_is_a_violation(self):
        calls = GOOD_START + [call("m1", "Bash", command="taskctl --root /r list")]
        r = record("E1-taskctl-worker", calls, [], " ", [])
        self.assertEqual(results(ae.evaluate(r))["Aufrufer arbeitet nicht selbst mit der CLI"],
                         "verletzt")


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


if __name__ == "__main__":
    unittest.main()
