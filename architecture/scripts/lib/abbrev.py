"""Object Type derivation and collision resolution (design.md, "Object Type").

Pure functions only -- no filesystem access. Callers (lib/metagroup.py) own
persistence of already-assigned abbreviations and pass them in as `known`.
"""

from __future__ import annotations

import re

_SORT_PREFIX_RE = re.compile(r"^\d{3}-")
_TARGET_LENGTH = 6
# 4/5-level widths are specctl's exception (design-specctl.md, "Object Type"):
# width grows with depth instead of staying fixed at 6, since a 5-level path
# could not stay legible otherwise. Every level count's widths still sum to
# the value passed as pad()'s target_length (see natural_object_type/
# derive_object_type below), so this table is the only thing that changes
# per tool -- the derivation/collision algorithm itself stays generic.
_WIDTHS_BY_LEVEL_COUNT = {
    0: (), 1: (6,), 2: (3, 3), 3: (2, 2, 2),
    4: (2, 2, 2, 2), 5: (2, 2, 2, 2, 2),
}
_MAX_EXTRA_WIDTH = 3
_MAX_NUMERIC_SUFFIX = 99


class AbbrevCollisionError(Exception):
    """Raised when no Object Type could be derived without an explicit --abbrev."""


def widths_for_level_count(level_count: int) -> tuple[int, ...]:
    try:
        return _WIDTHS_BY_LEVEL_COUNT[level_count]
    except KeyError:
        raise ValueError(f"unsupported metagroup level count: {level_count}") from None


def widths_target_length(level_count: int) -> int:
    """Total Object Type width for a given level count (sum of its per-level
    widths) -- the target length every pad() call for that level count uses.
    0 levels has no per-level widths to sum (there are no letters to take
    from anywhere), but still pads out to the standard 6-character width
    (design-taskctl.md/design-questctl.md, both "Object Type") -- the same
    padding rule every other level count already gets, just with nothing to
    pad in the first place."""
    if level_count == 0:
        return _TARGET_LENGTH
    return sum(widths_for_level_count(level_count))


def strip_sort_prefix(name: str) -> str:
    """Remove a leading 3-digit zero-padded sort prefix ('<nr>-'), if present."""
    return _SORT_PREFIX_RE.sub("", name, count=1)


def pad(letters: str, target_length: int = _TARGET_LENGTH) -> str:
    """Right-pad with '_' to `target_length` (default 6, the fixed width used
    by every 1-3 level tool). Codes already at or beyond that length (e.g.
    after collision-escalation, or specctl's wider 4/5-level codes) are left
    as-is. Also used to normalize a user-typed Object Type before matching (a
    trailing-'_' omission on the command line is re-padded before comparison)."""
    if len(letters) >= target_length:
        return letters
    return letters + "_" * (target_length - len(letters))


def _join(stripped_names: tuple[str, ...], widths: tuple[int, ...]) -> str:
    return "".join(name[:w] for name, w in zip(stripped_names, widths))


def natural_object_type(level_names: list[str]) -> str:
    """The unresolved, naturally-derived Object Type -- may collide with an
    already-assigned one; use derive_object_type() to get a guaranteed-unique result."""
    stripped = tuple(strip_sort_prefix(n) for n in level_names)
    widths = widths_for_level_count(len(stripped))
    return pad(_join(stripped, widths), widths_target_length(len(stripped)))


def _first_divergent_index(a: str, b: str) -> int | None:
    for index, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            return index
    return None  # one is a prefix of the other, or they are identical


def derive_object_type(
    level_names: list[str],
    known: dict[str, tuple[str, ...]],
    *,
    abbrev: str | None = None,
) -> str:
    """Derive a unique Object Type for a metagroup path.

    `known` maps every already-assigned Object Type to the stripped level
    names (same order/count as `level_names`) that produced it.

    `abbrev`, if given, is used verbatim (padded) -- an explicit override is
    never auto-resolved on collision; the caller must pick a different one.
    """
    if abbrev is not None:
        padded = pad(abbrev, widths_target_length(len(level_names)))
        if padded in known:
            raise AbbrevCollisionError(
                f"explicit --abbrev {abbrev!r} collides with an existing Object Type"
            )
        return padded

    stripped = tuple(strip_sort_prefix(n) for n in level_names)
    widths = widths_for_level_count(len(stripped))
    target_length = widths_target_length(len(stripped))
    candidate = pad(_join(stripped, widths), target_length)
    if candidate not in known:
        return candidate

    colliding = known[candidate]

    # Base resolution: per colliding level, replace the last character of its
    # natural window with the first character where the source names diverge.
    substituted = _substitute_colliding_levels(stripped, colliding, widths)
    if substituted is not None:
        candidate = pad(_join(substituted, widths), target_length)
        if candidate not in known:
            return candidate
    else:
        substituted = stripped

    # Escalate: widen each level's window up to 3 extra characters.
    for extra in range(1, _MAX_EXTRA_WIDTH + 1):
        for level_index in range(len(widths)):
            trial_widths = list(widths)
            trial_widths[level_index] += extra
            trial = pad(_join(stripped, tuple(trial_widths)), target_length)
            if trial not in known:
                return trial

    # Escalate further: numeric suffix on the best base candidate.
    base = pad(_join(substituted, widths), target_length)
    for suffix in range(2, _MAX_NUMERIC_SUFFIX + 1):
        trial = f"{base}-{suffix}"
        if trial not in known:
            return trial

    raise AbbrevCollisionError(
        "could not derive a unique Object Type; supply an explicit --abbrev"
    )


def _substitute_colliding_levels(
    stripped: tuple[str, ...],
    colliding: tuple[str, ...],
    widths: tuple[int, ...],
) -> tuple[str, ...] | None:
    """Return a new tuple of level names with each colliding level's letters
    resolved via the anchor + first-divergent-character rule, or None if no
    level could be resolved this way (e.g. a source name is identical to, or
    a prefix/superset of, the colliding one)."""
    result = list(stripped)
    resolved_any = False
    for level_index, width in enumerate(widths):
        if level_index >= len(colliding):
            continue
        new_part = stripped[level_index][:width]
        old_part = colliding[level_index][:width]
        if new_part != old_part:
            continue  # this level did not collide
        divergent_index = _first_divergent_index(stripped[level_index], colliding[level_index])
        if divergent_index is None or divergent_index >= len(stripped[level_index]):
            continue  # identical/prefix source names -- cannot resolve here
        anchor_len = max(width - 1, 0)
        divergent_char = stripped[level_index][divergent_index]
        result[level_index] = stripped[level_index][:anchor_len] + divergent_char
        resolved_any = True
    return tuple(result) if resolved_any else None
