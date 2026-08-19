"""Directory-mode index files (design.md, "Index Files").

Two files per metagroup-path directory, kept strictly separate:

- `.index.md`: human-maintainable, holds the Object Type abbreviation for
  that path segment. Write-once/stable -- never overwritten automatically
  once set, except by an explicit user edit or an explicit --abbrev
  override at creation time.
- `.index.json`: a pure performance cache, indexed by Object ID, listing
  only the direct children of that directory. Rebuildable at any time from
  the object files via `reindex`, which never touches `.index.md`.

Single-file mode has no equivalent here -- see the `## Metagroups` section
handled in lib/metagroup.py instead.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lib.atomicio import atomic_write_text
from lib.model import MetainfoEntry, ObjectRecord

INDEX_MD_NAME = ".index.md"
INDEX_JSON_NAME = ".index.json"

_ABBREV_LINE_PREFIX = "abbrev: "


class IndexError_(Exception):
    """Named to avoid shadowing the builtin IndexError."""


# --- .index.md ---------------------------------------------------------


def read_abbrev(directory: Path) -> Optional[str]:
    path = directory / INDEX_MD_NAME
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(_ABBREV_LINE_PREFIX):
            return line[len(_ABBREV_LINE_PREFIX):].strip()
    return None


def write_abbrev(directory: Path, abbrev: str) -> None:
    """Write-once: refuses to overwrite an already-recorded abbreviation."""
    existing = read_abbrev(directory)
    if existing is not None and existing != abbrev:
        raise IndexError_(
            f"{INDEX_MD_NAME} in {directory} already records abbrev {existing!r}; "
            f"refusing to overwrite with {abbrev!r}"
        )
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_text(directory / INDEX_MD_NAME, f"{_ABBREV_LINE_PREFIX}{abbrev}\n")


# --- .index.json --------------------------------------------------------


@dataclass
class IndexEntry:
    object_id: str
    nr: int
    type: str
    name: str
    status: str
    file: str
    meta: dict = field(default_factory=dict)


def read_index_json(directory: Path) -> dict[str, IndexEntry]:
    path = directory / INDEX_JSON_NAME
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = {}
    for object_id, fields in data.get("objects", {}).items():
        entries[object_id] = IndexEntry(
            object_id=object_id,
            nr=fields["nr"],
            type=fields["type"],
            name=fields["name"],
            status=fields["status"],
            file=fields["file"],
            meta=fields.get("meta", {}),
        )
    return entries


def write_index_json(directory: Path, entries: dict[str, IndexEntry]) -> None:
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "objects": {
            object_id: {
                "nr": entry.nr,
                "type": entry.type,
                "name": entry.name,
                "status": entry.status,
                "file": entry.file,
                "meta": entry.meta,
            }
            for object_id, entry in entries.items()
        },
    }
    atomic_write_text(directory / INDEX_JSON_NAME, json.dumps(payload, indent=2) + "\n")


def index_entry_for(record: ObjectRecord, file_name: str) -> IndexEntry:
    return IndexEntry(
        object_id=record.object_id,
        nr=record.number,
        type=record.object_type,
        name=record.name,
        status=record.status,
        file=file_name,
        meta={entry.type: entry.value for entry in record.metainfo},
    )


def rebuild_index_json(directory: Path, records: list[tuple[ObjectRecord, str]]) -> dict[str, IndexEntry]:
    """Rebuild the direct-children cache from (record, file_name) pairs and
    write it out. Never touches .index.md."""
    entries = {record.object_id: index_entry_for(record, file_name) for record, file_name in records}
    write_index_json(directory, entries)
    return entries
