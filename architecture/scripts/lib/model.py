"""Core data model: ObjectRecord and its constituent value types (design.md,
"Managed Objects"). Tool-specific configuration lives in lib/toolspec.py;
this module only knows the generic shape every object shares.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from lib.history import HistoryEntry
from lib.text import escape_signature_text

_ID_LENGTH = 6
_FORBIDDEN_ID_CHAR = "/"


class InvalidObjectIdError(Exception):
    pass


def derive_id(initial_content: str) -> str:
    """6-character hex ID derived from an object's initial content (design.md,
    "Object ID"). Frozen at creation -- later content changes never affect it."""
    digest = hashlib.sha1(initial_content.encode("utf-8")).hexdigest()
    return digest[:_ID_LENGTH]


def validate_free_form_id(object_id: str) -> str:
    """Free-form IDs may be any string except empty or containing '/' (reserved
    for the --id path-selector syntax)."""
    if not object_id:
        raise InvalidObjectIdError("object ID must not be empty")
    if _FORBIDDEN_ID_CHAR in object_id:
        raise InvalidObjectIdError(
            f"free-form object ID must not contain {_FORBIDDEN_ID_CHAR!r}: {object_id!r}"
        )
    return object_id


@dataclass(frozen=True)
class MetagroupLevel:
    """One resolved ancestor level of an object's single metagroup path, as
    recorded in the object's `## Meta` section: (level type, cumulative resolved name)."""

    type: str
    name: str


@dataclass(frozen=True)
class MetainfoEntry:
    type: str
    value: str


@dataclass
class ObjectRecord:
    object_id: str
    object_type: str
    number: int
    name: str
    status: str
    # Own (non-cumulative) name of each metagroup level, in root-to-leaf
    # order, sort prefix included (e.g. ("Python", "001-backend", "002-validation")).
    metagroup_levels: tuple[str, ...]
    metainfo: list[MetainfoEntry] = field(default_factory=list)
    content: dict[str, str] = field(default_factory=dict)  # block name -> raw text
    history: list[HistoryEntry] = field(default_factory=list)
    class_suffix: str | None = None  # optional Signature <class>, tool-defined

    @property
    def signature(self) -> str:
        parts = [
            self.object_type,
            f"{self.number:03d}",
            self.object_id,
            escape_signature_text(self.name),
        ]
        sig = "-".join(parts)
        if self.class_suffix:
            sig += f"-{escape_signature_text(self.class_suffix)}"
        return sig

    def metainfo_value(self, metainfo_type: str) -> str | None:
        for entry in self.metainfo:
            if entry.type == metainfo_type:
                return entry.value
        return None
