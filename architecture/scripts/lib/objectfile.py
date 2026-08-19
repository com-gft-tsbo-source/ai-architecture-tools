"""Parse/render a single object's Markdown text <-> ObjectRecord.

Mode-neutral: directory mode (one object per file) and single-file mode
(several objects per file, separated by '---') use the identical object
template; only lib/store.py's aggregation differs.

Implementation note on the H1 Signature and (in directory mode) the file
name: design.md defines both as one-way, display-only derivations
("reconstructing the original text from a Signature is neither possible nor
required" -- Object Signature). To make an object losslessly parseable from
its own text without relying on either of those, this module stores the
object's authoritative identity fields (ID, Type, Number, Status) as four
additional leading bullets in the `## Meta` section, ahead of the metagroup
ancestor and Metainfo bullets from design.md's Object Format. These four
keys never collide with a real metagroup-level type or Metainfo type name
across any of the three tools (those are always names like "Phase",
"Language", "weight", "tool", ...). The object's Name is *not* duplicated
here -- it is read directly from the `## <name>` heading, which already
carries the raw (unescaped) Name verbatim.
"""

from __future__ import annotations

import re

from lib.history import format_log, parse_history
from lib.model import MetainfoEntry, ObjectRecord
from lib.text import decode_block, encode_block
from lib.toolspec import ToolSpec

_META_FIXED_KEYS = ("ID", "Type", "Number", "Status")
_BULLET_RE = re.compile(r"^- ([^:]+): (.*)$")


class ObjectFileError(Exception):
    pass


def render_object(record: ObjectRecord, spec: ToolSpec) -> str:
    lines: list[str] = [f"# {record.signature}", "", "## Meta", ""]
    lines.append(f"- ID: {record.object_id}")
    lines.append(f"- Type: {record.object_type}")
    lines.append(f"- Number: {record.number:03d}")
    lines.append(f"- Status: {record.status}")

    level_types = spec.metagroup_level_types()
    cumulative = ""
    for level_type, own_name in zip(level_types, record.metagroup_levels):
        cumulative = own_name if not cumulative else f"{cumulative}/{own_name}"
        lines.append(f"- {level_type}: {cumulative}")

    for entry in record.metainfo:
        lines.append(f"- {entry.type}: {entry.value}")

    lines += ["", f"## {record.name}", "", encode_block(record.content.get("Description", ""))]

    for block_name in spec.user_content_blocks:
        if block_name == "Description":
            continue
        lines += ["", f"### {block_name}", "", encode_block(record.content.get(block_name, ""))]

    lines += ["", "## History"]
    if record.history:
        lines += ["", format_log(record.history)]

    return "\n".join(lines) + "\n"


def parse_object(text: str, spec: ToolSpec) -> ObjectRecord:
    lines = text.split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    if not lines or not lines[0].startswith("# "):
        raise ObjectFileError("object text must start with a level-1 heading")

    h2_sections = _parse_h2_sections(lines[1:])

    meta = next((s for s in h2_sections if s[0] == "Meta"), None)
    if meta is None:
        raise ObjectFileError("missing '## Meta' section")
    history_section = next((s for s in h2_sections if s[0] == "History"), None)
    name_sections = [s for s in h2_sections if s[0] not in ("Meta", "History")]
    if len(name_sections) != 1:
        raise ObjectFileError(
            f"expected exactly one object-name section, found {len(name_sections)}"
        )
    name_title, name_body, name_h3s = name_sections[0]

    fixed: dict[str, str] = {}
    metagroup_bullets: list[tuple[str, str]] = []
    metainfo: list[MetainfoEntry] = []
    level_types = set(spec.metagroup_level_types())
    for key, value in _parse_bullets(meta[1]):
        if key in _META_FIXED_KEYS:
            fixed[key] = value
        elif key in level_types:
            metagroup_bullets.append((key, value))
        else:
            metainfo.append(MetainfoEntry(type=key, value=value))
    missing = [k for k in _META_FIXED_KEYS if k not in fixed]
    if missing:
        raise ObjectFileError(f"missing Meta field(s): {', '.join(missing)}")

    metagroup_levels = tuple(value.rsplit("/", 1)[-1] for _key, value in metagroup_bullets)

    content = {"Description": _decode_body(name_body)}
    for h3_title, h3_body in name_h3s:
        content[h3_title] = _decode_body(h3_body)

    history_text = "\n".join(history_section[1]).strip("\n") if history_section else ""
    history = parse_history(history_text) if history_text else []

    try:
        number = int(fixed["Number"])
    except ValueError as exc:
        raise ObjectFileError(f"malformed Number in Meta: {fixed['Number']!r}") from exc

    return ObjectRecord(
        object_id=fixed["ID"],
        object_type=fixed["Type"],
        number=number,
        name=name_title,
        status=fixed["Status"],
        metagroup_levels=metagroup_levels,
        metainfo=metainfo,
        content=content,
        history=history,
    )


def _parse_h2_sections(lines: list[str]) -> list[tuple[str, list[str], list[tuple[str, list[str]]]]]:
    sections: list[list] = []
    current_h2 = None
    current_h3 = None
    for line in lines:
        if line.startswith("## "):
            current_h3 = None
            current_h2 = [line[3:], [], []]
            sections.append(current_h2)
        elif line.startswith("### "):
            if current_h2 is None:
                raise ObjectFileError("level-3 heading before any level-2 heading")
            current_h3 = [line[4:], []]
            current_h2[2].append(current_h3)
        else:
            if current_h3 is not None:
                current_h3[1].append(line)
            elif current_h2 is not None:
                current_h2[1].append(line)
    return [(title, body, [(t, b) for t, b in h3s]) for title, body, h3s in sections]


def _parse_bullets(lines: list[str]) -> list[tuple[str, str]]:
    bullets = []
    for line in lines:
        if not line:
            continue
        match = _BULLET_RE.match(line)
        if not match:
            raise ObjectFileError(f"malformed Meta bullet: {line!r}")
        bullets.append((match.group(1), match.group(2)))
    return bullets


def _decode_body(body_lines: list[str]) -> str:
    text = "\n".join(body_lines).strip("\n")
    return decode_block(text) if text else ""
