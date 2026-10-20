"""CLI integration scenarios for the documented agent recipes.

These exercise the required store semantics, not an LLM's adherence to prompts.
"""
import contextlib
import io
import json
import tempfile
import unittest

import adrctl
import questctl
import specctl


class TestAgentWorkflowRecipes(unittest.TestCase):
    def call(self, tool, root, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = tool.main(["--root", root, "--json", *args])
        self.assertEqual(code, 0, err.getvalue())
        output = out.getvalue().strip()
        return json.loads(output) if output.startswith(("{", "[")) else output

    def test_sequential_snapshot_leaves_unanswered_question_open_and_finishes_later_one(self):
        with tempfile.TemporaryDirectory() as root:
            first = self.call(questctl, root, "add", "--name", "Unknown requirement")["id"]
            second = self.call(questctl, root, "add", "--name", "Supported requirement")["id"]
            snapshot = self.call(questctl, root, "next-all")
            self.assertEqual([q["id"] for q in snapshot], [first, second])
            self.assertEqual([self.call(questctl, root, "show", q["id"])["status"]
                              for q in snapshot], [" ", " "])
            # No evidence for the first Question: annotate without claiming.
            self.call(questctl, root, "annotate", first, "--message", "No matching passage")
            # Advance by snapshot ID instead of calling next again.
            self.call(questctl, root, "set-status", second, "~", "--message", "Researching")
            self.call(questctl, root, "answer", second, "Supported answer", "--message", "spec section 2")
            self.call(questctl, root, "set-status", second, "X")
            self.assertEqual(self.call(questctl, root, "show", first)["status"], " ")
            self.assertEqual(self.call(questctl, root, "show", second)["status"], "X")
            self.assertEqual([q["id"] for q in self.call(questctl, root, "next-all")], [first])

    def test_shared_promotion_then_partial_and_complete_adr_replacement(self):
        with tempfile.TemporaryDirectory() as root:
            self.call(specctl, root, "init", "Design")
            sections = [self.call(specctl, root, "add-part", name)["id"] for name in ("API", "Storage")]
            self.call(adrctl, root, "add-domain", "Design")
            domains = self.call(adrctl, root, "show-metagroups")
            self.assertTrue(domains)

            def create_adr(name, section, description):
                return self.call(
                    adrctl, root, "add", "--domain", "Design", "--name", name,
                    "--description", description, "--spec-ref", section,
                    "--set-status", "accepted",
                )["id"]

            founding = create_adr("Accept common design", sections[0], "Accept API and Storage together")
            self.call(specctl, root, "set-adr", sections[1], founding)
            for section in sections:
                self.call(specctl, root, "set-status", section, "stable")
                self.assertEqual(self.call(specctl, root, "show", section)["adr"], founding)
            self.assertEqual(len(self.call(adrctl, root, "list")), 1)

            # One mixed topic revises stable API and promotes a new draft section.
            new_section = self.call(specctl, root, "add-part", "API details")["id"]
            replacement = create_adr("Revise API", sections[0], "Replaces only API; accepts API details")
            self.call(specctl, root, "set-adr", new_section, replacement)
            self.call(specctl, root, "set-status", new_section, "stable")
            self.call(specctl, root, "set-description", sections[0], "Revised API")
            self.assertEqual(self.call(specctl, root, "show", new_section)["adr"], replacement)
            self.assertEqual(len(self.call(adrctl, root, "list")), 2)
            remaining = self.call(specctl, root, "list", "--adr", founding)
            self.assertEqual([s["id"] for s in remaining], [sections[1]])
            self.assertEqual(self.call(adrctl, root, "show", founding)["status"], "accepted")
            self.assertFalse(self.call(adrctl, root, "show", founding)["metainfo"].get("superseded-by"))

            final = create_adr("Revise Storage", sections[1], "Replaces remaining Storage decision")
            self.call(specctl, root, "set-description", sections[1], "Revised Storage")
            self.assertEqual(self.call(specctl, root, "list", "--adr", founding), [])
            self.call(adrctl, root, "info-superseded-by", founding, final)
            self.call(adrctl, root, "set-status", founding, "superseded")
            self.assertEqual(self.call(adrctl, root, "show", founding)["status"], "superseded")
