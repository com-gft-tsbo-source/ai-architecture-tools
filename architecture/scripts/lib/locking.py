"""Per-invocation file locking (design.md, "Concurrency / Locking").

A lock is held for the duration of a single invocation only, scoped to
exactly the target the tool was invoked on: the single file in single-file
mode, or the root directory in directory mode. A waiting instance retries
for up to `timeout` seconds (default 3 minutes) and then steals the lock
unconditionally -- the timeout is about how long *this* instance is willing
to wait, not the age of the lock it finds. A warning is logged naming the
previous holder's PID and acquisition timestamp.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from lib.atomicio import atomic_write_text

DEFAULT_TIMEOUT = 180.0
_POLL_INTERVAL = 0.2

logger = logging.getLogger("workctl.locking")


def lock_path_for(target: Path) -> Path:
    """Directory targets lock via a '.lock' file inside them; file targets
    lock via a '<file>.lock' sibling."""
    target = Path(target)
    if target.is_dir():
        return target / ".lock"
    return target.with_name(target.name + ".lock")


class FileLock:
    def __init__(self, target: Path, *, timeout: float = DEFAULT_TIMEOUT,
                 poll_interval: float = _POLL_INTERVAL):
        self.target = Path(target)
        self.lock_path = lock_path_for(self.target)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._acquired = False
        self._own_payload: Optional[str] = None

    def acquire(self) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            if self._try_create():
                self._acquired = True
                return
            if time.monotonic() >= deadline:
                self._steal()
                self._acquired = True
                return
            time.sleep(self.poll_interval)

    def release(self) -> None:
        """Remove the lock file, but only if it still holds our own payload --
        if it was stolen from us (we were a slow, not crashed, holder) we must
        not clobber the new legitimate holder's lock."""
        if not self._acquired:
            return
        try:
            current = self.lock_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._acquired = False
            return
        if current == self._own_payload:
            try:
                os.remove(self.lock_path)
            except FileNotFoundError:
                pass
        self._acquired = False

    def __enter__(self) -> "FileLock":
        self.acquire()
        return self

    def __exit__(self, *exc_info) -> None:
        self.release()

    def _try_create(self) -> bool:
        payload = self._payload()
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
        self._own_payload = payload
        return True

    def _steal(self) -> None:
        previous = self._read_previous_holder()
        if previous is not None:
            logger.warning(
                "Stealing lock at %s held by pid=%s since %s",
                self.lock_path, previous.get("pid"), previous.get("acquired"),
            )
        else:
            logger.warning("Stealing lock at %s (previous holder info unreadable)", self.lock_path)
        payload = self._payload()
        atomic_write_text(self.lock_path, payload)
        self._own_payload = payload

    def _read_previous_holder(self) -> Optional[dict]:
        try:
            return json.loads(self.lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _payload() -> str:
        return json.dumps({"pid": os.getpid(), "acquired": datetime.now(timezone.utc).isoformat()})
