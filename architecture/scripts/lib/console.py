"""UTF-8 for stdout/stderr, independent of the platform's locale encoding.

Stores are read and written as UTF-8 (lib/atomicio.py), and their content
contains non-ASCII text (e.g. the History's `→`, German umlauts). Python
encodes a *redirected* stdout/stderr with the locale encoding, on Windows
typically cp1252, so `taskctl render > out.txt` would crash with
UnicodeEncodeError. Every CLI therefore emits UTF-8 (design.md, CLI Contract).
"""

from __future__ import annotations

import sys


def use_utf8_streams() -> None:
    """Switch stdout/stderr to UTF-8. Streams without `reconfigure` (e.g. an
    io.StringIO replacing them in tests) are left untouched."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
