"""Human-readable and JSON rendering of ObjectRecord (design.md, "Operations":
short/full/short+history display, and the generic combined `history` overview)."""

from __future__ import annotations

import json

from lib.history import HistoryEntry, format_entry
from lib.model import ObjectRecord
from lib.toolspec import ToolSpec


def short_line(record: ObjectRecord) -> str:
    return f"{record.status} {record.signature}"


def full_display(record: ObjectRecord, spec: ToolSpec) -> str:
    lines = [short_line(record), "", f"ID: {record.object_id}"]
    lines.append(f"Metagroup: {'/'.join(record.metagroup_levels)}")
    for entry in record.metainfo:
        lines.append(f"{entry.type}: {entry.value}")

    description = record.content.get("Description", "")
    lines += ["", description] if description else [""]

    for block_name in spec.user_content_blocks:
        if block_name == "Description":
            continue
        content = record.content.get(block_name, "")
        if content:
            lines += ["", f"{block_name}:", content]

    return "\n".join(lines)


def short_with_history(record: ObjectRecord) -> str:
    lines = [short_line(record)]
    if record.history:
        lines += ["", "\n".join(format_entry(entry) for entry in record.history)]
    return "\n".join(lines)


def combined_history(records: list[ObjectRecord]) -> str:
    """The generic `history` command: every object's History entries, merged
    and sorted newest-first, each line prefixed with its object's Signature."""
    entries: list[tuple[str, ObjectRecord, HistoryEntry]] = [
        (entry.timestamp, record, entry) for record in records for entry in record.history
    ]
    entries.sort(key=lambda item: item[0], reverse=True)
    return "\n".join(f"{record.signature}: {format_entry(entry)}" for _ts, record, entry in entries)


def to_json_dict(record: ObjectRecord) -> dict:
    return {
        "id": record.object_id,
        "type": record.object_type,
        "number": record.number,
        "name": record.name,
        "status": record.status,
        "signature": record.signature,
        "metagroup": list(record.metagroup_levels),
        "metainfo": {entry.type: entry.value for entry in record.metainfo},
        "content": dict(record.content),
        "history": [
            {
                "timestamp": entry.timestamp,
                "prefix": entry.prefix,
                "old_status": entry.old_status,
                "new_status": entry.new_status,
                "message": entry.message,
            }
            for entry in record.history
        ],
    }


def to_json(records: ObjectRecord | list[ObjectRecord]) -> str:
    if isinstance(records, list):
        payload = [to_json_dict(record) for record in records]
    else:
        payload = to_json_dict(records)
    return json.dumps(payload, indent=2)
