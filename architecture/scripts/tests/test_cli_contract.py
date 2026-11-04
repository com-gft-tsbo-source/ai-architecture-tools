"""Cross-tool CLI contract (scripts/CLAUDE.md, "Konsistenz zwischen den Tools").

specctl has its own CLI next to lib/cliapp.py, so the shared contract is
checked here once for all five tools instead of being kept in sync by hand:
exit codes (0 ok, 1 error, 2 usage error from argparse), errors on stderr
(except the machine-readable `reason` of NoWorkAvailable/GuardViolation
under --json, tested per tool),
valid JSON on stdout with --json, and one shared --root per project.
A new tool is covered by adding it to TOOLS.
"""

import contextlib
import io
import json
import os
import tempfile
import unittest
from dataclasses import dataclass
from typing import Callable

import adrctl
import questctl
import rulectl
import specctl
import taskctl


@dataclass(frozen=True)
class Tool:
    name: str
    main: Callable[[list[str]], int]
    # Commands that create the store's metagroups; the last one of create
    # adds exactly one object and must print it with --json.
    prepare: tuple[tuple[str, ...], ...]
    create: tuple[str, ...]


TOOLS = (
    Tool("taskctl", taskctl.main, (), ("add", "--name", "Task")),
    Tool("questctl", questctl.main, (), ("add", "--name", "Question")),
    Tool(
        "rulectl",
        rulectl.main,
        (("add-language", "Py"), ("add-context", "Py/Core"), ("add-category", "Py/Core/Style")),
        ("add", "--name", "Rule", "--category", "Py/Core/Style"),
    ),
    Tool("adrctl", adrctl.main, (("add-domain", "Backend"),), ("add", "--name", "Decision", "--domain", "Backend")),
    Tool("specctl", specctl.main, (("init", "Doc"),), ("add-part", "Intro")),
)


def run(tool: Tool, argv: list[str]) -> tuple[int, str, str]:
    """Run a tool in-process; argparse's SystemExit is mapped to its code."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = tool.main(argv)
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def create_object(tool: Tool, root: str) -> str:
    """Prepare metagroups and add one object; returns its id."""
    for argv in tool.prepare:
        code, _out, err = run(tool, ["--root", root, *argv])
        assert code == 0, f"{tool.name} {argv}: {err!r}"
    code, out, err = run(tool, ["--root", root, "--json", *tool.create])
    assert code == 0, f"{tool.name} {tool.create}: {err!r}"
    return json.loads(out)["id"]


def create_object_default(tool: Tool) -> str:
    """create_object() with the implicit --root."""
    for argv in tool.prepare:
        code, _out, err = run(tool, list(argv))
        assert code == 0, f"{tool.name} {argv}: {err!r}"
    code, out, err = run(tool, ["--json", *tool.create])
    assert code == 0, f"{tool.name} {tool.create}: {err!r}"
    return json.loads(out)["id"]


@contextlib.contextmanager
def _chdir(path: str):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class CliContractTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_help_exits_0_and_names_global_options(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                code, out, _err = run(tool, ["--help"])
                self.assertEqual(code, 0)
                self.assertIn("--root", out)
                self.assertIn("--json", out)

    def test_root_defaults_to_existing_doc_directory(self):
        # design.md, "File and Directory Parameters": --root is optional;
        # omitted, it means the directory "doc" relative to the cwd.
        for tool in TOOLS:
            with self.subTest(tool=tool.name), tempfile.TemporaryDirectory() as cwd:
                with _chdir(cwd):
                    code, _out, err = run(tool, ["list"])
                    self.assertEqual(code, 1)  # no doc directory
                    self.assertIn("'doc'", err)
                    self.assertFalse(os.path.exists("doc"))
                    os.mkdir("doc")
                    code, _out, err = run(tool, ["list"])
                    self.assertEqual(code, 1)  # doc exists, store does not
                    self.assertIn("no ", err)
                    self.assertEqual(os.listdir("doc"), [])  # read did not create
                    object_id = create_object_default(tool)
                    code, out, _err = run(tool, ["--json", "show", object_id])
                    self.assertEqual(code, 0)

    def test_creating_commands_only_create_the_store(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name), tempfile.TemporaryDirectory() as tmp:
                code, _out, _err = run(tool, ["--root", tmp, "show", "x"])
                self.assertEqual(code, 1)
                self.assertEqual(os.listdir(tmp), [])
                create_object(tool, tmp)
                self.assertTrue(os.listdir(tmp))

    def test_unknown_subcommand_is_usage_error(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                code, out, err = run(tool, ["--root", self.root, "no-such-command"])
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertTrue(err)

    def test_runtime_error_exits_1_on_stderr_only(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                create_object(tool, self.root)
                for json_flag in ([], ["--json"]):
                    code, out, err = run(tool, ["--root", self.root, *json_flag, "show", "nope00"])
                    self.assertEqual(code, 1)
                    self.assertEqual(out, "")
                    self.assertTrue(err.strip())

    def test_json_output_is_valid_json_on_stdout(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                object_id = create_object(tool, self.root)

                code, out, err = run(tool, ["--root", self.root, "--json", "show", object_id])
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(json.loads(out)["id"], object_id)

                code, out, err = run(tool, ["--root", self.root, "--json", "list"])
                self.assertEqual((code, err), (0, ""))
                self.assertEqual([item["id"] for item in json.loads(out)], [object_id])

    def test_human_output_is_not_json(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                object_id = create_object(tool, self.root)
                code, out, err = run(tool, ["--root", self.root, "list"])
                self.assertEqual((code, err), (0, ""))
                self.assertIn(object_id, out)
                with self.assertRaises(json.JSONDecodeError):
                    json.loads(out)

    def test_render_exists_in_all_tools_and_requires_the_store(self):
        # design.md, "Operations Across All Objects": render is a read-only view.
        for tool in TOOLS:
            with self.subTest(tool=tool.name), tempfile.TemporaryDirectory() as tmp:
                code, _out, _err = run(tool, ["--root", tmp, "render"])
                self.assertEqual(code, 1)
                self.assertEqual(os.listdir(tmp), [])
                create_object(tool, tmp)
                code, out, err = run(tool, ["--root", tmp, "render"])
                self.assertEqual((code, err), (0, ""))
                self.assertTrue(out.strip())

    def test_all_tools_share_one_root_without_seeing_each_other(self):
        ids = {tool.name: create_object(tool, self.root) for tool in TOOLS}
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                code, out, _err = run(tool, ["--root", self.root, "--json", "list"])
                self.assertEqual(code, 0)
                self.assertEqual([item["id"] for item in json.loads(out)], [ids[tool.name]])


if __name__ == "__main__":
    unittest.main()


class IdSelectorTest(unittest.TestCase):
    """Every command taking an object ID accepts the raw ID, the Signature,
    a `list` output line or a unique Signature fragment (lib/idmatch.py)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _create(self, tool: Tool) -> dict:
        create_object(tool, self.root)
        code, out, err = run(tool, ["--root", self.root, "--json", "list"])
        self.assertEqual(code, 0, err)
        return json.loads(out)[0]

    def test_show_accepts_id_signature_list_line_and_fragment(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                with tempfile.TemporaryDirectory() as root:
                    self.root = root
                    obj = self._create(tool)
                    _code, list_out, _err = run(tool, ["--root", root, "list"])
                    selectors = [
                        obj["id"], obj["signature"], list_out.splitlines()[0],
                        obj["id"][1:5], obj["signature"].lower(),
                    ]
                    for selector in selectors:
                        code, out, err = run(tool, ["--root", root, "--json", "show", selector])
                        self.assertEqual(code, 0, f"{selector!r}: {err}")
                        self.assertEqual(json.loads(out)["id"], obj["id"])

    def test_unknown_and_ambiguous_selectors_exit_1(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                with tempfile.TemporaryDirectory() as root:
                    self.root = root
                    first = self._create(tool)
                    # Second object with a longer name: IDs derive from the name.
                    name = first["name"]
                    second = [name + "B" if arg == name else arg for arg in tool.create]
                    code, _out, err = run(tool, ["--root", root, *second])
                    self.assertEqual(code, 0, err)
                    code, _out, err = run(tool, ["--root", root, "show", "no-such-thing-xyz"])
                    self.assertEqual(code, 1)
                    self.assertTrue(err.strip())
                    # The name part is shared by both objects.
                    fragment = first["signature"].split("-", 3)[3].lower()
                    code, _out, err = run(tool, ["--root", root, "show", fragment])
                    self.assertEqual(code, 1)
                    self.assertIn("ambiguous", err)

    def test_mutating_command_accepts_fragment(self):
        for tool in TOOLS:
            with self.subTest(tool=tool.name):
                with tempfile.TemporaryDirectory() as root:
                    self.root = root
                    obj = self._create(tool)
                    code, _out, err = run(tool, ["--root", root, "delete", obj["signature"].lower()])
                    self.assertEqual(code, 0, err)
                    code, out, err = run(tool, ["--root", root, "--json", "list"])
                    self.assertEqual(json.loads(out), [])
