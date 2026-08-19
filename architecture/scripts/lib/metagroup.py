"""Metagroup path resolution and creation (design.md, "Metagroups").

A metagroup path is a list of "own names" (each already carrying its
`<nr>-` sort prefix), root-to-leaf, one entry per hierarchy level. Every
directory (directory mode) / declared path (single-file mode) that has ever
been created via `add-<metagroup-type>` is itself a valid, complete
metagroup path that objects may be classified under -- not only the
deepest leaves of the tool's level hierarchy. Each such path gets its own
Object Type, derived via lib/abbrev.py from its own-name chain and checked
for collisions against every other Object Type already assigned anywhere
else in the same store.

Directory mode: the path is a chain of nested directories under the store
root; each such directory carries its own `.index.md` (lib/index.py) with
that path's Object Type.

Single-file mode: paths are declared in the file's `## Metagroups`
bookkeeping section instead (design.md, "Object Format"), one line per
declared path: `- <type>: <own-name/.../own-name> (abbrev: <code>)`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lib import abbrev, index, numbering

METAGROUPS_HEADING = "## Metagroups"
_METAGROUPS_LINE_RE = re.compile(r"^- ([^:]+): (\S+) \(abbrev: (\S+)\)$")


class MetagroupError(Exception):
    pass


# --- segment resolution & auto-numbering (corrections.md) ----------------


def has_sort_prefix(name: str) -> bool:
    return name != abbrev.strip_sort_prefix(name)


def assign_leaf_name(sibling_names: list[str], given_name: str) -> str:
    """Resolve the name for a *new* leaf segment being created via
    `add-<metagroup-type>`: if `given_name` already carries a `<nr>-`
    prefix, use it verbatim (explicit numbering); otherwise auto-assign the
    next number among the given siblings, same `max+1` rule as object
    numbering (corrections.md: 'add-phase: Parameter ohne Nummer, Nummer
    automatisch wählen')."""
    if has_sort_prefix(given_name):
        return given_name
    existing_numbers = [int(name[:3]) for name in sibling_names if has_sort_prefix(name)]
    next_nr = numbering.next_number(existing_numbers)
    return f"{next_nr:03d}-{given_name}"


def resolve_segment(sibling_names: list[str], given: str) -> str:
    """Resolve a user-given reference to an *existing* sibling segment:
    accepts the exact stored '<nr>-<name>' form, a bare number ('1'), or a
    bare name ('Setup') -- corrections.md: 'add ... --phase: Parameter
    Nummer, Name oder Nummer-Name'. Raises MetagroupError if no sibling (or
    more than one) matches."""
    if given in sibling_names:
        return given
    if given.isdigit():
        wanted_nr = int(given)
        matches = [
            name for name in sibling_names
            if has_sort_prefix(name) and int(name[:3]) == wanted_nr
        ]
    else:
        matches = [name for name in sibling_names if abbrev.strip_sort_prefix(name) == given]
    if not matches:
        raise MetagroupError(f"no metagroup segment matches {given!r} among {sorted(sibling_names)!r}")
    if len(matches) > 1:
        raise MetagroupError(f"ambiguous metagroup segment {given!r}: matches {sorted(matches)!r}")
    return matches[0]


def dir_sibling_names(root: Path, parent_segments: list[str]) -> list[str]:
    parent_dir = level_directory(root, parent_segments)
    if not parent_dir.is_dir():
        return []
    return [p.name for p in parent_dir.iterdir() if p.is_dir()]


def sf_sibling_names(declarations: list["MetagroupDeclaration"], parent_segments: list[str]) -> list[str]:
    target_depth = len(parent_segments) + 1
    names = []
    for declaration in declarations:
        parts = declaration.path.split("/")
        if len(parts) == target_depth and parts[:-1] == parent_segments:
            names.append(parts[-1])
    return names


def level_directory(root: Path, path_segments: list[str]) -> Path:
    directory = root
    for segment in path_segments:
        directory = directory / segment
    return directory


# --- directory mode ------------------------------------------------------


def dir_path_exists(root: Path, path_segments: list[str]) -> bool:
    return level_directory(root, path_segments).is_dir()


def dir_collect_known_types(root: Path) -> dict[str, tuple[str, ...]]:
    """Walk the whole tree, collecting every directory's own Object Type
    (from its .index.md) mapped to the own-name path (root-to-leaf, sort
    prefix included) that produced it -- e.g. for `show-metagroups` display.
    Use `_dir_collect_known_types_stripped()` when feeding lib.abbrev's
    `known` parameter, which expects pre-stripped level names."""
    known: dict[str, tuple[str, ...]] = {}
    if not root.is_dir():
        return known

    def walk(directory: Path, path_segments: tuple[str, ...]) -> None:
        this_abbrev = index.read_abbrev(directory)
        if this_abbrev is not None and path_segments:
            known[this_abbrev] = path_segments
        for child in sorted((p for p in directory.iterdir() if p.is_dir()), key=lambda p: p.name):
            walk(child, path_segments + (child.name,))

    walk(root, ())
    return known


def _dir_collect_known_types_stripped(root: Path) -> dict[str, tuple[str, ...]]:
    return {
        abbrev_code: tuple(abbrev.strip_sort_prefix(s) for s in path_segments)
        for abbrev_code, path_segments in dir_collect_known_types(root).items()
    }


def dir_create_path(
    root: Path,
    path_segments: list[str],
    *,
    abbrev_override: Optional[str] = None,
    object_type_fn=None,
) -> str:
    """Create the leaf directory of path_segments (ancestors must already
    exist) and return its Object Type. `object_type_fn`, if given (taskctl's
    unpadded-Phase-number exception, ToolSpec.object_type_fn), replaces the
    generic lib.abbrev-derived scheme entirely -- no collision resolution is
    needed for it, since it is inherently unique by the tool's own numbering."""
    if not path_segments:
        raise MetagroupError("metagroup path must not be empty")
    parent_segments = path_segments[:-1]
    if parent_segments and not dir_path_exists(root, parent_segments):
        raise MetagroupError(f"parent metagroup path does not exist: {'/'.join(parent_segments)}")
    directory = level_directory(root, path_segments)
    if directory.is_dir():
        raise MetagroupError(f"metagroup path already exists: {'/'.join(path_segments)}")

    if object_type_fn is not None:
        object_type = object_type_fn(list(path_segments))
    else:
        known = _dir_collect_known_types_stripped(root)
        object_type = abbrev.derive_object_type(list(path_segments), known, abbrev=abbrev_override)
    directory.mkdir(parents=True)
    index.write_abbrev(directory, object_type)
    return object_type


def dir_object_type_for(root: Path, path_segments: list[str]) -> str:
    directory = level_directory(root, path_segments)
    object_type = index.read_abbrev(directory)
    if object_type is None:
        raise MetagroupError(f"metagroup path does not exist: {'/'.join(path_segments)}")
    return object_type


# --- single-file mode ------------------------------------------------------


@dataclass(frozen=True)
class MetagroupDeclaration:
    level_type: str
    path: str  # slash-joined own-names, root-to-leaf
    abbrev: str


def parse_metagroups_section(body_lines: list[str]) -> list[MetagroupDeclaration]:
    declarations = []
    for line in body_lines:
        if not line.strip():
            continue
        match = _METAGROUPS_LINE_RE.match(line)
        if not match:
            raise MetagroupError(f"malformed Metagroups line: {line!r}")
        declarations.append(
            MetagroupDeclaration(level_type=match.group(1), path=match.group(2), abbrev=match.group(3))
        )
    return declarations


def render_metagroups_section(declarations: list[MetagroupDeclaration]) -> str:
    lines = [METAGROUPS_HEADING, ""]
    for declaration in declarations:
        lines.append(f"- {declaration.level_type}: {declaration.path} (abbrev: {declaration.abbrev})")
    return "\n".join(lines)


def sf_path_exists(declarations: list[MetagroupDeclaration], path_segments: list[str]) -> bool:
    path = "/".join(path_segments)
    return any(d.path == path for d in declarations)


def sf_create_path(
    declarations: list[MetagroupDeclaration],
    level_type: str,
    path_segments: list[str],
    *,
    abbrev_override: Optional[str] = None,
    object_type_fn=None,
) -> tuple[list[MetagroupDeclaration], str]:
    if not path_segments:
        raise MetagroupError("metagroup path must not be empty")
    parent_segments = path_segments[:-1]
    if parent_segments and not sf_path_exists(declarations, parent_segments):
        raise MetagroupError(f"parent metagroup path does not exist: {'/'.join(parent_segments)}")
    if sf_path_exists(declarations, path_segments):
        raise MetagroupError(f"metagroup path already exists: {'/'.join(path_segments)}")

    if object_type_fn is not None:
        object_type = object_type_fn(list(path_segments))
    else:
        known = {
            d.abbrev: tuple(abbrev.strip_sort_prefix(s) for s in d.path.split("/"))
            for d in declarations
        }
        object_type = abbrev.derive_object_type(list(path_segments), known, abbrev=abbrev_override)
    new_declaration = MetagroupDeclaration(
        level_type=level_type, path="/".join(path_segments), abbrev=object_type
    )
    return declarations + [new_declaration], object_type


def sf_object_type_for(declarations: list[MetagroupDeclaration], path_segments: list[str]) -> str:
    path = "/".join(path_segments)
    for declaration in declarations:
        if declaration.path == path:
            return declaration.abbrev
    raise MetagroupError(f"metagroup path does not exist: {path}")
