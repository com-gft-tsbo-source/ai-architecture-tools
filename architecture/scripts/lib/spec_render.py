"""Human-readable and JSON rendering of SpecSection for specctl's CLI --
mirrors lib/render.py's shape for the other three tools, even though this
one is specctl-only, so the file layout stays predictable across tools."""

from __future__ import annotations

import json

from lib.history import HistoryEntry, format_entry
from lib.spec_model import SpecSection


def short_line(section: SpecSection) -> str:
    return f"{section.status} {section.signature}"


def full_display(section: SpecSection) -> str:
    lines = [short_line(section), "", f"ID: {section.object_id}"]
    lines.append(f"Level: {section.level_type}")
    lines.append(f"Path: {'/'.join(section.path_levels)}")
    if section.adr:
        lines.append(f"adr: {section.adr}")
    description = section.description()
    lines += ["", description] if description else [""]
    if section.open_questions:
        lines += ["", "Open Questions:", section.open_questions]
    return "\n".join(lines)


def short_with_history(section: SpecSection) -> str:
    lines = [short_line(section)]
    if section.history:
        lines += ["", "\n".join(format_entry(entry) for entry in section.history)]
    return "\n".join(lines)


def combined_history(entries: list[tuple[SpecSection, HistoryEntry]]) -> str:
    return "\n".join(f"{section.signature}: {format_entry(entry)}" for section, entry in entries)


def to_json_dict(section: SpecSection) -> dict:
    return {
        "id": section.object_id,
        "type": section.object_type,
        "number": section.number,
        "name": section.name,
        "status": section.status,
        "signature": section.signature,
        "level": section.level,
        "level_type": section.level_type,
        "path": list(section.path_levels),
        "adr": section.adr,
        "content": dict(section.content),
        "open_questions": section.open_questions,
        "history": [
            {
                "timestamp": entry.timestamp,
                "prefix": entry.prefix,
                "old_status": entry.old_status,
                "new_status": entry.new_status,
                "message": entry.message,
            }
            for entry in section.history
        ],
    }


def to_json(sections: SpecSection | list[SpecSection]) -> str:
    if isinstance(sections, list):
        payload = [to_json_dict(s) for s in sections]
    else:
        payload = to_json_dict(sections)
    return json.dumps(payload, indent=2)
