"""Keil (Luis Bolaños Mures, November 2019) — Go on a hexagonal board.

Keil is Go played on the points of a hexagonal grid of triangles — equivalently
(and as rendered here) on the cells of a hexhex board, with the natural
6-neighbour adjacency. Plain Go rules on that topology lose crosscuts and ko
(the board is "too connected"); Keil restores them with a single idea, LINKING,
which weakens the board's connectivity. Everything below implements the
designer's current ruleset verbatim from Sensei's Library (senseis.xmp.net/?Keil,
maintained by the designer, last edited 2023; the designer-written BGG
description of boardgame 295889 is word-for-word identical):

  * "Two adjacent points, and any stones on them, are LINKED if there is
    another point adjacent to both that is the same type as at least one of
    them. Two points are the same type if they are either both empty or both
    occupied by stones of the same color."
  * A GROUP is a maximal set of like-coloured stones connected by links; a
    LIBERTY of a group is an empty point linked to a stone of the group; a
    TERRITORY is a maximal set of empty points connected by links; you own a
    territory if all stones linked to its points are yours.
  * Black plays first. A turn is a placement, the button, or (once the button
    is gone) a pass. After a placement, all enemy groups without liberties are
    removed; then the placed stone's group must have a liberty (no suicide) and
    the position must differ from the positions at the end of ALL YOUR OWN
    previous turns (the designer's restricted positional superko; two identical
    boards are still different positions if the button had been taken in one
    but not the other).
  * Two consecutive passes end the game. Score = your stones + your territory
    points, + komi for White, + half a point for whoever took the button.

KOMI-PIE PROTOCOL (from the page: "the first player chooses the value of komi,
and then the second player chooses sides"): implemented as in-game moves. Seat 0
first plays one of "komi=0" … "komi=12" (the page requires a WHOLE number; the
0–12 range is our discretisation — the designer's sample game used 6), then
seat 1 plays "black" (take Black, i.e. swap) or "white". The BUTTON is the move
"button", legal while unclaimed; passing is illegal until the button is taken,
exactly as the page specifies — which also means every finished (double-pass)
game has the button placed, so a whole komi can never produce a tie.

Board size: the page names no size, but its sample game scores 67 + 60 = 127
board points = a hexhex of side 7 (3·7·6+1). We offer sides 4–7 and default
to 5 (61 points) for playable game length.

Interpretations (documented in rules.md): komi range 0–12; a territory linked
to NO stones at all (e.g. an empty board) is neutral — the page's "all stones
linked … are of your color" is vacuously true for both players, and Go
convention (Tromp-Taylor) counts such regions for no one.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1
NAMES = {BLACK: "Black", WHITE: "White"}
KOMI_CHOICES = tuple(range(0, 13))

_NEI = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1))


@lru_cache(maxsize=None)
def _geom(size: int):
    """cells (sorted tuple), nbrs, and the common-neighbour ("witness") table.

    Witnesses of an adjacent pair are the on-board points adjacent to both —
    2 in the interior, 1 along the board edge. Linking is decided entirely by
    the contents of these witnesses.
    """
    n = size - 1
    cells = tuple(sorted(
        (q, r)
        for q in range(-n, n + 1)
        for r in range(-n, n + 1)
        if abs(q) <= n and abs(r) <= n and abs(q + r) <= n
    ))
    cs = frozenset(cells)
    nbrs = {
        (q, r): tuple((q + dq, r + dr) for dq, dr in _NEI if (q + dq, r + dr) in cs)
        for (q, r) in cells
    }
    common = {}
    for a in cells:
        sa = set(nbrs[a])
        for b in nbrs[a]:
            common[(a, b)] = tuple(sorted(sa.intersection(nbrs[b])))
    return cells, cs, nbrs, common


def _cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


def _linked(board, a, b, common) -> bool:
    """The Keil linking rule, verbatim: a and b (adjacent) are linked iff some
    point adjacent to both is the same type as at least one of them. Types are
    'empty' (None) and the two stone colours, so plain equality on
    ``board.get`` implements 'same type' exactly."""
    ta = board.get(a)
    tb = board.get(b)
    for c in common[(a, b)]:
        tc = board.get(c)
        if tc == ta or tc == tb:
            return True
    return False


def _group(board, seed, nbrs, common) -> set:
    """The linked like-coloured component containing stone ``seed``."""
    color = board[seed]
    seen, stack = {seed}, [seed]
    while stack:
        cur = stack.pop()
        for nb in nbrs[cur]:
            if nb not in seen and board.get(nb) == color and _linked(board, cur, nb, common):
                seen.add(nb)
                stack.append(nb)
    return seen


def _has_lib(board, group, nbrs, common) -> bool:
    """Does ``group`` have a liberty (an empty point LINKED to a member)?"""
    for m in group:
        for e in nbrs[m]:
            if e not in board and _linked(board, m, e, common):
                return True
    return False


def _liberties(board, group, nbrs, common) -> set:
    out = set()
    for m in group:
        for e in nbrs[m]:
            if e not in board and _linked(board, m, e, common):
                out.add(e)
    return out


def _enemy_groups(board, enemy, cells, nbrs, common):
    """All groups of colour ``enemy``: (stone -> group index, [group sets])."""
    gid, groups = {}, []
    for c in cells:
        if board.get(c) == enemy and c not in gid:
            g = _group(board, c, nbrs, common)
            i = len(groups)
            for m in g:
                gid[m] = i
            groups.append(g)
    return gid, groups


def _resolve_full(board, p, color, cells, nbrs, common):
    """Board after ``color`` places at ``p``: place, remove ALL enemy groups
    without liberties (full-board scan — the rules remove every dead enemy
    group, even ones far from the placement), then report whether the placed
    stone's group has a liberty. Returns (board2, dead_set, placed_ok)."""
    b2 = dict(board)
    b2[p] = color
    enemy = 1 - color
    dead, seen = set(), set()
    for c in cells:
        if b2.get(c) == enemy and c not in seen:
            g = _group(b2, c, nbrs, common)
            seen |= g
            if not _has_lib(b2, g, nbrs, common):
                dead |= g
    for c in dead:
        del b2[c]
    own = _group(b2, p, nbrs, common)
    return b2, dead, _has_lib(b2, own, nbrs, common)


def _board_key(board, cells) -> str:
    return "".join("." if c not in board else "bw"[board[c]] for c in cells)


def _score_points(board, cells, nbrs, common):
    """(black, white) board points: stones + owned territories. No komi/button.

    A territory is a linked-empty component; it is owned iff the stones linked
    to its points are non-empty and all one colour (a stoneless territory is
    neutral — documented interpretation of the vacuous case)."""
    black = sum(1 for v in board.values() if v == BLACK)
    white = sum(1 for v in board.values() if v == WHITE)
    seen = set()
    for c in cells:
        if c in board or c in seen:
            continue
        region, stack = {c}, [c]
        seen.add(c)
        while stack:
            cur = stack.pop()
            for nb in nbrs[cur]:
                if nb not in board and nb not in seen and _linked(board, cur, nb, common):
                    seen.add(nb)
                    region.add(nb)
                    stack.append(nb)
        colors = set()
        for t in region:
            for st in nbrs[t]:
                if st in board and _linked(board, t, st, common):
                    colors.add(board[st])
        if colors == {BLACK}:
            black += len(region)
        elif colors == {WHITE}:
            white += len(region)
    return black, white


@dataclass
class KeilState:
    size: int = 5
    board: dict = field(default_factory=dict)      # (q,r) -> BLACK/WHITE
    komi: Optional[int] = None                     # None until seat 0 names it
    side_chosen: bool = False
    black_seat: int = 0                            # seat playing Black
    to_move: int = BLACK                           # colour to move (play phase)
    passes: int = 0
    ply: int = 0
    button_taken: bool = False
    button_holder: Optional[int] = None            # colour that took the button
    last: object = None                            # (q,r) | "pass" | "button" | None
    hist_b: frozenset = field(default_factory=frozenset)   # Black's end-of-turn keys
    hist_w: frozenset = field(default_factory=frozenset)   # White's end-of-turn keys


class Keil(Game):
    uid = "keil"
    name = "Keil"

    @property
    def num_players(self) -> int:
        return 2

    # ------------------------------------------------------------------ setup
    def initial_state(self, options=None, rng=None) -> KeilState:
        opts = options or {}
        size = int(opts.get("size", 5))
        return KeilState(size=size)

    def current_player(self, s: KeilState) -> int:
        if s.komi is None:
            return 0                       # first player names the komi
        if not s.side_chosen:
            return 1                       # second player chooses sides
        return s.black_seat if s.to_move == BLACK else 1 - s.black_seat

    # ------------------------------------------------------------- move lists
    def _ply_cap(self, s: KeilState) -> int:
        return 3 * len(_geom(s.size)[0]) + 4

    def _pos_key(self, board, cells, button_taken) -> str:
        return _board_key(board, cells) + ("!" if button_taken else "-")

    def _hist(self, s: KeilState, color: int) -> frozenset:
        return s.hist_b if color == BLACK else s.hist_w

    def _legal_placements(self, s: KeilState, ignore_repetition=False):
        """Yield (move, board2) for every legal placement of s.to_move.

        Scoped capture check: a placement by X can only remove liberties of
        enemy groups holding a stone adjacent to the placement (a lost liberty
        is either the placement point itself or a stone–empty link whose
        witness is the placement point; both put the stone next to it), and it
        can never break enemy–enemy links (their witnesses must be enemy-
        coloured). Enemy groups that were ALREADY liberty-less die on any
        placement. selftest.py cross-checks this against the full-board scan.
        """
        cells, _, nbrs, common = _geom(s.size)
        color = s.to_move
        enemy = 1 - color
        gid, groups = _enemy_groups(s.board, enemy, cells, nbrs, common)
        stale = set()
        stale_ids = set()
        for i, g in enumerate(groups):
            if not _has_lib(s.board, g, nbrs, common):
                stale |= g
                stale_ids.add(i)
        hist = self._hist(s, color)
        flag = s.button_taken
        for p in cells:
            if p in s.board:
                continue
            b2 = dict(s.board)
            b2[p] = color
            dead = set(stale)
            for i in {gid[t] for t in nbrs[p] if t in gid}:
                if i not in stale_ids and not _has_lib(b2, groups[i], nbrs, common):
                    dead |= groups[i]
            for c in dead:
                del b2[c]
            own = _group(b2, p, nbrs, common)
            if not _has_lib(b2, own, nbrs, common):
                continue                                # suicide
            if not ignore_repetition and self._pos_key(b2, cells, flag) in hist:
                continue                                # own-position repetition
            yield f"{p[0]},{p[1]}", b2

    def legal_moves(self, s: KeilState) -> list[str]:
        if s.komi is None:
            return [f"komi={k}" for k in KOMI_CHOICES]
        if not s.side_chosen:
            return ["black", "white"]
        if self.is_terminal(s):
            return []
        moves = [m for m, _ in self._legal_placements(s)]
        moves.append("pass" if s.button_taken else "button")
        return moves

    # ------------------------------------------------------------- transition
    def apply_move(self, s: KeilState, move: str, rng=None) -> KeilState:
        cells = _geom(s.size)[0]
        if s.komi is None:
            if not (move.startswith("komi=") and int(move[5:]) in KOMI_CHOICES):
                raise ValueError(f"expected a komi offer, got {move!r}")
            return replace(s, komi=int(move[5:]), ply=s.ply + 1)
        if not s.side_chosen:
            if move not in ("black", "white"):
                raise ValueError(f"expected a side choice, got {move!r}")
            return replace(s, side_chosen=True,
                           black_seat=(1 if move == "black" else 0),
                           ply=s.ply + 1)

        color = s.to_move

        def record(st: KeilState) -> KeilState:
            key = self._pos_key(st.board, cells, st.button_taken)
            if color == BLACK:
                return replace(st, hist_b=st.hist_b | {key})
            return replace(st, hist_w=st.hist_w | {key})

        if move == "button":
            if s.button_taken:
                raise ValueError("button already taken")
            return record(replace(s, button_taken=True, button_holder=color,
                                  to_move=1 - color, passes=0, ply=s.ply + 1,
                                  last="button"))
        if move == "pass":
            if not s.button_taken:
                raise ValueError("passing is illegal until the button is taken")
            return record(replace(s, to_move=1 - color, passes=s.passes + 1,
                                  ply=s.ply + 1, last="pass"))

        p = _cell(move)
        _, cset, nbrs, common = _geom(s.size)
        if p not in cset or p in s.board:
            raise ValueError(f"illegal placement {move!r}")
        b2, _dead, ok = _resolve_full(s.board, p, color, cells, nbrs, common)
        if not ok:
            raise ValueError(f"suicide is illegal: {move!r}")
        if self._pos_key(b2, cells, s.button_taken) in self._hist(s, color):
            raise ValueError(f"repetition of an own previous position: {move!r}")
        return record(replace(s, board=b2, to_move=1 - color, passes=0,
                              ply=s.ply + 1, last=p))

    # -------------------------------------------------------------- terminal
    def is_terminal(self, s: KeilState) -> bool:
        if s.komi is None or not s.side_chosen:
            return False
        return s.passes >= 2 or s.ply >= self._ply_cap(s)

    def _final_scores(self, s: KeilState):
        cells, _, nbrs, common = _geom(s.size)
        b, w = _score_points(s.board, cells, nbrs, common)
        b = float(b)
        w = float(w) + (s.komi or 0)
        if s.button_holder == BLACK:
            b += 0.5
        elif s.button_holder == WHITE:
            w += 0.5
        return b, w

    def returns(self, s: KeilState) -> list[float]:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        b, w = self._final_scores(s)
        if b == w:
            return [0.0, 0.0]              # only reachable at the ply-cap safety net
        winner_color = BLACK if b > w else WHITE
        winner_seat = s.black_seat if winner_color == BLACK else 1 - s.black_seat
        out = [0.0, 0.0]
        out[winner_seat] = 1.0
        out[1 - winner_seat] = -1.0
        return out

    def heuristic(self, s: KeilState) -> list[float]:
        if s.komi is None or not s.side_chosen:
            return [0.0, 0.0]
        b, w = self._final_scores(s)
        d = (b - w) / (len(_geom(s.size)[0]) / 8.0)
        v = max(-1.0, min(1.0, d))
        out = [0.0, 0.0]
        out[s.black_seat] = v
        out[1 - s.black_seat] = -v
        return out

    # ------------------------------------------------------------------ io
    def serialize(self, s: KeilState) -> dict:
        last = s.last
        if isinstance(last, tuple):
            last = f"{last[0]},{last[1]}"
        return {
            "size": s.size,
            "board": {f"{q},{r}": p for (q, r), p in s.board.items()},
            "komi": s.komi,
            "side_chosen": s.side_chosen,
            "black_seat": s.black_seat,
            "to_move": s.to_move,
            "passes": s.passes,
            "ply": s.ply,
            "button_taken": s.button_taken,
            "button_holder": s.button_holder,
            "last": last,
            "hist_b": sorted(s.hist_b),
            "hist_w": sorted(s.hist_w),
        }

    def deserialize(self, d: dict) -> KeilState:
        last = d.get("last")
        if isinstance(last, str) and "," in last:
            last = _cell(last)
        return KeilState(
            size=d["size"],
            board={_cell(k): v for k, v in d["board"].items()},
            komi=d.get("komi"),
            side_chosen=d.get("side_chosen", False),
            black_seat=d.get("black_seat", 0),
            to_move=d.get("to_move", BLACK),
            passes=d.get("passes", 0),
            ply=d.get("ply", 0),
            button_taken=d.get("button_taken", False),
            button_holder=d.get("button_holder"),
            last=last,
            hist_b=frozenset(d.get("hist_b", [])),
            hist_w=frozenset(d.get("hist_w", [])),
        )

    def describe_move(self, s: KeilState, move: str) -> str:
        if move.startswith("komi="):
            return f"komi {move[5:]}"
        if move == "black":
            return "choose Black (swap)"
        if move == "white":
            return "choose White"
        if move == "button":
            return "take the button (½ point)"
        return move

    # ------------------------------------------------------------------ view
    def render(self, s: KeilState, perspective=None) -> dict:
        def seat_of(color):
            return s.black_seat if color == BLACK else 1 - s.black_seat

        pieces = [
            {"cell": f"{q},{r}", "owner": seat_of(p), "label": ""}
            for (q, r), p in s.board.items()
        ]
        highlights = []
        if isinstance(s.last, tuple):
            highlights.append({"cell": f"{s.last[0]},{s.last[1]}", "kind": "last-move"})
        if s.komi is None:
            caption = ("First player names the komi (whole points added to "
                       "White's score)")
        elif not s.side_chosen:
            caption = (f"Komi is {s.komi} — the other player now chooses a side "
                       f"(black = swap)")
        else:
            b, w = self._final_scores(s)
            button = (f"button: {NAMES[s.button_holder]}" if s.button_taken
                      else "button: available")
            score = f"score B {b:g} / W {w:g} (komi {s.komi})"
            if self.is_terminal(s):
                res = "Draw" if b == w else f"{NAMES[BLACK if b > w else WHITE]} wins"
                caption = f"{res} — Black {b:g}, White {w:g}  ·  {button}"
            else:
                passed = "  ·  opponent passed" if s.last == "pass" else ""
                caption = f"{NAMES[s.to_move]} to move{passed}  ·  {score}  ·  {button}"
        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
