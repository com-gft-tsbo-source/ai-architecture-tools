"""Whole-file parse/render for single-file mode (design.md, "Object Format",
single-file mode section).

Objects appear one after another in the file, separated by '---' -- only
*between* objects, never leading or trailing. If the file declares
metagroup paths that need to exist ahead of any object, it starts with a
`## Metagroups` bookkeeping section (lib/metagroup.py), directly followed
by the first object's `# <signature>` heading in the *same* leading chunk
(no '---' between the Metagroups section and the first object).
"""

from __future__ import annotations

from lib import metagroup, objectfile
from lib.metagroup import MetagroupDeclaration
from lib.model import ObjectRecord
from lib.toolspec import ToolSpec

_SEPARATOR = "---"


def parse_single_file(text: str, spec: ToolSpec) -> tuple[list[MetagroupDeclaration], list[ObjectRecord]]:
    if not text.strip():
        return [], []

    lines = text.split("\n")
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line == _SEPARATOR:
            chunks.append(current)
            current = []
        else:
            current.append(line)
    chunks.append(current)

    declarations: list[MetagroupDeclaration] = []
    records: list[ObjectRecord] = []

    for chunk_index, chunk_lines in enumerate(chunks):
        if not any(line.strip() for line in chunk_lines):
            continue
        if chunk_index == 0 and chunk_lines[0].rstrip() == metagroup.METAGROUPS_HEADING:
            object_start = next((i for i, l in enumerate(chunk_lines) if l.startswith("# ")), None)
            meta_lines = chunk_lines[1:] if object_start is None else chunk_lines[1:object_start]
            declarations = metagroup.parse_metagroups_section(meta_lines)
            if object_start is None:
                continue
            chunk_lines = chunk_lines[object_start:]
        object_text = "\n".join(chunk_lines).strip("\n")
        if object_text:
            records.append(objectfile.parse_object(object_text, spec))

    return declarations, records


def render_single_file(
    declarations: list[MetagroupDeclaration], records: list[ObjectRecord], spec: ToolSpec
) -> str:
    object_texts = [
        objectfile.render_object(record, spec).strip("\n")
        for record in sorted(records, key=lambda r: (r.metagroup_levels, r.number))
    ]

    if not declarations and not object_texts:
        return ""

    parts: list[str] = []
    if declarations:
        metagroups_text = metagroup.render_metagroups_section(declarations)
        if object_texts:
            parts.append(f"{metagroups_text}\n\n{object_texts[0]}")
            parts.extend(object_texts[1:])
        else:
            parts.append(metagroups_text)
    else:
        parts.extend(object_texts)

    return f"\n\n{_SEPARATOR}\n\n".join(parts) + "\n"
