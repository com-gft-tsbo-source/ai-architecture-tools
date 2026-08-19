"""Object storage orchestration: mode detection, locking, CRUD, --id
resolution, (directory mode) index maintenance and reindex repair.

Mode detection for a --root that does not exist yet (first invocation): a
path with a file suffix (e.g. "tasks.md") is treated as single-file mode;
anything else is treated as directory mode and created. design.md does not
specify this case explicitly -- this is a documented implementation choice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lib import atomicio, index, locking, metagroup, numbering, objectfile, singlefile
from lib.clock import now_iso
from lib.history import HistoryEntry
from lib.metagroup import MetagroupDeclaration
from lib.model import MetainfoEntry, ObjectRecord, derive_id, validate_free_form_id
from lib.toolspec import ToolSpec

_FILENAME_UNSAFE_RE = re.compile(r"[^a-z0-9]+")


class StoreError(Exception):
    pass


def detect_mode(path: Path) -> str:
    if path.exists():
        return "file" if path.is_file() else "directory"
    return "file" if path.suffix else "directory"


def _slug(name: str) -> str:
    slug = _FILENAME_UNSAFE_RE.sub("-", name.lower()).strip("-")
    return slug or "object"


def object_file_name(record: ObjectRecord) -> str:
    return f"{record.number:03d}-{record.object_type}-{record.object_id}-{_slug(record.name)}.md"


@dataclass(frozen=True)
class ReindexReport:
    directory: Path
    # number -> object IDs sharing it (design.md: reindex should detect and
    # help clean up residual inconsistencies an interrupted multi-file
    # operation, e.g. an aborted reorder cascade, may leave behind).
    duplicate_numbers: dict
    removed_tmp_files: tuple

    @property
    def is_clean(self) -> bool:
        return not self.duplicate_numbers and not self.removed_tmp_files


@dataclass
class Store:
    """A single --root normally maps to one Store. Passing a list of more
    than one root switches to "merged" mode (design.md: "If the tool
    receives multiple files and/or directories ... it operates strictly
    read-only across all of them, merging their information") -- every
    write operation raises StoreError in that mode."""

    spec: ToolSpec
    root: Path | list[Path]
    mode: str = field(init=False)

    def __post_init__(self) -> None:
        roots = [Path(r) for r in self.root] if isinstance(self.root, list) else [Path(self.root)]
        if len(roots) > 1:
            self.mode = "merged"
            self.root = roots
            self._sub_stores = [Store(self.spec, r) for r in roots]
            return
        self.root = roots[0]
        self.mode = detect_mode(self.root)
        if self.mode == "directory":
            self.root.mkdir(parents=True, exist_ok=True)

    def lock(self) -> locking.FileLock:
        return locking.FileLock(self.root)

    def _require_writable(self) -> None:
        if self.mode == "merged":
            raise StoreError("multiple --root values were given; this operation is read-only in that mode")

    # -- metagroup ------------------------------------------------------

    def add_metagroup_path(
        self, path_segments: list[str], *, abbrev_override: Optional[str] = None
    ) -> str:
        """path_segments: given tokens root-to-leaf; every segment except the
        last must resolve to an existing sibling (number, name, or the exact
        '<nr>-<name>' form -- corrections.md). The last segment is the new
        leaf: if it already carries a '<nr>-' prefix it is used verbatim,
        otherwise a sort number is auto-assigned (max+1 among its siblings,
        corrections.md: 'add-phase: Parameter ohne Nummer, Nummer
        automatisch wählen')."""
        self._require_writable()
        with self.lock():
            given_parents, given_leaf = path_segments[:-1], path_segments[-1]
            if self.mode == "directory":
                parent_resolved = self._dir_resolve_path(given_parents)
                sibling_names = metagroup.dir_sibling_names(self.root, parent_resolved)
                leaf_resolved = metagroup.assign_leaf_name(sibling_names, given_leaf)
                full_path = parent_resolved + [leaf_resolved]
                return metagroup.dir_create_path(
                    self.root, full_path,
                    abbrev_override=abbrev_override, object_type_fn=self.spec.object_type_fn,
                )
            declarations, records = self._sf_read()
            parent_resolved = self._sf_resolve_path(declarations, given_parents)
            sibling_names = metagroup.sf_sibling_names(declarations, parent_resolved)
            leaf_resolved = metagroup.assign_leaf_name(sibling_names, given_leaf)
            full_path = parent_resolved + [leaf_resolved]
            level_type = self.spec.metagroup_levels[len(full_path) - 1].type
            declarations, object_type = metagroup.sf_create_path(
                declarations, level_type, full_path,
                abbrev_override=abbrev_override, object_type_fn=self.spec.object_type_fn,
            )
            self._sf_write(declarations, records)
            return object_type

    def metagroup_object_type(self, path_segments: list[str]) -> str:
        if self.mode == "directory":
            return metagroup.dir_object_type_for(self.root, self._dir_resolve_path(path_segments))
        declarations, _records = self._sf_read()
        return metagroup.sf_object_type_for(declarations, self._sf_resolve_path(declarations, path_segments))

    def metagroup_paths(self) -> list[tuple[str, ...]]:
        if self.mode == "merged":
            paths: list[tuple[str, ...]] = []
            for sub in self._sub_stores:
                paths.extend(sub.metagroup_paths())
            return paths
        if self.mode == "directory":
            return list(metagroup.dir_collect_known_types(self.root).values())
        declarations, _records = self._sf_read()
        return [tuple(d.path.split("/")) for d in declarations]

    def resolve_metagroup_path(self, given_path: list[str]) -> list[str]:
        """Resolve every segment of a user-given path against existing
        siblings (number, name, or exact '<nr>-<name>' form)."""
        if self.mode == "directory":
            return self._dir_resolve_path(given_path)
        declarations, _records = self._sf_read()
        return self._sf_resolve_path(declarations, given_path)

    def _dir_resolve_path(self, given_segments: list[str]) -> list[str]:
        resolved: list[str] = []
        for given in given_segments:
            siblings = metagroup.dir_sibling_names(self.root, resolved)
            resolved.append(metagroup.resolve_segment(siblings, given))
        return resolved

    def _sf_resolve_path(self, declarations, given_segments: list[str]) -> list[str]:
        resolved: list[str] = []
        for given in given_segments:
            siblings = metagroup.sf_sibling_names(declarations, resolved)
            resolved.append(metagroup.resolve_segment(siblings, given))
        return resolved

    # -- add --------------------------------------------------------------

    def add(
        self,
        *,
        metagroup_path: list[str],
        name: str,
        description: str = "",
        content: Optional[dict[str, str]] = None,
        metainfo: Optional[dict[str, str]] = None,
        object_id: Optional[str] = None,
        initial_status: Optional[str] = None,
    ) -> ObjectRecord:
        self._require_writable()
        content = dict(content or {})
        content.setdefault("Description", description)
        metainfo = metainfo or {}

        with self.lock():
            declarations: list[MetagroupDeclaration] = []
            sf_records: list[ObjectRecord] = []
            if self.mode == "directory":
                metagroup_path = self._dir_resolve_path(metagroup_path)
                object_type = metagroup.dir_object_type_for(self.root, metagroup_path)
                directory = metagroup.level_directory(self.root, metagroup_path)
                sibling_numbers = [record.number for record, _path in self._load_directory(directory)]
            else:
                declarations, sf_records = self._sf_read()
                metagroup_path = self._sf_resolve_path(declarations, metagroup_path)
                object_type = metagroup.sf_object_type_for(declarations, metagroup_path)
                sibling_numbers = [
                    record.number for record in sf_records
                    if list(record.metagroup_levels) == metagroup_path
                ]

            number = numbering.next_number(sibling_numbers)
            status = initial_status if initial_status is not None else self.spec.status.initial
            if status not in self.spec.status.codes:
                raise StoreError(f"invalid status {status!r} for {self.spec.name}")

            if object_id is not None:
                object_id = validate_free_form_id(object_id)
            else:
                canonical = "|".join(
                    [
                        "/".join(metagroup_path),
                        name,
                        content.get("Description", ""),
                        ",".join(f"{k}={v}" for k, v in sorted(metainfo.items())),
                    ]
                )
                object_id = derive_id(canonical)

            record = ObjectRecord(
                object_id=object_id,
                object_type=object_type,
                number=number,
                name=name,
                status=status,
                metagroup_levels=tuple(metagroup_path),
                metainfo=[MetainfoEntry(type=k, value=v) for k, v in metainfo.items()],
                content=content,
                history=[HistoryEntry(timestamp=now_iso(), prefix="M", message="Object created")],
            )

            if self.mode == "directory":
                file_path = directory / object_file_name(record)
                file_path.write_text(objectfile.render_object(record, self.spec), encoding="utf-8")
                self._rebuild_index(directory)
            else:
                sf_records.append(record)
                self._sf_write(declarations, sf_records)
            return record

    # -- read ---------------------------------------------------------------

    def get(self, object_id: str) -> ObjectRecord:
        if self.mode == "merged":
            for sub in self._sub_stores:
                try:
                    return sub.get(object_id)
                except StoreError:
                    continue
            raise StoreError(f"no object with ID {object_id!r}")
        if self.mode == "directory":
            return self._find(object_id)[0]
        return self._sf_find(object_id)[0]

    def list_all(self) -> list[ObjectRecord]:
        if self.mode == "merged":
            records: list[ObjectRecord] = []
            for sub in self._sub_stores:
                records.extend(sub.list_all())
            return records
        if self.mode == "directory":
            return [record for record, _path in self._load_all()]
        _declarations, records = self._sf_read()
        return records

    def resolve_id(self, token: str) -> ObjectRecord:
        """--id selector: (1) Signature match, (2) contains '/' -> metagroup-path/nr, (3) raw ID."""
        records = self.list_all()
        for record in records:
            if record.signature == token:
                return record
        if "/" in token:
            path_str, _, nr_str = token.rpartition("/")
            try:
                nr = int(nr_str)
            except ValueError:
                raise StoreError(f"malformed --id path selector: {token!r}") from None
            path_segments = path_str.split("/")
            for record in records:
                if list(record.metagroup_levels) == path_segments and record.number == nr:
                    return record
            raise StoreError(f"no object at metagroup path {path_str!r} number {nr}")
        for record in records:
            if record.object_id == token:
                return record
        raise StoreError(f"no object matches --id {token!r}")

    # -- status / content mutation ------------------------------------------

    def set_status(
        self, object_id: str, new_status: str, *, message: str = "", force: bool = False
    ) -> ObjectRecord:
        self._require_writable()
        if new_status not in self.spec.status.codes:
            raise StoreError(f"invalid status {new_status!r} for {self.spec.name}")
        with self.lock():
            record, ctx = self._locate(object_id)
            validator = self.spec.status.transition_validator
            if validator is not None:
                validator(record, new_status, message=message, force=force)
            old_status = record.status
            record.status = new_status
            if old_status != new_status:
                record.history.append(
                    HistoryEntry(
                        timestamp=now_iso(), prefix="M",
                        old_status=old_status, new_status=new_status, message=message,
                    )
                )
            elif message:
                record.history.append(HistoryEntry(timestamp=now_iso(), prefix="M", message=message))
            self._persist(record, ctx)
            return record

    def set_metainfo(self, object_id: str, metainfo_type: str, value: str) -> ObjectRecord:
        self._require_writable()
        with self.lock():
            record, ctx = self._locate(object_id)
            record.metainfo = [e for e in record.metainfo if e.type != metainfo_type]
            record.metainfo.append(MetainfoEntry(type=metainfo_type, value=value))
            record.history.append(
                HistoryEntry(timestamp=now_iso(), prefix="M", message=f"{metainfo_type} set to {value}")
            )
            self._persist(record, ctx)
            return record

    def annotate(self, object_id: str, message: str) -> ObjectRecord:
        self._require_writable()
        with self.lock():
            record, ctx = self._locate(object_id)
            record.history.append(
                HistoryEntry(
                    timestamp=now_iso(), prefix="T",
                    old_status=record.status, new_status=record.status, message=message,
                )
            )
            self._persist(record, ctx)
            return record

    # -- reorder --------------------------------------------------------------

    def reorder(self, object_id: str, insert_after: int) -> ObjectRecord:
        """Move an object to a new position among its metagroup siblings,
        right after sibling number `insert_after` (0 = before all siblings).
        Delegates the actual plan (gap reuse vs. cascade) to lib/numbering.py."""
        self._require_writable()
        with self.lock():
            if self.mode == "directory":
                return self._dir_reorder(object_id, insert_after)
            return self._sf_reorder(object_id, insert_after)

    def _dir_reorder(self, object_id: str, insert_after: int) -> ObjectRecord:
        record, path = self._find(object_id)
        directory = path.parent
        siblings = self._load_directory(directory)
        by_number = {r.number: (r, p) for r, p in siblings}

        plan = numbering.plan_reorder([r.number for r, _p in siblings], record.number, insert_after)
        if plan.is_noop:
            return record

        for old_nr, new_nr in plan.shifts:
            other_record, other_path = by_number[old_nr]
            other_record.number = new_nr
            other_record.history.append(
                HistoryEntry(
                    timestamp=now_iso(), prefix="M",
                    message=f"Renumbered {old_nr:03d} -> {new_nr:03d} (reorder)",
                )
            )
            new_path = directory / object_file_name(other_record)
            new_path.write_text(objectfile.render_object(other_record, self.spec), encoding="utf-8")
            if new_path != other_path:
                other_path.unlink()

        record.number = plan.moving_number_after
        record.history.append(
            HistoryEntry(
                timestamp=now_iso(), prefix="M",
                message=f"Reordered to position {plan.moving_number_after:03d}",
            )
        )
        new_path = directory / object_file_name(record)
        new_path.write_text(objectfile.render_object(record, self.spec), encoding="utf-8")
        if new_path != path:
            path.unlink()

        self._rebuild_index(directory)
        return record

    def _sf_reorder(self, object_id: str, insert_after: int) -> ObjectRecord:
        record, declarations, records = self._sf_find(object_id)
        siblings = [r for r in records if list(r.metagroup_levels) == list(record.metagroup_levels)]
        by_number = {r.number: r for r in siblings}

        plan = numbering.plan_reorder([r.number for r in siblings], record.number, insert_after)
        if plan.is_noop:
            return record

        for old_nr, new_nr in plan.shifts:
            other = by_number[old_nr]
            other.number = new_nr
            other.history.append(
                HistoryEntry(
                    timestamp=now_iso(), prefix="M",
                    message=f"Renumbered {old_nr:03d} -> {new_nr:03d} (reorder)",
                )
            )

        record.number = plan.moving_number_after
        record.history.append(
            HistoryEntry(
                timestamp=now_iso(), prefix="M",
                message=f"Reordered to position {plan.moving_number_after:03d}",
            )
        )
        self._sf_write(declarations, records)
        return record

    # -- reindex --------------------------------------------------------------

    def reindex(self) -> list[ReindexReport]:
        """Rebuild every directory's .index.json cache from the object files
        (never touching .index.md), and detect+clean up residual
        inconsistencies an interrupted multi-file operation (e.g. an
        aborted reorder cascade or a stolen lock) may have left behind:
        orphaned .tmp files (removed) and duplicate object numbers within a
        metagroup (reported -- not auto-fixed, since choosing which of two
        colliding objects keeps the number requires human judgment).
        Single-file mode has no separate cache to rebuild (design.md: the
        `## Metagroups` section is that mode's equivalent), so this is a
        no-op there.
        """
        if self.mode != "directory":
            return []
        reports = []
        with self.lock():
            for directory in self._all_metagroup_directories():
                removed_tmp = self._cleanup_orphaned_tmp(directory)
                records = self._load_directory(directory)
                seen: dict[int, str] = {}
                duplicates: dict[int, list[str]] = {}
                for record, _path in records:
                    if record.number in seen:
                        duplicates.setdefault(record.number, [seen[record.number]]).append(record.object_id)
                    else:
                        seen[record.number] = record.object_id
                index.rebuild_index_json(directory, [(r, p.name) for r, p in records])
                reports.append(
                    ReindexReport(
                        directory=directory,
                        duplicate_numbers=duplicates,
                        removed_tmp_files=tuple(removed_tmp),
                    )
                )
        return reports

    def _cleanup_orphaned_tmp(self, directory: Path) -> list[str]:
        removed = []
        for tmp_path in sorted(directory.glob("*.tmp")):
            tmp_path.unlink()
            removed.append(tmp_path.name)
        return removed

    # -- internals: shared record location/persistence -----------------------

    def _locate(self, object_id: str):
        if self.mode == "directory":
            record, path = self._find(object_id)
            return record, path
        record, declarations, records = self._sf_find(object_id)
        return record, (declarations, records)

    def _persist(self, record: ObjectRecord, ctx) -> None:
        if self.mode == "directory":
            path = ctx
            path.write_text(objectfile.render_object(record, self.spec), encoding="utf-8")
            self._rebuild_index(path.parent)
        else:
            declarations, records = ctx
            self._sf_write(declarations, records)

    # -- internals: directory mode --------------------------------------------

    def _find(self, object_id: str) -> tuple[ObjectRecord, Path]:
        for record, path in self._load_all():
            if record.object_id == object_id:
                return record, path
        raise StoreError(f"no object with ID {object_id!r}")

    def _load_directory(self, directory: Path) -> list[tuple[ObjectRecord, Path]]:
        if not directory.is_dir():
            return []
        results = []
        for file_path in sorted(directory.glob("*.md")):
            if file_path.name.startswith("."):
                continue  # e.g. .index.md -- pathlib's glob("*.md") matches dotfiles too
            text = file_path.read_text(encoding="utf-8")
            results.append((objectfile.parse_object(text, self.spec), file_path))
        return results

    def _load_all(self) -> list[tuple[ObjectRecord, Path]]:
        results = []
        for directory in self._all_metagroup_directories():
            results.extend(self._load_directory(directory))
        return results

    def _all_metagroup_directories(self) -> list[Path]:
        directories: list[Path] = []
        if not self.root.is_dir():
            return directories

        def walk(directory: Path) -> None:
            if index.read_abbrev(directory) is not None:
                directories.append(directory)
            for child in sorted((p for p in directory.iterdir() if p.is_dir()), key=lambda p: p.name):
                walk(child)

        walk(self.root)
        return directories

    def _rebuild_index(self, directory: Path) -> None:
        records = self._load_directory(directory)
        index.rebuild_index_json(directory, [(record, path.name) for record, path in records])

    # -- internals: single-file mode ------------------------------------------

    def _sf_read(self) -> tuple[list[MetagroupDeclaration], list[ObjectRecord]]:
        if not self.root.exists():
            return [], []
        text = self.root.read_text(encoding="utf-8")
        return singlefile.parse_single_file(text, self.spec)

    def _sf_write(self, declarations: list[MetagroupDeclaration], records: list[ObjectRecord]) -> None:
        text = singlefile.render_single_file(declarations, records, self.spec)
        atomicio.atomic_write_text(self.root, text)

    def _sf_find(
        self, object_id: str
    ) -> tuple[ObjectRecord, list[MetagroupDeclaration], list[ObjectRecord]]:
        declarations, records = self._sf_read()
        for record in records:
            if record.object_id == object_id:
                return record, declarations, records
        raise StoreError(f"no object with ID {object_id!r}")
