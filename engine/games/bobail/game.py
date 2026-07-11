"""Bobail — traditional two-player game from the Morbihan region of France.

5x5 board. Each player has 5 pieces on their back rank; a shared neutral piece,
the BOBAIL, starts on the centre square. A turn is TWO sub-moves by the same
player (the multi-move pattern — ``current_player`` stays put between them):

  1. step the Bobail exactly one square in any of the 8 directions to an empty
     square, then
  2. slide one of YOUR pieces in any of the 8 directions AS FAR AS IT CAN GO
     (until the board edge or the square before any piece/the Bobail — stopping
     early is not allowed).

EXCEPTION: the very first turn of the game skips the Bobail step — the opening
player only slides a piece (all sources agree).

WIN (both immediate):
  * The Bobail lands on a player's home row (the row where that player's pieces
    started) -> the OWNER OF THAT ROW wins instantly, mid-turn, regardless of
    who moved it there (you can be forced to deliver the win to your opponent).
  * A player who cannot move the Bobail at the start of their turn (it is
    surrounded / pinned against an edge) LOSES — the trapper wins.

Both sub-moves are ``from>to`` cell paths. The encoding is unambiguous: in the
Bobail phase the only legal ``from`` is the Bobail's square (which no other
piece occupies), and in the piece phase a move can never start on the Bobail's
square.

Draw backstops (sources define no draw; the Bobail can shuffle forever under
random play): threefold repetition of a full turn-start position (pieces +
Bobail + player to move) or a hard cap of 400 sub-move plies is an honest draw.

Seats: player 0 = Red (home row 0, drawn at the bottom), player 1 = Blue
(home row 4, top). The Bobail renders as a neutral (owner-2, green) glyph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

N = 5
PLY_CAP = 400          # sub-move plies (a full turn = 2) -> honest draw
REPEAT = 3             # threefold repetition of a turn-start position -> draw
DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
NAMES = {0: "Red", 1: "Blue"}
HOME = {0: 0, 1: N - 1}      # seat -> its home row (where its pieces start)


def _cell(txt: str):
    c, r = txt.split(",")
    return int(c), int(r)


def _cid(c, r) -> str:
    return f"{c},{r}"


def _on(c, r) -> bool:
    return 0 <= c < N and 0 <= r < N


@dataclass
class BobState:
    pieces: dict = field(default_factory=dict)   # (c, r) -> seat 0/1
    bobail: tuple = (N // 2, N // 2)
    to_move: int = 0
    phase: str = "piece"        # "bobail" | "piece"; first turn skips the bobail step
    ply: int = 0                # sub-moves applied
    seen: dict = field(default_factory=dict)     # turn-start position key -> count
    draw: bool = False


def _poskey(s: BobState) -> str:
    mine = sorted(k for k, v in s.pieces.items() if v == 0)
    theirs = sorted(k for k, v in s.pieces.items() if v == 1)
    return f"{mine}|{theirs}|{s.bobail}|{s.to_move}"


class Bobail(Game):
    name = "Bobail"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BobState:
        pieces = {}
        for c in range(N):
            pieces[(c, HOME[0])] = 0
            pieces[(c, HOME[1])] = 1
        return BobState(pieces=pieces)

    def current_player(self, s: BobState) -> int:
        return s.to_move

    # -- move generation ---------------------------------------------------

    def _slides(self, s: BobState, player: int, occ: set) -> list:
        """Full-distance slides for `player`'s pieces given occupancy `occ`."""
        out = []
        for (c, r), pl in s.pieces.items():
            if pl != player:
                continue
            for dc, dr in DIRS:
                nc, nr = c + dc, r + dr
                while _on(nc, nr) and (nc, nr) not in occ:
                    nc, nr = nc + dc, nr + dr
                nc, nr = nc - dc, nr - dr        # last empty square
                if (nc, nr) != (c, r):
                    out.append(((c, r), (nc, nr)))
        return out

    def _gen(self, s: BobState) -> list:
        if s.phase == "bobail":
            bc, br = s.bobail
            out = []
            for dc, dr in DIRS:
                t = (bc + dc, br + dr)
                if not _on(*t) or t in s.pieces:
                    continue
                # A Bobail step is playable if it ends the game (home row) or
                # leaves the mover at least one piece slide to complete the turn.
                if t[1] in (HOME[0], HOME[1]):
                    out.append((s.bobail, t))
                elif self._slides(s, s.to_move, set(s.pieces) | {t}):
                    out.append((s.bobail, t))
            return out
        occ = set(s.pieces) | {s.bobail}
        return self._slides(s, s.to_move, occ)

    def legal_moves(self, s: BobState) -> list[str]:
        if self._decided(s):
            return []
        return [f"{_cid(*a)}>{_cid(*b)}" for a, b in self._gen(s)]

    # -- dynamics ----------------------------------------------------------

    def apply_move(self, s: BobState, move: str, rng=None) -> BobState:
        frm, to = (_cell(x) for x in move.split(">"))
        if s.phase == "bobail":
            if frm != s.bobail:
                raise ValueError(f"expected a Bobail move from {s.bobail}, got {move}")
            return BobState(pieces=dict(s.pieces), bobail=to, to_move=s.to_move,
                            phase="piece", ply=s.ply + 1, seen=dict(s.seen),
                            draw=s.draw)
        pieces = dict(s.pieces)
        pieces[to] = pieces.pop(frm)
        ns = BobState(pieces=pieces, bobail=s.bobail, to_move=1 - s.to_move,
                      phase="bobail", ply=s.ply + 1, seen=dict(s.seen))
        key = _poskey(ns)
        ns.seen[key] = ns.seen.get(key, 0) + 1
        ns.draw = ns.seen[key] >= REPEAT or ns.ply >= PLY_CAP
        return ns

    # -- outcome -----------------------------------------------------------

    def _decided(self, s: BobState) -> bool:
        return s.bobail[1] in (HOME[0], HOME[1]) or s.draw

    def is_terminal(self, s: BobState) -> bool:
        # decided outright, or the player to move cannot play (Bobail trapped /
        # no way to complete a turn) -> that player loses.
        return self._decided(s) or not self._gen(s)

    def returns(self, s: BobState) -> list[float]:
        if s.bobail[1] == HOME[0]:
            w = 0
        elif s.bobail[1] == HOME[1]:
            w = 1
        elif s.draw:
            return [0.0, 0.0]
        else:
            w = 1 - s.to_move        # trapped/blocked: player to move loses
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def heuristic(self, s: BobState) -> list[float]:
        # Race eval: the Bobail nearer your home row is good for you.
        v = (N - 1 - 2 * s.bobail[1]) / (N - 1) * 0.8
        return [v, -v]

    # -- io ------------------------------------------------------------------

    def serialize(self, s: BobState) -> dict:
        return {
            "pieces": {_cid(c, r): p for (c, r), p in s.pieces.items()},
            "bobail": _cid(*s.bobail),
            "to_move": s.to_move,
            "phase": s.phase,
            "ply": s.ply,
            "seen": dict(s.seen),
            "draw": s.draw,
        }

    def deserialize(self, d: dict) -> BobState:
        return BobState(
            pieces={_cell(k): v for k, v in d["pieces"].items()},
            bobail=_cell(d["bobail"]),
            to_move=d["to_move"],
            phase=d["phase"],
            ply=d["ply"],
            seen=dict(d["seen"]),
            draw=d["draw"],
        )

    def describe_move(self, s: BobState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        alg = lambda c: f"{'abcde'[c[0]]}{c[1] + 1}"  # noqa: E731
        if s.phase == "bobail":
            return f"Bobail {alg(frm)}-{alg(to)}"
        return f"{alg(frm)}-{alg(to)}"

    def render(self, s: BobState, perspective=None) -> dict:
        pieces = [{"cell": _cid(c, r), "owner": p, "label": ""}
                  for (c, r), p in s.pieces.items()]
        pieces.append({"cell": _cid(*s.bobail), "owner": 2, "glyph": "◉"})
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret[0] == ret[1]:
                caption = "Draw"
            else:
                w = 0 if ret[0] > 0 else 1
                how = "Bobail home" if s.bobail[1] == HOME[w] else "Bobail trapped"
                caption = f"{NAMES[w]} wins ({how})"
        elif s.phase == "bobail":
            caption = f"{NAMES[s.to_move]}: step the Bobail"
        else:
            caption = f"{NAMES[s.to_move]}: slide a piece"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [{"cell": _cid(*s.bobail), "kind": "last-move"}]
            if s.phase == "piece" and not self.is_terminal(s) else [],
            "caption": caption,
        }
