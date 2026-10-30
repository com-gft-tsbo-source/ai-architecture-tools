"""Guard violations raised by a ToolSpec's sequence/metainfo guards and by
the review-protecting parts of lib/taskctl_spec.py's transition validator
(design-taskctl.md, "Guards"; design-decisions.md, "Amendments (2026-10-30,
taskctl guards + --user-approved)").

A guard rejects an operation an agent must not perform on its own: one that
skips past an unresolved earlier Task, or one that completes or bypasses a
user review. Every guarded operation stays possible when the user asked for
it -- the CLI's `--user-approved <text>` lifts the guard and records <text>
in the History (lib/store.py's `approval_message`).

Subclasses ValueError so every existing `except ValueError` path still
treats it as an ordinary rejection; lib/cliapp.py additionally catches it
first to emit the machine-readable `reason` under --json.
"""

from __future__ import annotations

from typing import Optional

SEQUENCE_BLOCKED = "sequence_blocked"
APPROVAL_REQUIRED = "approval_required"

APPROVAL_PREFIX = "USER-APPROVED: "
APPROVAL_HINT = 'ask the user; rerun with --user-approved "<their instruction>" only if they say so'


class GuardViolation(ValueError):
    def __init__(self, reason: str, message: str, *, blocking_task: Optional[str] = None) -> None:
        super().__init__(message)
        self.reason = reason
        self.blocking_task = blocking_task

    def to_dict(self) -> dict:
        result = {"reason": self.reason, "message": str(self)}
        if self.blocking_task is not None:
            result["blocking_task"] = self.blocking_task
        return result


def approval_message(approval: Optional[str], message: str) -> str:
    """History message for an operation lifted by --user-approved: the
    approval as first line, the caller's own message (if any) after it --
    History's grammar (lib/history.py) allows nothing after the header's
    transition except the message itself, so the marker lives there."""
    if not approval:
        return message
    marker = f"{APPROVAL_PREFIX}{approval}"
    return f"{marker}\n{message}" if message else marker
