"""Generic argparse CLI, built from a ToolSpec (design.md, "CLI Contract").

Each of taskctl/rulectl/adrctl builds its parser via build_parser(), adds
any tool-specific extra subcommands directly to the returned subparsers
(and a matching handler in `extra_handlers`), then calls main(). This is
what keeps the CLI structure uniform across all three tools without one
importing another (architecture/scripts/CLAUDE.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional

from lib import render
from lib.model import ObjectRecord
from lib.store import ReindexReport, Store, StoreError
from lib.toolspec import ToolSpec

Handler = Callable[[Store, argparse.Namespace], object]


class CliError(Exception):
    pass


class DeferredOperationError(Exception):
    pass


def _flag_name(type_name: str) -> str:
    return type_name.lower().replace(" ", "-")


def build_parser(spec: ToolSpec) -> tuple[argparse.ArgumentParser, "argparse._SubParsersAction"]:
    parser = argparse.ArgumentParser(prog=spec.name)
    parser.add_argument(
        "--root", required=True,
        help="A directory shared by all four tools, or any single tool's own file/directory within "
             "it -- resolved to this tool's <root_name>.md / <root_name> (design.md, "
             "'File and Directory Parameters').",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add", help="Create a new object")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--description", default="")
    add_parser.add_argument("--id", dest="object_id", default=None, help="Explicit free-form Object ID")
    add_parser.add_argument("--set-status", dest="set_status", default=None)
    for level in spec.metagroup_levels:
        add_parser.add_argument(
            f"--{_flag_name(level.type)}", dest=f"metagroup__{level.type}", default=None,
            help=f"Assign this object to the given {level.type} metagroup path",
        )
    for metainfo in spec.metainfo:
        add_parser.add_argument(f"--{_flag_name(metainfo.type)}", dest=f"metainfo__{metainfo.type}", default=None)
    for block in spec.user_content_blocks:
        if block == "Description":
            continue
        add_parser.add_argument(f"--{_flag_name(block)}", dest=f"content__{block}", default="")

    for level in spec.metagroup_levels:
        level_parser = subparsers.add_parser(
            f"add-{_flag_name(level.type)}", help=f"Create a new {level.type} metagroup path"
        )
        level_parser.add_argument("name", help="Path-like name, e.g. 'Python/001-backend' for a nested level")
        level_parser.add_argument("--abbrev", default=None)

    status_parser = subparsers.add_parser("set-status", help="Change an object's Status")
    status_parser.add_argument("id")
    status_parser.add_argument("status")
    status_parser.add_argument("--message", default="")
    status_parser.add_argument("--force", action="store_true")

    for metainfo in spec.metainfo:
        metainfo_parser = subparsers.add_parser(
            f"set-{_flag_name(metainfo.type)}", help=f"Set {metainfo.type} on an object"
        )
        metainfo_parser.add_argument("id")
        metainfo_parser.add_argument("value")

    show_parser = subparsers.add_parser("show", help="Display an object")
    show_parser.add_argument("id")
    show_parser.add_argument("--history", action="store_true", help="Include History")

    reorder_parser = subparsers.add_parser("reorder", help="Move an object to a new position among its siblings")
    reorder_parser.add_argument("id")
    reorder_parser.add_argument("--after", dest="insert_after", type=int, required=True,
                                 help="Insert right after this sibling number (0 = before all siblings)")

    subparsers.add_parser("show-metagroups", help="List all declared metagroup paths")
    subparsers.add_parser("reindex", help="Rebuild .index.json caches from the object files")
    subparsers.add_parser("history", help="Combined History of every object, newest first")

    list_parser = subparsers.add_parser("list", help="List objects")
    list_parser.add_argument("--status", default=None)

    return parser, subparsers


def register_deferred(subparsers: "argparse._SubParsersAction", name: str, extra_handlers: dict[str, Handler]) -> None:
    """Register a subcommand that is documented but not yet specified
    (currently: rulectl/adrctl's `tasklist`) -- discoverable via --help,
    but fails deterministically with exit code 1 rather than a no-op or
    'unrecognized arguments'."""
    subparsers.add_parser(name, help=f"{name}: not yet specified (deferred)")

    def handler(store: Store, args: argparse.Namespace) -> object:
        raise DeferredOperationError(f"{name}: not yet specified")

    extra_handlers[name] = handler


def _metagroup_path_for_add(spec: ToolSpec, args: argparse.Namespace) -> list[str]:
    supplied = [
        (level.type, getattr(args, f"metagroup__{level.type}"))
        for level in spec.metagroup_levels
        if getattr(args, f"metagroup__{level.type}") is not None
    ]
    if len(supplied) != 1:
        flags = ", ".join(f"--{_flag_name(l.type)}" for l in spec.metagroup_levels)
        raise CliError(f"add requires exactly one of [{flags}] specifying the object's metagroup path")
    return supplied[0][1].split("/")


def dispatch(spec: ToolSpec, store: Store, args: argparse.Namespace, extra_handlers: dict[str, Handler]) -> object:
    command = args.command

    if command in extra_handlers:
        return extra_handlers[command](store, args)

    if command == "add":
        metagroup_path = _metagroup_path_for_add(spec, args)
        metainfo = {
            m.type: getattr(args, f"metainfo__{m.type}")
            for m in spec.metainfo
            if getattr(args, f"metainfo__{m.type}") is not None
        }
        content = {
            block: getattr(args, f"content__{block}")
            for block in spec.user_content_blocks
            if block != "Description" and getattr(args, f"content__{block}")
        }
        return store.add(
            metagroup_path=metagroup_path, name=args.name, description=args.description,
            content=content, metainfo=metainfo, object_id=args.object_id,
            initial_status=args.set_status,
        )

    for depth, level in enumerate(spec.metagroup_levels, start=1):
        if command == f"add-{_flag_name(level.type)}":
            path_segments = args.name.split("/")
            if len(path_segments) != depth:
                raise CliError(
                    f"add-{_flag_name(level.type)} expects a {depth}-segment path "
                    f"(got {len(path_segments)}: {args.name!r})"
                )
            object_type = store.add_metagroup_path(path_segments, abbrev_override=args.abbrev)
            return f"{level.type} {args.name}: {object_type}"

    if command == "set-status":
        return store.set_status(args.id, args.status, message=args.message, force=args.force)

    for metainfo in spec.metainfo:
        if command == f"set-{_flag_name(metainfo.type)}":
            return store.set_metainfo(args.id, metainfo.type, args.value)

    if command == "show":
        record = store.resolve_id(args.id)
        return record

    if command == "reorder":
        return store.reorder(args.id, args.insert_after)

    if command == "show-metagroups":
        return store.metagroup_paths()

    if command == "reindex":
        return store.reindex()

    if command == "history":
        return store.list_all()

    if command == "list":
        records = store.list_all()
        if args.status is not None:
            records = [r for r in records if r.status == args.status]
        return records

    raise CliError(f"unknown command: {command}")


def _reindex_report_dict(report: ReindexReport) -> dict:
    return {
        "directory": str(report.directory),
        "duplicate_numbers": {str(nr): ids for nr, ids in report.duplicate_numbers.items()},
        "removed_tmp_files": list(report.removed_tmp_files),
        "clean": report.is_clean,
    }


def _print_result(spec: ToolSpec, args: argparse.Namespace, result: object) -> None:
    if result is None:
        return

    if isinstance(result, list) and result and isinstance(result[0], ReindexReport):
        if args.json:
            print(json.dumps([_reindex_report_dict(r) for r in result], indent=2))
            return
        for report in result:
            if report.is_clean:
                print(f"{report.directory}: OK")
                continue
            print(f"{report.directory}: inconsistencies found")
            for nr, ids in report.duplicate_numbers.items():
                print(f"  duplicate number {nr:03d}: {', '.join(ids)}")
            for name in report.removed_tmp_files:
                print(f"  removed orphaned tmp file: {name}")
        return

    if args.json:
        if isinstance(result, ObjectRecord):
            print(render.to_json(result))
        elif isinstance(result, list) and (not result or isinstance(result[0], ObjectRecord)):
            print(render.to_json(result))
        else:
            print(result)
        return

    if isinstance(result, ObjectRecord):
        if args.command == "show" and getattr(args, "history", False):
            print(render.short_with_history(result))
        elif args.command == "show":
            print(render.full_display(result, spec))
        else:
            print(render.short_line(result))
    elif isinstance(result, list) and result and isinstance(result[0], ObjectRecord):
        if args.command == "history":
            print(render.combined_history(result))
        else:
            for record in result:
                print(render.short_line(record))
    elif isinstance(result, list):
        for item in result:
            print(item)
    else:
        print(result)


def main(
    spec: ToolSpec,
    argv: list[str],
    *,
    extra_handlers: Optional[dict[str, Handler]] = None,
    configure_parser: Optional[Callable[[argparse.ArgumentParser, "argparse._SubParsersAction"], None]] = None,
) -> int:
    if extra_handlers is None:
        extra_handlers = {}
    parser, subparsers = build_parser(spec)
    if configure_parser is not None:
        configure_parser(parser, subparsers)

    args = parser.parse_args(argv)

    try:
        store = Store(spec=spec, root=Path(args.root))
        result = dispatch(spec, store, args, extra_handlers)
    except (StoreError, CliError, DeferredOperationError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print_result(spec, args, result)
    return 0
