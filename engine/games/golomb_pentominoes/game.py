"""Pentominoes — Solomon W. Golomb's two-player placement game (mid-1950s).

Twelve pentominoes and an 8x8 board. Players alternate placing pieces on the
board, covering whole squares and without overlap. The player who cannot make a
move loses. (Rules verbatim from Orman 1996; see rules.md.)

The twelve pieces form a SINGLE SHARED POOL — each piece is used at most once in
the game, by EITHER player. There is no set per player. Both players therefore
always face the same set of legal moves, which makes Pentominoes an *impartial*
game (like Cram, unlike Domineering).

The pieces are the twelve FREE pentominoes: rotations AND reflections of a piece
are the same piece (one-sided pentominoes would number 18, fixed ones 63). They
are generated programmatically here and labelled with Golomb's conventional
letters F, I, L, N, P, T, U, V, W, X, Y, Z (mnemonic: "FILiPiNo" + the end of the
alphabet TUVWXYZ).

Correctness anchor (Orman 1996) — see selftest.py:
  * exactly **2308** legal opening moves, **296** modulo the 8 board symmetries;
  * replies to an opening range from **1181** (the most restrictive move, a long
    "L") to about 2000 (we count 1974);
  * the second-most-restrictive piece is the "N" at **1197** replies.

Known result: Pentominoes is a FIRST-PLAYER WIN (Orman 1996, ~22 billion
positions, independently verified by Richard Schroeppel). We do not re-solve it.

Moves use the palette primitive: "KEY:o@c,r" — piece KEY, orientation index o,
anchored at cell c,r. Orientations are normalised so the anchor is always the
bottom-most, then left-most cell the piece COVERS, so the cell you click is
always part of the piece you place.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

W = H = 8

# The twelve free pentominoes in Golomb's conventional lettering. Drawn as ASCII
# art with row 0 at the TOP (so these read the right way up in source); `_parse`
# flips them into engine cell coords, where +r goes UP the board.
#
# Verified against the standard naming figure (Wikimedia Commons, "Pentomino
# Naming Conventions.svg", the Golomb set) and re-derived programmatically: the
# canonical forms of these twelve are exactly the twelve free pentominoes that
# `selftest.py` grows from scratch.
TEMPLATES = {
    "F": [".XX", "XX.", ".X."],
    "I": ["X", "X", "X", "X", "X"],
    "L": ["X.", "X.", "X.", "XX"],
    "N": [".X", ".X", "XX", "X."],
    "P": ["XX", "XX", "X."],
    "T": ["XXX", ".X.", ".X."],
    "U": ["X.X", "XXX"],
    "V": ["X..", "X..", "XXX"],
    "W": ["X..", "XX.", ".XX"],
    "X": [".X.", "XXX", ".X."],
    "Y": [".X", "XX", ".X", ".X"],
    "Z": ["XX.", ".X.", ".XX"],
}

# Human-readable tooltips for the palette chips.
LABELS = {
    "F": "F pentomino", "I": "I pentomino (straight)", "L": "L pentomino",
    "N": "N pentomino", "P": "P pentomino", "T": "T pentomino",
    "U": "U pentomino", "V": "V pentomino", "W": "W pentomino",
    "X": "X pentomino (plus)", "Y": "Y pentomino", "Z": "Z pentomino",
}

# Fixed piece order — the palette tray reads F I L N P T U V W X Y Z.
ORDER = "FILNPTUVWXYZ"


def _parse(rows):
    """ASCII art (row 0 = TOP) -> [(c, r)] cells with r increasing UPWARD."""
    h = len(rows)
    return [(c, h - 1 - r)
            for r, row in enumerate(rows)
            for c, ch in enumerate(row) if ch == "X"]


def _transforms(cells):
    """The 8 symmetries of the square: 4 rotations x optional reflection."""
    out, cur = [], list(cells)
    for flip in (False, True):
        c0 = [(-c, r) for c, r in cur] if flip else list(cur)
        for _ in range(4):
            c0 = [(r, -c) for c, r in c0]          # rotate 90 degrees
            out.append(list(c0))
    return out


def _normalize(cells):
    """Translate so the ANCHOR sits at (0,0).

    The anchor is the bottom-most, then left-most cell the piece COVERS — so
    (0,0) is always part of the tile and the cell the player clicks is always
    one the piece lands on. (dr is therefore never negative; dc may be.)
    """
    ac, ar = min(cells, key=lambda t: (t[1], t[0]))
    return tuple(sorted((c - ac, r - ar) for c, r in cells))


def _orients(cells):
    """Every DISTINCT orientation, reflections included (free pentominoes)."""
    seen, out = set(), []
    for t in _transforms(cells):
        n = _normalize(t)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


# key -> list of orientations, each a tuple of (dc, dr) offsets from the anchor.
ORIENTS = {k: _orients(_parse(TEMPLATES[k])) for k in ORDER}
# The twelve free pentominoes, all distinct — a guard on the table above.
assert len(ORIENTS) == 12, f"expected 12 pentominoes, got {len(ORIENTS)}"
assert all(len(o) == 5 for os in ORIENTS.values() for o in os), "a piece is not a 5-omino"
assert len({min(os) for os in ORIENTS.values()}) == 12, "pentominoes are not distinct"
# 63 fixed pentominoes in total (the standard count).
assert sum(len(o) for o in ORIENTS.values()) == 63, "not 63 fixed pentominoes"

# Precomputed placements: key -> list of (orientation index, anchor, cells).
PLACEMENTS = {}
for _k in ORDER:
    _lst = []
    for _oi, _o in enumerate(ORIENTS[_k]):
        for _r in range(H):
            for _c in range(W):
                _cells = tuple((_c + dc, _r + dr) for dc, dr in _o)
                if all(0 <= x < W and 0 <= y < H for x, y in _cells):
                    _lst.append((_oi, (_c, _r), _cells))
    PLACEMENTS[_k] = _lst
# Orman 1996: "At the start of the game, there are 2308 possible moves".
assert sum(len(v) for v in PLACEMENTS.values()) == 2308, "opening move count != 2308"


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class PentState:
    board: dict = field(default_factory=dict)    # (c, r) -> owner (the placer)
    used: frozenset = frozenset()                # piece keys already played, by EITHER player
    to_move: int = 0
    last: tuple = ()                             # cells covered by the last piece


class GolombPentominoes(Game):
    name = "Pentominoes"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> PentState:
        return PentState()

    def current_player(self, s: PentState) -> int:
        return s.to_move

    def _fits(self, s: PentState, cells) -> bool:
        return all(0 <= x < W and 0 <= y < H and (x, y) not in s.board for x, y in cells)

    def legal_moves(self, s: PentState) -> list[str]:
        """Every placement of every UNUSED piece on empty cells.

        The pool is shared, so this does not depend on who is to move — both
        players always have exactly the same options (the game is impartial).
        """
        moves = []
        board = s.board
        for k in ORDER:
            if k in s.used:
                continue
            for oi, (c, r), cells in PLACEMENTS[k]:
                if not any(x in board for x in cells):
                    moves.append(f"{k}:{oi}@{c},{r}")
        return moves

    def _decode(self, move: str):
        """'KEY:o@c,r' -> (key, orientation index, anchor). Raises on junk."""
        try:
            keyo, anchor = move.split("@")
            key, oi = keyo.split(":")
            return key, int(oi), _cell(anchor)
        except ValueError:
            raise ValueError(f"malformed move: {move}")

    def _covered(self, key, oi, anchor):
        c, r = anchor
        return tuple((c + dc, r + dr) for dc, dr in ORIENTS[key][oi])

    def apply_move(self, s: PentState, move: str, rng=None) -> PentState:
        key, oi, anchor = self._decode(move)
        if key not in ORIENTS:
            raise ValueError(f"no such pentomino: {key}")
        if not 0 <= oi < len(ORIENTS[key]):
            raise ValueError(f"no orientation {oi} for pentomino {key}")
        if key in s.used:
            raise ValueError(f"pentomino {key} has already been played")
        cells = self._covered(key, oi, anchor)
        if not self._fits(s, cells):
            raise ValueError(f"pentomino does not fit on empty board cells: {move}")
        board = dict(s.board)
        for x in cells:
            board[x] = s.to_move
        return PentState(board=board, used=s.used | {key},
                         to_move=1 - s.to_move, last=cells)

    def is_terminal(self, s: PentState) -> bool:
        # Bounded by construction: each move consumes one of the 12 pieces.
        return not self.legal_moves(s)

    def returns(self, s: PentState) -> list[float]:
        # Normal play: the player to move cannot move, and so loses. No draws.
        loser = s.to_move
        out = [0.0, 0.0]
        out[1 - loser] = 1.0
        out[loser] = -1.0
        return out

    def serialize(self, s: PentState) -> dict:
        return {
            "board": {f"{c},{r}": v for (c, r), v in s.board.items()},
            "used": sorted(s.used),
            "to_move": s.to_move,
            "last": [f"{c},{r}" for (c, r) in s.last],
        }

    def deserialize(self, d: dict) -> PentState:
        return PentState(
            board={_cell(k): v for k, v in d["board"].items()},
            used=frozenset(d.get("used", ())),
            to_move=d["to_move"],
            last=tuple(_cell(x) for x in d.get("last", [])),
        )

    def describe_move(self, s: PentState, move: str) -> str:
        key, oi, anchor = self._decode(move)
        cells = sorted(self._covered(key, oi, anchor), key=lambda t: (t[1], t[0]))
        at = " ".join(f"{c + 1},{r + 1}" for c, r in cells)
        return f"P{s.to_move + 1} {key} @ {at}"

    def render(self, s: PentState, perspective=None) -> dict:
        # The pool is SHARED — one common set of twelve, not a set per player —
        # so the palette is emitted under the "shared" key rather than per-seat
        # keys. The UI then draws a single "Pool" tray in the mover's colour.
        # This has to be explicit: two separate but identical hands (Blokus Duo
        # at move 1) are byte-identical, so the renderer cannot infer it.
        tiles = [{"key": k, "label": LABELS[k], "orients": [list(map(list, o)) for o in ORIENTS[k]]}
                 for k in ORDER if k not in s.used]
        palette = {"shared": tiles}

        left = len(ORDER) - len(s.used)
        if self.is_terminal(s):
            caption = (f"Player {2 - s.to_move} wins — Player {s.to_move + 1} "
                       f"cannot place a pentomino ({left} left, none fit)")
        else:
            caption = f"Player {s.to_move + 1} to move — {left} pentominoes in the shared pool"
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": [{"cell": f"{c},{r}", "owner": v} for (c, r), v in s.board.items()],
            "highlights": [{"cell": f"{c},{r}", "kind": "last-move"} for c, r in s.last],
            "palette": palette,
            "caption": caption,
        }
