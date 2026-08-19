"""Pure object-numbering logic (design.md, "Numbering"). No filesystem access
-- lib/store.py executes the plans this module produces.

Numbers run from 1 within a metagroup subpath, assigned as max+1 on
creation (never smallest-free-gap). Deleting an object leaves a permanent
gap. Reordering moves an object to a new position among its siblings,
identified as "insert right after sibling number `insert_after`" (0 means
"insert before every sibling"). An existing gap right after `insert_after`
is reused untouched; otherwise the minimal contiguous, gap-free run of
sibling numbers starting there is shifted up by one to make room.
"""

from __future__ import annotations

from dataclasses import dataclass


def next_number(existing_numbers: list[int]) -> int:
    """max+1 of the numbers currently used in a subpath (1 if none)."""
    return max(existing_numbers, default=0) + 1


@dataclass(frozen=True)
class ReorderPlan:
    moving_number_before: int
    moving_number_after: int
    # (old_nr, new_nr) for every OTHER sibling that must be renamed, ordered
    # highest-first so applying them in sequence never collides.
    shifts: tuple[tuple[int, int], ...]

    @property
    def is_noop(self) -> bool:
        return self.moving_number_before == self.moving_number_after and not self.shifts


def plan_reorder(sibling_numbers: list[int], moving_number: int, insert_after: int) -> ReorderPlan:
    siblings = sorted(n for n in sibling_numbers if n != moving_number)

    if insert_after != 0 and insert_after not in siblings:
        raise ValueError(f"insert_after={insert_after} is not an existing sibling number")

    following = [n for n in siblings if n > insert_after]
    if not following:
        new_number = (max(siblings) if siblings else insert_after) + 1
        return ReorderPlan(moving_number, new_number, ())

    target_slot = insert_after + 1
    if following[0] != target_slot:
        return ReorderPlan(moving_number, target_slot, ())

    run = []
    expected = target_slot
    for n in following:
        if n != expected:
            break
        run.append(n)
        expected += 1

    shifts = tuple((n, n + 1) for n in reversed(run))
    return ReorderPlan(moving_number, target_slot, shifts)
