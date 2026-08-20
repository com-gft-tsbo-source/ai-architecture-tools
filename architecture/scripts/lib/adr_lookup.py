"""Looks up an ADR by ID in adrctl's store, for specctl's ADR-existence
validation (design-specctl.md, "Status": a "valid adr reference" means the
ADR actually exists, not merely that the field is non-empty).

Kept as its own module rather than folded into lib/spec_link.py: that module
already imports lib/spec_store.py (for the adrctl -> specctl direction), and
lib/spec_store.py needs *this* lookup (the specctl -> adrctl direction) --
importing lib/spec_link.py from lib/spec_store.py would be circular.
"""

from __future__ import annotations

from pathlib import Path

from lib.adrctl_spec import build_spec as build_adrctl_spec
from lib.store import Store, StoreError


class AdrLookupError(Exception):
    pass


def check_adr_exists(shared_root: Path, adr_id: str) -> None:
    """Raise AdrLookupError unless an ADR with this ID exists in the adrctl
    store within `shared_root` -- the directory shared by all four tools
    (design.md, "File and Directory Parameters"). Does not check the ADR's
    Status; existence is the "valid" specctl's own spec asks for."""
    store = Store(spec=build_adrctl_spec(), root=Path(shared_root))
    try:
        store.get(adr_id)
    except StoreError as exc:
        raise AdrLookupError(f"adr {adr_id!r}: {exc}") from exc
