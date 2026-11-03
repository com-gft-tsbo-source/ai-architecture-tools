"""CLI-side lookup of one object by ID, Signature or a fragment of it.

Shared by lib/store.py (taskctl, questctl, rulectl, adrctl) and
lib/spec_store.py (specctl) -- design.md, "CLI Contract". Only the CLI layer
resolves loosely (`lib/cliapp.py`, `specctl.py`); the stores' mutating
methods and every internal cross-reference (spec-ref, tasklist export, ...)
keep working with exact raw IDs.

Lookup order, first hit wins:
  1. exact raw ID
  2. exact Signature
  3. `<metagroup-path>/<number>` selector
  4. case-insensitive substring of the Signature -- must be unambiguous

A `list`/`show` output line (`<status> <signature>`) is accepted too: the
status prefix is dropped (a Signature never contains whitespace).
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence, TypeVar

T = TypeVar("T")

_MAX_CANDIDATES_SHOWN = 8


class IdMatchError(Exception):
    """No match, or an ambiguous fragment."""


class NoMatchError(IdMatchError):
    """Nothing matches (as opposed to an ambiguous fragment)."""


def _candidates_text(signatures: Sequence[str]) -> str:
    shown = list(signatures[:_MAX_CANDIDATES_SHOWN])
    if len(signatures) > _MAX_CANDIDATES_SHOWN:
        shown.append(f"... (+{len(signatures) - _MAX_CANDIDATES_SHOWN} more)")
    return ", ".join(shown)


def resolve(
    items: Sequence[T],
    token: str,
    *,
    kind: str,
    object_id: Callable[[T], str],
    signature: Callable[[T], str],
    by_path: Callable[[Sequence[T], str, int], Optional[T]],
) -> T:
    """Return the one item `token` designates.

    `by_path(items, path, number)` implements selector 3 (the path shape
    differs between the generic store and specctl); it returns None for "no
    such item". `kind` ("object"/"section") only words the error messages.
    """
    raw = token.strip()
    if not raw:
        raise IdMatchError(f"empty {kind} selector")
    fields = raw.split()
    # `list` lines read "<status> <signature>": the Signature is the last field.
    forms = [raw] if fields == [raw] else [raw, fields[-1]]

    for form in forms:
        for item in items:
            if object_id(item) == form:
                return item
    for form in forms:
        for item in items:
            if signature(item) == form:
                return item

    for form in forms:
        path_str, sep, nr_str = form.rpartition("/")
        if sep and nr_str.isdigit():
            found = by_path(items, path_str, int(nr_str))
            if found is not None:
                return found

    needle = forms[-1].lower()
    matches = [item for item in items if needle in signature(item).lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise NoMatchError(f"no {kind} matches {token!r}")
    raise IdMatchError(
        f"{token!r} is ambiguous, it matches {len(matches)} {kind}s: "
        + _candidates_text([signature(m) for m in matches])
    )
