"""Parse/format the History log line grammar shared by all workctl tools.

Grammar (line-based, no real parser needed):
  - A line starting with "- " in column 0 begins a new entry:
        - <timestamp>: <prefix>[ [<old>] -> [<new>]] | <inline message>
    The transition segment is present only when the caller supplies both
    old_status and new_status (not None) for that entry.
  - A line starting with exactly "  > " continues the previous entry's message.
  - Message text is either inline after " | ", or one or more "  > "-prefixed
    continuation lines -- never both. It must not itself contain a line
    starting with "- " in column 0 or with "  > ".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_CONTINUATION_PREFIX = "  > "

_HEADER_RE = re.compile(
    r"^- (?P<ts>\S+): (?P<prefix>[A-Z])"
    r"(?: \[(?P<old>[^\]]*)\] -> \[(?P<new>[^\]]*)\])?"
    r" \|(?: (?P<inline>.*))?$"
)


@dataclass(frozen=True)
class HistoryEntry:
    timestamp: str
    prefix: str
    message: str = ""
    old_status: Optional[str] = None
    new_status: Optional[str] = None

    @property
    def has_transition(self) -> bool:
        return self.old_status is not None or self.new_status is not None


def _validate_message(message: str) -> None:
    for line in message.split("\n"):
        if line.startswith("- ") or line.startswith(_CONTINUATION_PREFIX):
            raise ValueError(
                f"History message must not contain a line starting with '- ' "
                f"or '{_CONTINUATION_PREFIX}': {line!r}"
            )


def format_entry(entry: HistoryEntry) -> str:
    _validate_message(entry.message)
    header = f"- {entry.timestamp}: {entry.prefix}"
    if entry.has_transition:
        header += f" [{entry.old_status or ''}] -> [{entry.new_status or ''}]"
    message_lines = entry.message.split("\n") if entry.message else []
    if len(message_lines) <= 1:
        inline = message_lines[0] if message_lines else ""
        return header + (f" | {inline}" if inline else " |")
    header += " |"
    continuation = "\n".join(f"{_CONTINUATION_PREFIX}{line}" for line in message_lines)
    return header + "\n" + continuation


def format_log(entries: list[HistoryEntry]) -> str:
    return "\n".join(format_entry(entry) for entry in entries)


def parse_history(text: str) -> list[HistoryEntry]:
    entries: list[HistoryEntry] = []
    current: Optional[dict] = None
    current_lines: list[str] = []

    def finalize() -> None:
        if current is None:
            return
        entries.append(
            HistoryEntry(
                timestamp=current["ts"],
                prefix=current["prefix"],
                message="\n".join(current_lines),
                old_status=current.get("old"),
                new_status=current.get("new"),
            )
        )

    for raw_line in text.split("\n"):
        if raw_line == "":
            continue
        match = _HEADER_RE.match(raw_line)
        if match:
            finalize()
            current = match.groupdict()
            inline = current.get("inline")
            current_lines = [inline] if inline else []
        elif raw_line.startswith(_CONTINUATION_PREFIX):
            if current is None:
                raise ValueError(f"Continuation line without a preceding entry: {raw_line!r}")
            current_lines.append(raw_line[len(_CONTINUATION_PREFIX):])
        else:
            raise ValueError(f"Malformed History line: {raw_line!r}")

    finalize()
    return entries
