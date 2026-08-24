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
    # Fixed store name this tool resolves --root to within the directory
    # shared by all tools (design.md, "File and Directory Parameters"), and
    # its default mode ("file" | "directory") when neither <root_name>.md
    # nor <root_name> exists yet and --root didn't name either explicitly.
    root_name: str
    default_mode: str
    # Override for the generic lib.abbrev-based derivation, e.g. taskctl's
    # unpadded-Phase-number Object Type. Receives the object's per-level
    # metagroup names (root-to-leaf) and returns the Object Type string.
    # Called with [] for a depth-0 object (design.md, "Metagroups": a
    # variable_depth tool's store may use no grouping axis at all) --
    # taskctl's override handles that case too (lib/taskctl_spec.py).
    object_type_fn: Optional[Callable[[list[str]], str]] = None
    # design.md, "Metagroups": a tool may declare an *allowed range* of
    # metagroup depths (0..len(metagroup_levels)) instead of requiring every
    # object at the one fixed, deepest level -- taskctl (0 or 1) and
    # questctl (0, 1, or 2) are the two tools that set this. The actual
    # depth used is a whole-store property, inferred by lib/store.py's
    # Store._established_depth(), never a per-object choice.
    variable_depth: bool = False
    # User Content blocks listed here still render/parse normally (design.md,
    # "Object Format") but get no generic `set-<block>` command and no inline
    # `--<block>` flag on `add` (lib/cliapp.py) -- questctl's Answer is the
    # one user: it must be written only via its own bespoke `answer` command
    # (design-questctl.md, "Operations"), never through the generic content
    # setter, which always logs `M` where `answer` needs `T`.
    no_generic_setter: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.default_mode not in ("file", "directory"):
            raise ValueError(f"default_mode must be 'file' or 'directory', got {self.default_mode!r}")

    def metainfo_names(self) -> tuple[str, ...]:
        return tuple(m.type for m in self.metainfo)

    def metagroup_level_types(self) -> tuple[str, ...]:
        return tuple(level.type for level in self.metagroup_levels)
