"""Oxono — Tom Delahaye, Cosmoludo 2024. BGG id 398388.

A double-natured four-in-a-row on a 6x6 board, driven by two SHARED totems
(one marked X, one marked O). Rules implemented from the official Cosmoludo
digital rulebook (undecent.fr/wp-content/uploads/2024/04/
Oxono-digital-rule-book.pdf), cross-checked against BGA's gamehelp:

* Setup: the totems are placed RANDOMLY on the two central dot squares of the
  board — the diagonally-adjacent centre cells (2,2) and (3,3) (per the
  rulebook's setup diagram). Each player holds 16 tokens of their colour:
  8 marked X and 8 marked O. Player 1 (pink in the physical set) starts.
* Turn = two sub-moves by the same player (the platform's multi-move pattern):
  1. MOVE one totem of your choice like a rook — any distance >= 1,
     horizontally or vertically, over EMPTY squares only (it may not pass over
     or land on tokens or the other totem). You may only move a totem whose
     symbol you still hold in reserve.
  2. PLACE one of your tokens of the SAME symbol as the moved totem on an
     empty square orthogonally adjacent to the totem's new position.
* Surrounded totem (special case A): when every existing orthogonal neighbour
  of a totem is occupied (tokens or the other totem — board edges don't
  count), it moves by JUMPING: in each orthogonal direction it may leap the
  contiguous occupied squares and land on the FIRST free square of that row or
  column. (Jumping over the other totem is allowed: the rulebook's case C
  triggers only when *all* squares of both rows are occupied, so any free
  square in the row must be reachable regardless of what sits in between.)
* Enclosed landing (special case B): if the moved totem's new position has no
  free orthogonal neighbour (only possible after a jump/fly — a rook move
  always leaves its path free behind it), the token may be placed on ANY free
  square of the board.
* Fully trapped totem (special case C): if a surrounded totem has no jump
  landing at all (its entire row AND column are occupied), it may FLY to any
  free square of the board; the token then follows the normal adjacent rule
  (or case B if the landing square is itself enclosed).
* Win: placing a token that completes a horizontal or vertical line of 4+
  tokens of your COLOUR (symbols mixed freely) or of one SYMBOL (colours
  mixed freely) wins immediately — the player who PLACES the 4th token of a
  same-symbol line wins it even if the opponent owns more tokens in it. The
  totems never count in an alignment (they block lines instead). Diagonals
  never count.
* Draw: if both players place all 16 of their tokens and no line of 4 exists,
  the game is a draw (honest — 32 tokens on 36 squares leave room for this).

Termination is structural: every turn permanently places one of the 32 tokens,
so a game lasts at most 64 plies (32 turns x 2 sub-moves); no ply cap needed.
A totem move always exists for any symbol you hold (slide, else jump, else
fly — at least 3 squares are always free), so nobody is ever stuck.

Move encoding (prefix-safe two-click):
* totem sub-move: "c1,r1>c2,r2" (totems sit on unique squares, so the source
  cell identifies the totem; jumps and case-C flights use the same encoding);
* token drop: a single cell "c,r" (the symbol is implied — only tokens of the
  moved totem's symbol may be placed this turn).

Seat 0 = pink (moves first), seat 1 = black; on screen they use the platform
seat colours (red / blue). Totems render as neutral green discs marked X / O.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 6
DOTS = ((2, 2), (3, 3))       # the two central dot squares (rulebook diagram)
ORTH = ((1, 0), (-1, 0), (0, 1), (0, -1))
SYMS = ("X", "O")
COLS = "abcdef"
NAMES = ("Red", "Blue")       # platform seat colours (pink / black in the box)
DOT_TINT = "#3d4457"          # subtle slate marking the two dot squares

# neutral (owner-2) green, from web/src/colors.js, for the shared totems
TOTEM_FILL, TOTEM_STROKE = "#3aa84a", "#1c5a26"


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(p) -> str:
    return f"{p[0]},{p[1]}"


def _alg(p) -> str:
    return f"{COLS[p[0]]}{p[1] + 1}"


def _on(c: int, r: int) -> bool:
    return 0 <= c < SIZE and 0 <= r < SIZE


@dataclass
class OxState:
    tokens: dict = field(default_factory=dict)   # (c,r) -> (owner, "X"|"O")
    totems: dict = field(default_factory=dict)   # "X"|"O" -> (c,r)
    reserve: list = field(default_factory=lambda: [{"X": 8, "O": 8},
                                                   {"X": 8, "O": 8}])
    to_move: int = 0
    phase: str = "TOTEM"                         # TOTEM -> DROP -> TOTEM ...
    moved: Optional[str] = None                  # symbol of the totem moved this turn
    winner: Optional[int] = None
    last: list = field(default_factory=list)     # cells to highlight
    ply: int = 0


class Oxono(Game):
    name = "Oxono"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OxState:
        rng = rng or random.Random()
        dots = list(DOTS)
        rng.shuffle(dots)                        # rulebook: totems placed randomly
        return OxState(totems={"X": dots[0], "O": dots[1]})

    def current_player(self, s: OxState) -> int:
        return s.to_move

    # -- geometry ---------------------------------------------------------------

    def _occupied(self, s: OxState) -> set:
        occ = set(s.tokens)
        occ.update(s.totems.values())
        return occ

    def _surrounded(self, occ: set, pos) -> bool:
        """All existing orthogonal neighbours occupied (edges don't count)."""
        c, r = pos
        return all((c + dc, r + dr) in occ
                   for dc, dr in ORTH if _on(c + dc, r + dr))

    def _totem_dests(self, s: OxState, sym: str) -> list:
        """Landing squares for the `sym` totem: rook slides over empty squares;
        a surrounded totem instead jumps to the first free square in each
        direction; with no jump landing at all it may fly anywhere free."""
        occ = self._occupied(s)
        c, r = s.totems[sym]
        if not self._surrounded(occ, (c, r)):
            out = []
            for dc, dr in ORTH:
                x, y = c + dc, r + dr
                while _on(x, y) and (x, y) not in occ:
                    out.append((x, y))
                    x, y = x + dc, y + dr
            return out
        # surrounded: jump over the contiguous blockers to the first free square
        out = []
        for dc, dr in ORTH:
            x, y = c + dc, r + dr
            while _on(x, y) and (x, y) in occ:
                x, y = x + dc, y + dr
            if _on(x, y):
                out.append((x, y))
        if out:
            return out
        # case C: whole row + column occupied -> fly to any free square
        return [(x, y) for y in range(SIZE) for x in range(SIZE)
                if (x, y) not in occ]

    def _drop_cells(self, s: OxState) -> list:
        """Empty orthogonal neighbours of the moved totem; if none (enclosed
        landing), any empty square of the board."""
        occ = self._occupied(s)
        c, r = s.totems[s.moved]
        adj = [(c + dc, r + dr) for dc, dr in ORTH
               if _on(c + dc, r + dr) and (c + dc, r + dr) not in occ]
        if adj:
            return sorted(adj)
        return [(x, y) for y in range(SIZE) for x in range(SIZE)
                if (x, y) not in occ]

    # -- move generation ----------------------------------------------------------

    def legal_moves(self, s: OxState) -> list[str]:
        if self.is_terminal(s):
            return []
        if s.phase == "TOTEM":
            moves = []
            for sym in SYMS:
                if s.reserve[s.to_move][sym] <= 0:
                    continue                     # need a matching token in reserve
                frm = _fmt(s.totems[sym])
                moves.extend(f"{frm}>{_fmt(d)}" for d in self._totem_dests(s, sym))
            return moves
        return [_fmt(c) for c in self._drop_cells(s)]

    # -- win detection ------------------------------------------------------------

    def _wins(self, tokens: dict, cell, owner: int, sym: str) -> bool:
        """Does the token just placed on `cell` complete a horizontal or
        vertical run of 4+ same-colour or 4+ same-symbol tokens? Totems are
        not in `tokens`, so they neither count nor extend a run."""
        for pick, want in ((0, owner), (1, sym)):
            for dc, dr in ((1, 0), (0, 1)):
                n = 1
                for sgn in (1, -1):
                    x, y = cell[0] + sgn * dc, cell[1] + sgn * dr
                    while True:
                        t = tokens.get((x, y))
                        if t is None or t[pick] != want:
                            break
                        n += 1
                        x, y = x + sgn * dc, y + sgn * dr
                if n >= 4:
                    return True
        return False

    # -- move application -----------------------------------------------------------

    def apply_move(self, s: OxState, move: str, rng=None) -> OxState:
        if move not in self.legal_moves(s):
            raise ValueError(f"illegal move {move!r}")
        p = s.to_move
        ns = OxState(tokens=dict(s.tokens), totems=dict(s.totems),
                     reserve=[dict(s.reserve[0]), dict(s.reserve[1])],
                     to_move=p, phase=s.phase, moved=s.moved,
                     winner=None, last=list(s.last), ply=s.ply + 1)
        if s.phase == "TOTEM":
            frm, _, to = move.partition(">")
            src, dst = _cell(frm), _cell(to)
            sym = next(k for k, v in ns.totems.items() if v == src)
            ns.totems[sym] = dst
            ns.phase = "DROP"
            ns.moved = sym
            ns.last = [frm, to]
        else:                                    # DROP
            cell = _cell(move)
            ns.tokens[cell] = (p, s.moved)
            ns.reserve[p][s.moved] -= 1
            if self._wins(ns.tokens, cell, p, s.moved):
                ns.winner = p
            ns.phase = "TOTEM"
            ns.moved = None
            ns.to_move = 1 - p
            ns.last = ns.last + [move]
        return ns

    # -- termination / scoring --------------------------------------------------------

    def is_terminal(self, s: OxState) -> bool:
        if s.winner is not None:
            return True
        return (s.phase == "TOTEM"
                and all(n == 0 for h in s.reserve for n in h.values()))

    def returns(self, s: OxState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]                    # honest draw: supplies exhausted
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    # -- serialization ------------------------------------------------------------------

    def serialize(self, s: OxState) -> dict:
        return {
            "tokens": {_fmt(c): [o, k] for c, (o, k) in sorted(s.tokens.items())},
            "totems": {k: _fmt(c) for k, c in sorted(s.totems.items())},
            "reserve": [dict(s.reserve[0]), dict(s.reserve[1])],
            "to_move": s.to_move,
            "phase": s.phase,
            "moved": s.moved,
            "winner": s.winner,
            "last": list(s.last),
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> OxState:
        return OxState(
            tokens={_cell(k): (int(v[0]), str(v[1]))
                    for k, v in d["tokens"].items()},
            totems={k: _cell(v) for k, v in d["totems"].items()},
            reserve=[dict(d["reserve"][0]), dict(d["reserve"][1])],
            to_move=d["to_move"],
            phase=d.get("phase", "TOTEM"),
            moved=d.get("moved"),
            winner=d.get("winner"),
            last=list(d.get("last", [])),
            ply=d.get("ply", 0),
        )

    # -- presentation ----------------------------------------------------------------------

    def describe_move(self, s: OxState, move: str) -> str:
        if s.phase == "TOTEM":
            frm, _, to = move.partition(">")
            src, dst = _cell(frm), _cell(to)
            sym = next(k for k, v in s.totems.items() if v == src)
            return f"{sym}-totem {_alg(src)}-{_alg(dst)}"
        return f"{s.moved}{_alg(_cell(move))}"

    def render(self, s: OxState, perspective=None) -> dict:
        pieces = [{"cell": _fmt(c), "owner": o, "label": k}
                  for c, (o, k) in sorted(s.tokens.items())]
        for sym in SYMS:
            pieces.append({"cell": _fmt(s.totems[sym]), "owner": 2,
                           "label": sym, "fill": TOTEM_FILL,
                           "stroke": TOTEM_STROKE})
        highlights = [{"cell": c, "kind": "last-move"} for c in s.last]
        res = s.reserve
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins — 4 in a row"
        elif self.is_terminal(s):
            caption = "Draw — all 32 tokens placed, no line of 4"
        elif s.phase == "TOTEM":
            can = [sym for sym in SYMS if res[s.to_move][sym] > 0]
            caption = (f"{NAMES[s.to_move]} — move the {' or '.join(can)} totem "
                       f"(rook move; jump/fly if surrounded)")
        else:
            caption = (f"{NAMES[s.to_move]} — place an {s.moved} token "
                       f"next to the {s.moved} totem")
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE,
                      "tints": {_fmt(d): DOT_TINT for d in DOTS}},
            "pieces": pieces,
            "highlights": highlights,
            "reserve": {str(p): {k: n for k, n in sorted(res[p].items()) if n > 0}
                        for p in (0, 1)},
            "caption": caption,
        }
