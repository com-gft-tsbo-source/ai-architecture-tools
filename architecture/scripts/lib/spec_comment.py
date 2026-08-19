"""Parse/render the hidden metadata comment specctl attaches to every
Section heading (design-specctl.md, "Object Format").

Grammar (line-based, no real parser needed, mirrors lib.history's style):

    <!-- specctl id=<id> type=<type> nr=<nr> status=<status>[ adr=<id>]
    open-questions:
    > ...
    history:
    - <timestamp>: M ... | ...
    -->

The first line inside the comment is always `specctl <key>=<value> ...`
(id/type/nr/status mandatory, adr optional). `type` is stored rather than
re-derived on every parse because its collision resolution depends on
creation order (design.md, "Object Type") -- the same reason
lib.objectfile stores it as an explicit `## Meta` bullet in the generic
Object Format instead of recomputing it from the metagroup path alone.
`open-questions:` and `history:`
are each optional, fixed-order blocks; every line from one marker up to the
next marker (or the closing `-->`) belongs to that block's body.
`open-questions:` reuses lib.text's '> '-prefixed encoding, kept hidden
inside the comment rather than as visible Markdown so it doesn't need a
second in-band delimiter convention that could collide with a real nested
heading; `history:` reuses lib.history's own self-delimiting grammar
verbatim -- both are the same building blocks the other three tools use for
their own (visible) User Content blocks and History section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from lib.history import HistoryEntry, format_log, parse_history
from lib.text import decode_block, encode_block

_OPEN = "<!-- specctl"
_CLOSE = "-->"
_ATTR_RE = re.compile(r"(\w[\w-]*)=(\S*)")
_OPEN_QUESTIONS_MARKER = "open-questions:"
_HISTORY_MARKER = "history:"


class SpecCommentError(Exception):
    pass


@dataclass
class CommentData:
    object_id: str
    object_type: str
    number: int
    status: str
    adr: Optional[str] = None
    open_questions: str = ""
    history: list[HistoryEntry] = field(default_factory=list)


def render_comment(data: CommentData) -> str:
    attrs = [
        f"id={data.object_id}", f"type={data.object_type}",
        f"nr={data.number:03d}", f"status={data.status}",
    ]
    if data.adr:
        attrs.append(f"adr={data.adr}")
    lines = [f"{_OPEN} {' '.join(attrs)}"]
    if data.open_questions:
        lines.append(_OPEN_QUESTIONS_MARKER)
        lines.append(encode_block(data.open_questions))
    if data.history:
        lines.append(_HISTORY_MARKER)
        lines.append(format_log(data.history))
    if len(lines) == 1:
        return f"{lines[0]} {_CLOSE}"
    return "\n".join(lines) + f"\n{_CLOSE}"


def parse_comment(text: str) -> CommentData:
    """`text` is the full comment, from `<!-- specctl` through `-->`
    inclusive, as a single (possibly multi-line) string."""
    stripped = text.strip()
    if not stripped.startswith(_OPEN):
        raise SpecCommentError(f"comment must start with {_OPEN!r}: {text[:40]!r}")
    if not stripped.endswith(_CLOSE):
        raise SpecCommentError(f"comment must end with {_CLOSE!r}: {text[-40:]!r}")

    inner = stripped[len(_OPEN):-len(_CLOSE)].strip("\n")
    lines = inner.split("\n")

    attr_line = lines[0]
    attrs = dict(_ATTR_RE.findall(attr_line))
    for required in ("id", "type", "nr", "status"):
        if required not in attrs:
            raise SpecCommentError(f"comment missing required {required!r} attribute: {attr_line!r}")
    try:
        number = int(attrs["nr"])
    except ValueError as exc:
        raise SpecCommentError(f"malformed nr in comment: {attrs['nr']!r}") from exc

    open_questions_lines: list[str] = []
    history_lines: list[str] = []
    current: Optional[list[str]] = None
    for line in lines[1:]:
        if line == _OPEN_QUESTIONS_MARKER:
            current = open_questions_lines
            continue
        if line == _HISTORY_MARKER:
            current = history_lines
            continue
        if current is not None:
            current.append(line)
        elif line.strip():
            raise SpecCommentError(f"unexpected line before any block marker: {line!r}")

    open_questions = (
        decode_block("\n".join(open_questions_lines).strip("\n")) if open_questions_lines else ""
    )
    history_text = "\n".join(history_lines).strip("\n")
    history = parse_history(history_text) if history_text else []

    return CommentData(
        object_id=attrs["id"],
        object_type=attrs["type"],
        number=number,
        status=attrs["status"],
        adr=attrs.get("adr") or None,
        open_questions=open_questions,
        history=history,
    )


def extract_comment(lines: list[str]) -> tuple[str, list[str]]:
    """Given the lines directly following a heading, locate the mandatory
    metadata comment (skipping any leading blank lines) and return its full
    text plus the remaining lines after it -- with at most one leading blank
    line of the remainder consumed, matching normal Markdown spacing."""
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or not lines[index].startswith(_OPEN):
        raise SpecCommentError(f"section is missing its {_OPEN!r} metadata comment")

    comment_lines: list[str] = []
    end_index: Optional[int] = None
    for i in range(index, len(lines)):
        comment_lines.append(lines[i])
        if lines[i].rstrip().endswith(_CLOSE):
            end_index = i
            break
    if end_index is None:
        raise SpecCommentError(f"metadata comment starting at line {index} is never closed with {_CLOSE!r}")

    remaining = lines[end_index + 1:]
    if remaining and not remaining[0].strip():
        remaining = remaining[1:]
    return "\n".join(comment_lines), remaining
