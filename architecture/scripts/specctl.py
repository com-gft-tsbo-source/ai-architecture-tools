#!/usr/bin/env python3
"""specctl -- CLI for managing specification documents as a tree of Section
objects, one per Markdown heading (design-specctl.md).

Deliberately does not reuse lib/cliapp.py: that module's `add`/`add-<type>`
shape assumes a metagroup is pure classification, separate from the object
placed under it (design.md). specctl collapses the two (every metagroup
node *is* the object at that level -- design-specctl.md, "Deviation from
the general model"), so its command surface -- one add-<level> per heading
depth, each creating a populated Section directly -- doesn't fit that
shape. The --root/--json/exit-code/stderr conventions are kept identical
to the other three tools regardless (architecture/scripts/CLAUDE.md: "CLI
structure ... einheitlich ... halten, auch wenn ein Tool das jeweilige
Feature (noch) nicht braucht").

Both single-file and directory mode are implemented (design-specctl.md,
"Object Format"). `--root` resolves to specctl's `spec.md`/`spec` within a
directory shared by all four tools (design.md, "File and Directory
Parameters") -- the same `--root` a user already passes to `adrctl` also
locates specctl's data, deterministically. `adrctl`'s `spec-ref` metainfo
field drives automatic propagation into a Section's `adr` field via
lib/spec_link.py (design-specctl.md, "ADR Linkage") -- `set-adr` here
remains the manual, unlogged way to set/correct it directly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib import spec_render as render
from lib.spec_model import LEVEL_TYPES, SpecSection
from lib.spec_store import SpecStore, SpecStoreError


class CliError(Exception):
    pass


def _level_flag_name(level_type: str) -> str:
    return f"add-{level_type.lower()}"


def _move_flag_name(level_type: str) -> str:
    return f"move-to-{level_type.lower()}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="specctl")
    parser.add_argument(
        "--root", required=True,
        help="A directory shared by all four tools, or any single tool's own file/directory within "
             "it -- resolved to specctl's spec.md / spec (design.md, 'File and Directory Parameters').",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for depth, level_type in enumerate(LEVEL_TYPES, start=1):
        level_parser = subparsers.add_parser(
            _level_flag_name(level_type),
            help=f"Create a new {level_type} Section (depth {depth})",
        )
        level_parser.add_argument(
            "path",
            help=f"'/'-separated path of {depth} heading name(s), ancestors then the new leaf",
        )
        level_parser.add_argument("--description", default="")
        level_parser.add_argument("--id", dest="object_id", default=None, help="Explicit free-form Object ID")
        level_parser.add_argument("--set-status", dest="set_status", default=None)
        level_parser.add_argument("--abbrev", default=None)

    status_parser = subparsers.add_parser("set-status", help="Change a Section's Status")
    status_parser.add_argument("id")
    status_parser.add_argument("status", choices=("draft", "stable", "deprecated"))
    status_parser.add_argument("--message", default="")
    status_parser.add_argument("--force", action="store_true")
    status_parser.add_argument("--adr", default=None, help="Governing ADR ID, required entering stable/deprecated")

    adr_parser = subparsers.add_parser("set-adr", help="Manually set/correct the governing ADR reference")
    adr_parser.add_argument("id")
    adr_parser.add_argument("value")

    description_parser = subparsers.add_parser("set-description", help="Change a Section's Description content")
    description_parser.add_argument("id")
    description_parser.add_argument("value")
    description_parser.add_argument(
        "--adr", default=None,
        help="Governing ADR ID; required if the Section is stable/deprecated and none is set yet",
    )

    rename_parser = subparsers.add_parser("rename", help="Change a Section's heading text")
    rename_parser.add_argument("id")
    rename_parser.add_argument("name")

    reorder_parser = subparsers.add_parser("reorder", help="Move a Section to a new position among its siblings")
    reorder_parser.add_argument("id")
    reorder_parser.add_argument(
        "--after", dest="insert_after", type=int, required=True,
        help="Insert right after this sibling number (0 = before all siblings)",
    )

    for depth, level_type in enumerate(LEVEL_TYPES, start=1):
        move_parser = subparsers.add_parser(
            _move_flag_name(level_type),
            help=f"Move a Section to become a {level_type} (depth {depth}) under a new parent",
        )
        move_parser.add_argument("id")
        move_parser.add_argument(
            "path", nargs="?", default=None,
            help=f"'/'-separated path of {depth - 1} existing ancestor Section name(s) "
                 + ("(omit for move-to-part, which has no parent)" if depth == 1 else "-- the new parent"),
        )

    show_parser = subparsers.add_parser("show", help="Display a Section")
    show_parser.add_argument("id")
    show_parser.add_argument("--history", action="store_true", help="Include History")

    list_parser = subparsers.add_parser("list", help="List Sections")
    list_parser.add_argument("--status", default=None, choices=("draft", "stable", "deprecated"))

    subparsers.add_parser("history", help="Combined History of every Section, newest first")
    subparsers.add_parser("render", help="Emit the document as plain, comment-stripped Markdown")

    return parser


def dispatch(store: SpecStore, args: argparse.Namespace) -> object:
    command = args.command

    for depth, level_type in enumerate(LEVEL_TYPES, start=1):
        if command == _level_flag_name(level_type):
            path_segments = args.path.split("/")
            if len(path_segments) != depth:
                raise CliError(
                    f"{command} expects a {depth}-segment path (got {len(path_segments)}: {args.path!r})"
                )
            try:
                return store.add(
                    depth, path_segments, description=args.description,
                    object_id=args.object_id, initial_status=args.set_status,
                    abbrev_override=args.abbrev,
                )
            except SpecStoreError as exc:
                raise CliError(str(exc)) from exc

    if command == "set-status":
        return store.set_status(args.id, args.status, message=args.message, force=args.force, adr=args.adr)

    if command == "set-adr":
        return store.set_adr(args.id, args.value)

    if command == "set-description":
        return store.set_description(args.id, args.value, adr=args.adr)

    if command == "rename":
        return store.rename(args.id, args.name)

    if command == "reorder":
        return store.reorder(args.id, args.insert_after)

    for depth, level_type in enumerate(LEVEL_TYPES, start=1):
        if command == _move_flag_name(level_type):
            path_segments = args.path.split("/") if args.path else []
            try:
                return store.move(args.id, depth, path_segments)
            except SpecStoreError as exc:
                raise CliError(str(exc)) from exc

    if command == "show":
        return store.resolve_id(args.id)

    if command == "list":
        sections = store.list_all()
        if args.status is not None:
            sections = [s for s in sections if s.status == args.status]
        return sections

    if command == "history":
        return store.combined_history()

    if command == "render":
        return store.render_plain()

    raise CliError(f"unknown command: {command}")


def _print_result(args: argparse.Namespace, result: object) -> None:
    if result is None:
        return

    if args.command == "render":
        print(result, end="")
        return

    if args.command == "history":
        entries = result
        if args.json:
            payload = [
                {"section": render.to_json_dict(section), "entry": {
                    "timestamp": entry.timestamp, "prefix": entry.prefix,
                    "old_status": entry.old_status, "new_status": entry.new_status,
                    "message": entry.message,
                }}
                for section, entry in entries
            ]
            print(json.dumps(payload, indent=2))
        else:
            print(render.combined_history(entries))
        return

    if args.json:
        if isinstance(result, SpecSection):
            print(render.to_json(result))
        elif isinstance(result, list):
            print(render.to_json(result))
        else:
            print(result)
        return

    if isinstance(result, SpecSection):
        if args.command == "show" and getattr(args, "history", False):
            print(render.short_with_history(result))
        elif args.command == "show":
            print(render.full_display(result))
        else:
            print(render.short_line(result))
    elif isinstance(result, list):
        for section in result:
            print(render.short_line(section))
    else:
        print(result)


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        store = SpecStore(root=Path(args.root))
        result = dispatch(store, args)
    except (SpecStoreError, CliError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print_result(args, result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
