"""Atomic text file writes: write to a .tmp sibling, then rename into place."""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: os.PathLike | str, content: str, *, encoding: str = "utf-8") -> None:
    path = Path(path)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(content, encoding=encoding)
    os.replace(tmp_path, path)
