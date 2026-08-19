"""Text helpers: Signature escaping and '> '-prefixed User Content blocks."""

from __future__ import annotations

import re

_SIGNATURE_UNSAFE = re.compile(r"[^A-Za-z0-9]")


def escape_signature_text(text: str) -> str:
    """One-way escape for free-text Signature components: every character
    outside [A-Za-z0-9] becomes '_'. Not reversible; Signatures are display-only."""
    return _SIGNATURE_UNSAFE.sub("_", text)


def encode_block(content: str) -> str:
    """Prefix every line of a User Content block with '> ' (bare '>' for blank lines,
    to avoid trailing whitespace)."""
    lines = content.split("\n")
    return "\n".join(f"> {line}" if line else ">" for line in lines)


def decode_block(encoded: str) -> str:
    """Inverse of encode_block."""
    lines = encoded.split("\n")
    decoded = []
    for line in lines:
        if line == ">":
            decoded.append("")
        elif line.startswith("> "):
            decoded.append(line[2:])
        elif line.startswith(">"):
            decoded.append(line[1:])
        else:
            decoded.append(line)
    return "\n".join(decoded)
