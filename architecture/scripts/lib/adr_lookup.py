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
from lib.store import Store, StoreError, resolve_root


class AdrLookupError(Exception):
    pass


def check_adr_exists(shared_root: Path, adr_id: str) -> None:
    """Raise AdrLookupError unless an ADR with this ID exists in the adrctl
    store within `shared_root` -- the directory shared by all four tools
    (design.md, "File and Directory Parameters"). Does not check the ADR's
    Status; existence is the "valid" specctl's own spec asks for.

    Two things a plain `Store(...).get(adr_id)` would get wrong for a
    *validating* (as opposed to mutating) call:

    - `Store.__post_init__` unconditionally creates the directory-mode
      target (`mkdir(..., exist_ok=True)`) -- constructing one just to
      validate would leave a fresh, empty `adrs/` behind even when the
      check (or the specctl operation it gates) ultimately fails. Resolved
      by checking existence via `resolve_root` first (pure path logic, no
      filesystem writes) and failing fast, before a `Store` is ever built.
    - `Store.get` takes no lock, so a concurrent adrctl mutation could run
      between this check and the specctl write it gates. Resolved by
      holding the adrctl store's own lock for the duration of the lookup --
      this closes the "no lock at all" gap, but does not make the check
      and the later specctl write atomic as one cross-store transaction;
      that remains explicitly out of scope (design-decisions.md,
      "Amendments": the adrctl <-> specctl link is accepted as
      non-transactional)."""
    shared_root = Path(shared_root)
    spec = build_adrctl_spec()
    resolved_root, mode = resolve_root(shared_root, spec.root_name, spec.default_mode)
    target_exists = resolved_root.is_dir() if mode == "directory" else resolved_root.is_file()
    if not target_exists:
        raise AdrLookupError(f"adr {adr_id!r}: no adrctl store found under {shared_root}")

    store = Store(spec=spec, root=shared_root)
    with store.lock():
        try:
            store.get(adr_id)
        except StoreError as exc:
            raise AdrLookupError(f"adr {adr_id!r}: {exc}") from exc
