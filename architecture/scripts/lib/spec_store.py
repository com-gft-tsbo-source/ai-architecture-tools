"""specctl storage orchestration: locking, CRUD, --id resolution
(design-specctl.md). The adrctl `spec-ref` auto-propagation is still
deferred (design-specctl.md, "ADR Linkage", Implementation status).

Unlike lib/store.py, there is no separate metagroup-declaration layer: a
SpecSection's position *is* its classification (design-specctl.md,
"Deviation from the general model"), so `add` resolves an ancestor path and
creates the leaf object in the same step, and renaming/renumbering a
section must cascade into every descendant's `ancestor_levels` (its own
"<nr>-<name>" segment is embedded there) -- the specctl analogue of
lib/store.py's "changing an object's metagroup re-derives everything
downstream" (design-decisions.md).

Both modes convert to/from the exact same flat, pre-order `list[SpecSection]`
representation (`_read`/`_write`, dispatching on `self.mode`) -- every CRUD
method below (add, set_status, rename, reorder, ...) operates purely on
that in-memory list and knows nothing about single-file vs. directory
storage. Directory mode has no `.index.md`/`.index.json`: unlike the
general model, where those cache an Object Type *shared* by every object
under one metagroup leaf, a specctl Section already carries its own Object
Type directly (design-specctl.md, "Object Format": stored in the metadata
comment, not re-derived) -- a parallel index would just duplicate it.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lib import abbrev, locking, metagroup, numbering
from lib import store as generic_store
from lib.atomicio import atomic_write_text
from lib.clock import now_iso
from lib.history import HistoryEntry
from lib.model import derive_id, validate_free_form_id
from lib.spec_document import (
    SpecDocumentError,
    check_duplicate_ids,
    parse_document,
    parse_section_block,
    render_document,
    render_section_block,
)
from lib.spec_model import LEVEL_TYPES, MAX_LEVEL, STATUS_CODES, STATUS_INITIAL, SpecSection
from lib.text import slugify

_ADR_REQUIRING_STATUSES = ("stable", "deprecated")
_FORWARD_TRANSITIONS = {"draft": "stable", "stable": "deprecated"}
_CONTENT_FILENAME = "_content.md"
_PREAMBLE_FILENAME = "_preamble.md"


class SpecStoreError(Exception):
    pass


def _direct_children_own_names(sections: list[SpecSection], parent_levels: tuple[str, ...]) -> list[str]:
    return [s.own_name for s in sections if s.ancestor_levels == parent_levels]


def _known_object_types(sections: list[SpecSection]) -> dict[str, tuple[str, ...]]:
    return {
        s.object_type: tuple(abbrev.strip_sort_prefix(p) for p in s.path_levels)
        for s in sections
    }


def _insertion_index(sections: list[SpecSection], parent_levels: tuple[str, ...]) -> int:
    """A new child is appended after the entire existing subtree of
    `parent_levels` (self included) -- or at the very end of the document
    for a new root-level Part, since every path trivially starts with the
    empty parent path (design-specctl.md, "Numbering": max+1 among siblings,
    applied to document position instead of a bare counter)."""
    subtree = [
        i for i, s in enumerate(sections) if s.path_levels[: len(parent_levels)] == parent_levels
    ]
    return (max(subtree) + 1) if subtree else len(sections)


def _subtree_end(sections: list[SpecSection], index: int) -> int:
    """End (exclusive) of sections[index]'s own contiguous subtree (itself
    plus every descendant) within the flat, pre-order `sections` list."""
    prefix = sections[index].path_levels
    end = index + 1
    while end < len(sections) and sections[end].path_levels[: len(prefix)] == prefix:
        end += 1
    return end


def _cascade_own_name_change(
    sections: list[SpecSection], index: int, end: int, depth_index: int,
    old_own_name: str, new_own_name: str,
) -> None:
    """After sections[index]'s own `own_name` changed (rename or renumber),
    fix up every descendant's `ancestor_levels` entry at the corresponding
    depth. `end` must be the subtree span captured *before* the change."""
    for j in range(index + 1, end):
        levels = list(sections[j].ancestor_levels)
        if depth_index < len(levels) and levels[depth_index] == old_own_name:
            levels[depth_index] = new_own_name
            sections[j].ancestor_levels = tuple(levels)


@dataclass
class SpecStore:
    """A single --root maps to one SpecStore. Passing a list of more than
    one root switches to "merged" mode, same read-only semantics as
    lib.store.Store (design.md, "File and Directory Parameters")."""

    root: "Path | list[Path]"
    mode: str = field(init=False)

    def __post_init__(self) -> None:
        roots = [Path(r) for r in self.root] if isinstance(self.root, list) else [Path(self.root)]
        if len(roots) > 1:
            self.mode = "merged"
            self.root = roots
            self._sub_stores = [SpecStore(r) for r in roots]
            return
        self.root = roots[0]
        self.mode = generic_store.detect_mode(self.root)
        if self.mode == "directory":
            self.root.mkdir(parents=True, exist_ok=True)

    def lock(self) -> locking.FileLock:
        return locking.FileLock(self.root)

    def _require_writable(self) -> None:
        if self.mode == "merged":
            raise SpecStoreError(
                "multiple --root values were given; this operation is read-only in that mode"
            )

    # -- read/write -----------------------------------------------------

    def _read(self) -> tuple[str, list[SpecSection]]:
        return self._dir_read() if self.mode == "directory" else self._file_read()

    def _write(self, preamble: str, sections: list[SpecSection]) -> None:
        if self.mode == "directory":
            self._dir_write(preamble, sections)
        else:
            self._file_write(preamble, sections)

    def _file_read(self) -> tuple[str, list[SpecSection]]:
        if not self.root.exists():
            return "", []
        text = self.root.read_text(encoding="utf-8")
        try:
            return parse_document(text)
        except SpecDocumentError as exc:
            raise SpecStoreError(str(exc)) from exc

    def _file_write(self, preamble: str, sections: list[SpecSection]) -> None:
        self.root.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self.root, render_document(preamble, sections))

    def _dir_name_for(self, section: SpecSection) -> str:
        return f"{section.number:03d}-{section.object_type}-{section.object_id}-{slugify(section.name)}"

    def _dir_read(self) -> tuple[str, list[SpecSection]]:
        preamble_path = self.root / _PREAMBLE_FILENAME
        preamble = preamble_path.read_text(encoding="utf-8").rstrip("\n") if preamble_path.exists() else ""

        sections: list[SpecSection] = []
        self._dir_read_children(self.root, (), sections)
        try:
            check_duplicate_ids(sections)
        except SpecDocumentError as exc:
            raise SpecStoreError(str(exc)) from exc
        return preamble, sections

    def _dir_read_children(
        self, directory: Path, ancestor_levels: tuple[str, ...], sections: list[SpecSection]
    ) -> None:
        depth = len(ancestor_levels) + 1
        lock_name = locking.lock_path_for(directory).name
        child_dirs = sorted(
            (p for p in directory.iterdir() if p.is_dir() and p.name != lock_name),
            key=lambda p: p.name,
        )
        for child_dir in child_dirs:
            content_path = child_dir / _CONTENT_FILENAME
            if not content_path.exists():
                raise SpecStoreError(f"{child_dir}: missing its {_CONTENT_FILENAME!r} file")
            try:
                section = parse_section_block(
                    content_path.read_text(encoding="utf-8"), depth, ancestor_levels
                )
            except SpecDocumentError as exc:
                raise SpecStoreError(f"{content_path}: {exc}") from exc
            sections.append(section)
            self._dir_read_children(child_dir, ancestor_levels + (section.own_name,), sections)

    def _dir_write(self, preamble: str, sections: list[SpecSection]) -> None:
        # Directory mode has no delete/create diffing -- like single-file
        # mode's whole-file rewrite, every write clears and rebuilds the
        # whole tree from the in-memory `sections` list (locked for the
        # duration, per lib.locking; not atomic across the multiple
        # directories/files involved, same limitation the general model's
        # directory mode already has for a reorder cascade -- design.md,
        # Concurrency / Locking).
        lock_name = locking.lock_path_for(self.root).name
        for entry in self.root.iterdir():
            if entry.name == lock_name:
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

        if preamble.strip():
            atomic_write_text(self.root / _PREAMBLE_FILENAME, preamble.rstrip("\n") + "\n")

        directory_by_levels: dict[tuple[str, ...], Path] = {(): self.root}
        for section in sections:
            parent_dir = directory_by_levels[section.ancestor_levels]
            section_dir = parent_dir / self._dir_name_for(section)
            section_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_text(section_dir / _CONTENT_FILENAME, render_section_block(section) + "\n")
            directory_by_levels[section.path_levels] = section_dir

    def _resolve_ancestor_path(
        self, sections: list[SpecSection], given_segments: list[str]
    ) -> tuple[str, ...]:
        resolved: tuple[str, ...] = ()
        for given in given_segments:
            siblings = _direct_children_own_names(sections, resolved)
            try:
                segment = metagroup.resolve_segment(siblings, given)
            except metagroup.MetagroupError as exc:
                raise SpecStoreError(str(exc)) from exc
            resolved = resolved + (segment,)
        return resolved

    def _find_with_index(self, sections: list[SpecSection], object_id: str) -> tuple[int, SpecSection]:
        for i, s in enumerate(sections):
            if s.object_id == object_id:
                return i, s
        raise SpecStoreError(f"no section with ID {object_id!r}")

    # -- add --------------------------------------------------------------

    def add(
        self,
        level: int,
        path_segments: list[str],
        *,
        description: str = "",
        object_id: Optional[str] = None,
        initial_status: Optional[str] = None,
        abbrev_override: Optional[str] = None,
    ) -> SpecSection:
        self._require_writable()
        if not 1 <= level <= MAX_LEVEL:
            raise SpecStoreError(f"unsupported level {level}; specctl supports 1-{MAX_LEVEL}")
        if len(path_segments) != level:
            raise SpecStoreError(
                f"add-{LEVEL_TYPES[level - 1].lower()} expects a {level}-segment path "
                f"(got {len(path_segments)}: {'/'.join(path_segments)!r})"
            )

        with self.lock():
            preamble, sections = self._read()
            given_parents, given_leaf = path_segments[:-1], path_segments[-1]
            parent_levels = self._resolve_ancestor_path(sections, given_parents)
            siblings = _direct_children_own_names(sections, parent_levels)
            leaf_own_name = metagroup.assign_leaf_name(siblings, given_leaf)
            number_str, _, name = leaf_own_name.partition("-")
            number = int(number_str)

            known = _known_object_types(sections)
            full_path = list(parent_levels) + [leaf_own_name]
            try:
                object_type = abbrev.derive_object_type(full_path, known, abbrev=abbrev_override)
            except abbrev.AbbrevCollisionError as exc:
                raise SpecStoreError(str(exc)) from exc

            status = initial_status if initial_status is not None else STATUS_INITIAL
            if status not in STATUS_CODES:
                raise SpecStoreError(f"invalid status {status!r} for specctl")

            if object_id is not None:
                object_id = validate_free_form_id(object_id)
            else:
                canonical = "|".join(["/".join(full_path), description])
                object_id = derive_id(canonical)

            section = SpecSection(
                object_id=object_id,
                object_type=object_type,
                number=number,
                name=name,
                status=status,
                ancestor_levels=parent_levels,
                content={"Description": description},
                history=[HistoryEntry(timestamp=now_iso(), prefix="M", message="Add")],
            )
            index = _insertion_index(sections, parent_levels)
            sections.insert(index, section)
            self._write(preamble, sections)
            return section

    # -- read ---------------------------------------------------------------

    def list_all(self) -> list[SpecSection]:
        if self.mode == "merged":
            sections: list[SpecSection] = []
            for sub in self._sub_stores:
                sections.extend(sub.list_all())
            return sections
        _preamble, sections = self._read()
        return sections

    def resolve_id(self, token: str) -> SpecSection:
        """--id selector: (1) Signature match, (2) contains '/' -> ancestor-path/nr,
        (3) raw ID (design.md, CLI Contract)."""
        if self.mode == "merged":
            for sub in self._sub_stores:
                try:
                    return sub.resolve_id(token)
                except SpecStoreError:
                    continue
            raise SpecStoreError(f"no section matches --id {token!r}")

        sections = self.list_all()
        for s in sections:
            if s.signature == token:
                return s
        if "/" in token:
            path_str, _, nr_str = token.rpartition("/")
            try:
                nr = int(nr_str)
            except ValueError:
                raise SpecStoreError(f"malformed --id path selector: {token!r}") from None
            path_segments = tuple(path_str.split("/")) if path_str else ()
            for s in sections:
                if s.ancestor_levels == path_segments and s.number == nr:
                    return s
            raise SpecStoreError(f"no section at path {path_str!r} number {nr}")
        for s in sections:
            if s.object_id == token:
                return s
        raise SpecStoreError(f"no section matches --id {token!r}")

    def render_plain(self) -> str:
        """The `render` operation: comment-stripped Markdown, headings and
        content only (design-specctl.md, Operations)."""
        preamble, sections = self._read()
        parts = [preamble] if preamble.strip() else []
        for s in sections:
            lines = [f"{s.heading_mark} {s.name}"]
            description = s.description()
            if description:
                lines += ["", description]
            parts.append("\n".join(lines))
        return "\n\n".join(parts).rstrip("\n") + "\n"

    def combined_history(self) -> list[tuple[SpecSection, HistoryEntry]]:
        entries = [(s, entry) for s in self.list_all() for entry in s.history]
        entries.sort(key=lambda item: item[1].timestamp, reverse=True)
        return entries

    # -- status / content mutation ------------------------------------------

    def set_status(
        self, object_id: str, new_status: str, *, message: str = "", force: bool = False,
        adr: Optional[str] = None,
    ) -> SpecSection:
        self._require_writable()
        if new_status not in STATUS_CODES:
            raise SpecStoreError(f"invalid status {new_status!r} for specctl")
        with self.lock():
            preamble, sections = self._read()
            _index, section = self._find_with_index(sections, object_id)
            old_status = section.status
            self._validate_transition(old_status, new_status, force)

            if new_status in _ADR_REQUIRING_STATUSES:
                effective_adr = adr or section.adr
                if not effective_adr:
                    raise SpecStoreError(
                        f"transitioning to {new_status!r} requires a valid 'adr' reference "
                        f"(supply --adr, or set one first via set-adr)"
                    )
                section.adr = effective_adr

            section.status = new_status
            if old_status != new_status:
                log_message = message
                if section.adr and new_status in _ADR_REQUIRING_STATUSES:
                    log_message = f"{message} adr={section.adr}".strip() if message else f"adr={section.adr}"
                section.history.append(
                    HistoryEntry(
                        timestamp=now_iso(), prefix="M",
                        old_status=old_status, new_status=new_status, message=log_message,
                    )
                )
            elif message:
                section.history.append(HistoryEntry(timestamp=now_iso(), prefix="M", message=message))

            self._write(preamble, sections)
            return section

    def _validate_transition(self, old_status: str, new_status: str, force: bool) -> None:
        if old_status == new_status:
            return
        if _FORWARD_TRANSITIONS.get(old_status) == new_status:
            return
        if not force:
            raise SpecStoreError(
                f"transition {old_status!r} -> {new_status!r} requires --force"
            )

    def set_adr(self, object_id: str, adr_id: str) -> SpecSection:
        """Manual correction of the `adr` Metainfo field (design-specctl.md,
        Operations). Not logged in History: standalone adr changes are not
        Add/Rename/Move/Status, the only categories specctl's History tracks
        -- the authoritative trail lives in the ADR itself."""
        self._require_writable()
        with self.lock():
            preamble, sections = self._read()
            _index, section = self._find_with_index(sections, object_id)
            section.adr = adr_id
            self._write(preamble, sections)
            return section

    def set_description(self, object_id: str, description: str, *, adr: Optional[str] = None) -> SpecSection:
        self._require_writable()
        with self.lock():
            preamble, sections = self._read()
            _index, section = self._find_with_index(sections, object_id)
            if section.status in _ADR_REQUIRING_STATUSES:
                effective_adr = adr or section.adr
                if not effective_adr:
                    raise SpecStoreError(
                        f"content changes to a {section.status!r} section require a valid "
                        f"'adr' reference (supply --adr, or set one first via set-adr)"
                    )
                section.adr = effective_adr
            section.content["Description"] = description
            self._write(preamble, sections)
            return section

    # -- rename / reorder -----------------------------------------------

    def rename(self, object_id: str, new_name: str) -> SpecSection:
        self._require_writable()
        with self.lock():
            preamble, sections = self._read()
            index, section = self._find_with_index(sections, object_id)
            if new_name == section.name:
                return section
            end = _subtree_end(sections, index)
            depth_index = len(section.ancestor_levels)
            old_own_name = section.own_name
            old_name = section.name
            section.name = new_name
            _cascade_own_name_change(sections, index, end, depth_index, old_own_name, section.own_name)
            section.history.append(
                HistoryEntry(timestamp=now_iso(), prefix="M", message=f"Rename from {old_name!r}")
            )
            self._write(preamble, sections)
            return section

    def reorder(self, object_id: str, insert_after: int) -> SpecSection:
        self._require_writable()
        with self.lock():
            preamble, sections = self._read()
            index, section = self._find_with_index(sections, object_id)
            parent_levels = section.ancestor_levels
            child_indices = [i for i, s in enumerate(sections) if s.ancestor_levels == parent_levels]
            sibling_numbers = [sections[i].number for i in child_indices]

            try:
                plan = numbering.plan_reorder(sibling_numbers, section.number, insert_after)
            except ValueError as exc:
                raise SpecStoreError(str(exc)) from exc
            if plan.is_noop:
                return section

            index_by_number = {sections[i].number: i for i in child_indices}
            changes = [(section.number, plan.moving_number_after)] + list(plan.shifts)
            for old_nr, new_nr in changes:
                i = index_by_number[old_nr]
                s = sections[i]
                end = _subtree_end(sections, i)
                depth_index = len(s.ancestor_levels)
                old_own_name = s.own_name
                s.number = new_nr
                _cascade_own_name_change(sections, i, end, depth_index, old_own_name, s.own_name)
                s.history.append(
                    HistoryEntry(timestamp=now_iso(), prefix="M", message=f"Move to position {new_nr}")
                )

            sections = self._reorder_children_blocks(sections, parent_levels)
            self._write(preamble, sections)
            return self._find_with_index(sections, object_id)[1]

    def _reorder_children_blocks(
        self, sections: list[SpecSection], parent_levels: tuple[str, ...]
    ) -> list[SpecSection]:
        child_indices = [i for i, s in enumerate(sections) if s.ancestor_levels == parent_levels]
        if not child_indices:
            return sections
        span_start = child_indices[0]
        span_end = _subtree_end(sections, child_indices[-1])

        blocks: list[list[SpecSection]] = []
        i = span_start
        while i < span_end:
            end = _subtree_end(sections, i)
            blocks.append(sections[i:end])
            i = end
        blocks.sort(key=lambda block: block[0].number)

        new_span = [s for block in blocks for s in block]
        return sections[:span_start] + new_span + sections[span_end:]
