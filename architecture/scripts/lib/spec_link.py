"""Shared linkage between adrctl and specctl (design-adrctl.md, "Metainfo";
design-specctl.md, "ADR Linkage"): keeps a specctl Section's `adr` field in
sync with the adrctl ADR that governs it, via the ADR's `spec-ref`
Metainfo field. Used by both adrctl.py and specctl.py directly -- neither
CLI script imports the other (architecture/scripts/CLAUDE.md).

v1 scope: `spec-ref` is single-valued (one ADR names at most one governed
Section), not repeatable -- design-decisions.md, "Amendments", records why
the general Metainfo mechanism's single-valued shape was kept rather than
generalized for this one field.
"""

from __future__ import annotations

from pathlib import Path

from lib.spec_store import SpecStore, SpecStoreError


class SpecLinkError(Exception):
    pass


def propagate(root: Path, spec_ref: str, adr_id: str, *, message: str = "") -> None:
    """Update the specctl Section named by `spec_ref` so its `adr` field
    points at `adr_id`, logging an `M` History entry there (design-specctl.md,
    "History"). `root` must be the *same*, unresolved --root value the
    triggering adrctl invocation itself received -- not adrctl's own
    resolved store path -- so SpecStore can independently resolve its own
    target within the directory shared by both tools (design.md, "File and
    Directory Parameters"); passing adrctl's own resolved directory here
    would hit the documented "pointed at another tool's own directory" gap.
    A `spec_ref` naming a Section that doesn't exist raises SpecLinkError,
    aborting the triggering adrctl operation (design-adrctl.md, "Metainfo")."""
    try:
        store = SpecStore(root=Path(root))
        store.receive_adr_link(spec_ref, adr_id, message=message)
    except SpecStoreError as exc:
        raise SpecLinkError(f"spec-ref {spec_ref!r}: {exc}") from exc
