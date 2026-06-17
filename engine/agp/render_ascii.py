"""Render a RenderSpec to text for the CLI preview.

This is a debugging aid, not the real renderer (that's a Phase-1 web SVG
renderer). It understands the Phase-0 board types: ``square`` and ``hex``.
"""

from __future__ import annotations


def render(spec: dict) -> str:
    board = spec.get("board", {})
    btype = board.get("type")
    pieces = {p["cell"]: p for p in spec.get("pieces", [])}
    caption = spec.get("caption", "")

    if btype == "square":
        out = _square(board, pieces)
    elif btype == "hex":
        out = _hex(board, pieces)
    else:
        out = f"(no ASCII renderer for board type {btype!r})"

    return out + (f"\n{caption}" if caption else "")


_GLYPH = {0: "X", 1: "O"}  # fallback by owner when no label


def _glyph(piece: dict) -> str:
    label = (piece.get("label") or "").strip()
    if label:
        return label[0]
    return _GLYPH.get(piece.get("owner"), "?")


def _square(board: dict, pieces: dict) -> str:
    w, h = board["width"], board["height"]
    rows = []
    for r in range(h):
        cells = [_glyph(pieces[f"{c},{r}"]) if f"{c},{r}" in pieces else "." for c in range(w)]
        rows.append(" ".join(cells))
    return "\n".join(rows)


def _hex(board: dict, pieces: dict) -> str:
    """Indented rows of an axial hexagon (size = cells per side)."""
    size = board["size"]
    coords = [
        (q, r)
        for q in range(-(size - 1), size)
        for r in range(-(size - 1), size)
        if abs(q + r) <= size - 1
    ]
    rows = {}
    for (q, r) in coords:
        rows.setdefault(r, []).append((q, r))
    lines = []
    for r in sorted(rows):
        cells = sorted(rows[r], key=lambda qr: qr[0])
        glyphs = [
            _glyph(pieces[f"{q},{r}"]) if f"{q},{r}" in pieces else "."
            for (q, r) in cells
        ]
        indent = " " * (r + (size - 1))
        lines.append(indent + " ".join(glyphs))
    return "\n".join(lines)
