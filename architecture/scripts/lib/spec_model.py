"""Core data model for specctl: SpecSection (design-specctl.md).

Unlike lib.model.ObjectRecord, there is no separate metagroup-vs-object
split here: design-specctl.md, "Deviation from the general model" -- every
metagroup-path node *is* the object at that level. `ancestor_levels` holds
this section's ancestors' own "<nr>-<name>" segments (root..parent, same
shape as lib.metagroup's path segments); the section's own `number`/`name`
complete its own trailing path segment (`own_name`).

`level` (1 = Part .. 5 = Point) is stored explicitly rather than derived
from the path length: a branch may skip levels (design-specctl.md,
"Metagroups": "a Chapter may hold Points directly"), so a Point can sit
only two ancestors deep. It defaults to the path depth when not given.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from lib.history import HistoryEntry
from lib.text import escape_signature_text

# One type per Markdown heading depth below the document's '# <title>'
# (design-specctl.md, "Metagroups"): '##' == Part ... '######' == Point.
LEVEL_TYPES = ("Part", "Chapter", "Section", "Subsection", "Point")
MAX_LEVEL = len(LEVEL_TYPES)
HEADING_MARKS = {depth: "#" * (depth + 1) for depth in range(1, MAX_LEVEL + 1)}
STATUS_CODES = ("draft", "stable", "deprecated")
STATUS_INITIAL = "draft"


class SpecModelError(Exception):
    pass


@dataclass
class SpecSection:
    object_id: str
    object_type: str
    number: int
    name: str  # raw heading text, verbatim, unescaped
    status: str
    # Ancestors' own "<nr>-<name>" segments, root..parent. Empty for a
    # level-1 (Part) section.
    ancestor_levels: tuple[str, ...] = ()
    content: dict[str, str] = field(default_factory=dict)  # currently just "Description"
    open_questions: str = ""
    adr: Optional[str] = None
    history: list[HistoryEntry] = field(default_factory=list)
    level: int = 0  # 0 = derive from the path depth

    def __post_init__(self) -> None:
        if self.level == 0:
            self.level = len(self.ancestor_levels) + 1
        if not 1 <= self.level <= MAX_LEVEL:
            raise SpecModelError(
                f"section {self.name!r} has depth {self.level}, "
                f"specctl supports at most {MAX_LEVEL} levels"
            )
        if self.level < len(self.ancestor_levels) + 1:
            raise SpecModelError(
                f"section {self.name!r} at level {self.level} cannot have "
                f"{len(self.ancestor_levels)} ancestor(s)"
            )

    @property
    def level_type(self) -> str:
        return LEVEL_TYPES[self.level - 1]

    @property
    def heading_mark(self) -> str:
        return HEADING_MARKS[self.level]

    @property
    def own_name(self) -> str:
        return f"{self.number:03d}-{self.name}"

    @property
    def path_levels(self) -> tuple[str, ...]:
        """Full own-name path, root..self -- one entry per ancestor plus this
        section's own segment, mirroring lib.metagroup's path_segments shape."""
        return self.ancestor_levels + (self.own_name,)

    @property
    def signature(self) -> str:
        parts = [
            self.object_type,
            f"{self.number:03d}",
            self.object_id,
            escape_signature_text(self.name),
        ]
        return "-".join(parts)

    def description(self) -> str:
        return self.content.get("Description", "")
