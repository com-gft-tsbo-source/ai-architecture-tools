"""Declarative per-tool configuration.

Each of taskctl/rulectl/adrctl builds one ToolSpec describing its metagroup
levels, Metainfo types, Status model and User Content blocks. lib/store.py,
lib/objectfile.py, lib/render.py and lib/cliapp.py all consume a ToolSpec
instead of hardcoding tool-specific shape -- this is what keeps the CLI
structure uniform across all three tools without one importing another.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class MetagroupLevelSpec:
    """One level of a tool's metagroup hierarchy, e.g. Phase (taskctl, 1
    level) or Language/Context/Category (rulectl, 3 levels)."""

    type: str


@dataclass(frozen=True)
class MetainfoSpec:
    type: str
    choices: Optional[tuple[str, ...]] = None  # None => free text


@dataclass(frozen=True)
class StatusSpec:
    """A tool's Status model.

    `codes` lists every valid status value (bracket-free for taskctl, e.g.
    " ", "~", "X" -- see lib/objectfile.py's module docstring on why History
    stores raw status tokens rather than the "[ ]"-bracketed display form,
    to avoid double-bracketing the History transition markup). `transition_validator`,
    if given, is called as validator(record, target, *, message, force) -> None
    (the full ObjectRecord, so a validator can inspect Metainfo like
    taskctl's `review`) and must raise ValueError on an invalid transition;
    taskctl is the only tool that supplies one -- rulectl/adrctl leave it
    None, meaning every manual status change is accepted without restriction
    (design.md/design-decisions.md: "no automatic transitions", not "no
    transition validation").
    """

    codes: tuple[str, ...]
    initial: str
    transition_validator: Optional[Callable[..., None]] = None

    def __post_init__(self) -> None:
        if self.initial not in self.codes:
            raise ValueError(f"initial status {self.initial!r} is not among {self.codes!r}")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    metagroup_levels: tuple[MetagroupLevelSpec, ...]
    metainfo: tuple[MetainfoSpec, ...]
    status: StatusSpec
    user_content_blocks: tuple[str, ...]
    # Override for the generic lib.abbrev-based derivation, e.g. taskctl's
    # unpadded-Phase-number Object Type. Receives the object's per-level
    # metagroup names (root-to-leaf) and returns the Object Type string.
    object_type_fn: Optional[Callable[[list[str]], str]] = None
    # Operations listed by the tool's design doc but explicitly deferred
    # (currently: "tasklist" for rulectl/adrctl) -- lib/cliapp.py registers
    # these as stubs that fail with "not yet specified" rather than omitting
    # them, per scripts/workctl/CLAUDE.md's "keep CLI structure uniform" rule.
    deferred_operations: tuple[str, ...] = ()

    def metainfo_names(self) -> tuple[str, ...]:
        return tuple(m.type for m in self.metainfo)

    def metagroup_level_types(self) -> tuple[str, ...]:
        return tuple(level.type for level in self.metagroup_levels)
