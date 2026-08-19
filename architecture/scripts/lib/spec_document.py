"""Whole-document parse/render for specctl's single-file mode
(design-specctl.md, "Object Format").

Walks the Markdown heading structure directly -- '##' through '######' are
Sections at depth 1-5 (design-specctl.md, "Metagroups": Part..Point).
Everything before the first such heading (the document's own '# <title>'
and any preamble) is preserved verbatim and never touched. Ancestry is
tracked with a plain depth-stack as sections are walked top to bottom: a
new heading's ancestors are whatever remains on the stack once entries at
its own depth or deeper are popped -- which is also what naturally rejects
a heading that skips a depth (design-specctl.md: "adding a level 4 heading
requires its enclosing ... objects to already exist").
"""

from __future__ import annotations

import re

from lib.spec_comment import CommentData, extract_comment, parse_comment, render_comment
from lib.spec_model import SpecModelError, SpecSection

_HEADING_RE = re.compile(r"^(#{2,6}) (.+)$")


class SpecDocumentError(Exception):
    pass


def parse_document(text: str) -> tuple[str, list[SpecSection]]:
    lines = text.split("\n")
    first_index = next((i for i, line in enumerate(lines) if _HEADING_RE.match(line)), None)
    if first_index is None:
        return text, []

    preamble = "\n".join(lines[:first_index]).rstrip("\n")
    blocks = _split_into_blocks(lines[first_index:])

    sections: list[SpecSection] = []
    stack: list[SpecSection] = []
    for depth, heading_text, content_lines in blocks:
        while len(stack) >= depth:
            stack.pop()
        if len(stack) != depth - 1:
            raise SpecDocumentError(
                f"heading {heading_text!r} at depth {depth} has no enclosing depth-{depth - 1} heading"
            )

        try:
            comment_text, remaining = extract_comment(content_lines)
            comment = parse_comment(comment_text)
        except Exception as exc:
            raise SpecDocumentError(f"section {heading_text!r}: {exc}") from exc

        description = "\n".join(remaining).strip("\n")
        ancestor_levels = tuple(section.own_name for section in stack)
        try:
            section = SpecSection(
                object_id=comment.object_id,
                object_type=comment.object_type,
                number=comment.number,
                name=heading_text,
                status=comment.status,
                ancestor_levels=ancestor_levels,
                content={"Description": description},
                open_questions=comment.open_questions,
                adr=comment.adr,
                history=comment.history,
            )
        except SpecModelError as exc:
            raise SpecDocumentError(str(exc)) from exc

        sections.append(section)
        stack.append(section)

    _check_duplicate_ids(sections)
    return preamble, sections


def render_document(preamble: str, sections: list[SpecSection]) -> str:
    parts = [preamble] if preamble.strip() else []
    for section in sections:
        parts.append(_render_section_block(section))
    return "\n\n".join(parts).rstrip("\n") + "\n"


def _render_section_block(section: SpecSection) -> str:
    comment = CommentData(
        object_id=section.object_id,
        object_type=section.object_type,
        number=section.number,
        status=section.status,
        adr=section.adr,
        open_questions=section.open_questions,
        history=section.history,
    )
    lines = [f"{section.heading_mark} {section.name}", "", render_comment(comment)]
    description = section.description()
    if description:
        lines += ["", description]
    return "\n".join(lines)


def _split_into_blocks(lines: list[str]) -> list[tuple[int, str, list[str]]]:
    blocks: list[list] = []
    current: list | None = None
    for line in lines:
        match = _HEADING_RE.match(line)
        if match:
            if current is not None:
                blocks.append(current)
            depth = len(match.group(1)) - 1
            current = [depth, match.group(2), []]
        else:
            current[2].append(line)
    if current is not None:
        blocks.append(current)
    return [(depth, text, content) for depth, text, content in blocks]


def _check_duplicate_ids(sections: list[SpecSection]) -> None:
    seen: dict[str, str] = {}
    for section in sections:
        if section.object_id in seen:
            raise SpecDocumentError(
                f"duplicate object ID {section.object_id!r} "
                f"(also used by {seen[section.object_id]!r})"
            )
        seen[section.object_id] = section.name
