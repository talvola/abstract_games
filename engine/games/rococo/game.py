"""Rococo, by Peter Aronson and David Howe (c. 2000).

A Recognized Chess Variant in the Ultima family (chessvariants.com).  Played on
a 10x10 board whose 36 outer squares form a special "edge ring": a move may only
pass over or end on an edge square when that is necessary for a capture (and
then crossing as few edge squares as possible).  Pieces are differentiated by
HOW they capture, not how they move (almost everything moves like a chess
queen).  Win by CAPTURING the enemy King -- no check/checkmate.  A player who
cannot move LOSES; a player whose move repeats a position for the third time
LOSES.

Pieces / letters (per side: 8 P, 2 L, 1 each of the rest):
  K = King         (chess king; may enter an edge square only to capture there)
  A = Advancer     (queen move; captures the enemy just BEYOND its stop, in the
                    direction of travel -- capture by approach; never enters an
                    edge square by its own move, but once swapped onto the ring
                    it may make capturing moves along it)
  W = Withdrawer   (queen move; captures the adjacent enemy it moves directly
                    AWAY from -- capture by withdrawal)
  L = Long Leaper  (queen move; captures by leaping enemies in its line, chain
                    captures along the line allowed)
  S = Swapper      (queen move without capturing; may SWAP with any piece of
                    either side an unobstructed queen-move away; may destroy
                    itself together with an adjacent enemy -- mutual destruction)
  I = Immobilizer  (queen move; never captures; freezes all adjacent enemies;
                    a frozen piece other than a King may commit suicide)
  C = Chameleon    (queen move; captures each victim by the victim's own
                    method, several methods combinable in one move; freezes
                    enemy Immobilizers; swaps with enemy Swappers)
  P = Cannon Pawn  (steps one square any direction, or leaps an adjacent piece
                    landing just beyond; captures BY the leap -- landing on the
                    enemy just past the mount; promotes, optionally, on the far
                    King-rank or the edge rank beyond it to any captured
                    friendly non-Pawn piece)

Move encoding:
  "fc,fr>tc,tr"          normal move (captures are implied side effects)
  "fc,fr>tc,tr=swap"     Swapper/Chameleon swap with the piece at t
  "fc,fr>tc,tr=boom"     mutual destruction with the adjacent enemy at t
  "c,r>c,r"              suicide of the frozen piece at c,r (click it twice)
  "...=A/C/I/L/S/W"      Cannon-Pawn promotion choice (optional; bare move stays a Pawn)

White = player 0, moves first.  Draw guards: hard 600-ply cap and a
100-ply no-progress (no capture / removal / pawn move / promotion) cap.
"""

from __future__ import annotations

import hashlib
from collections import namedtuple
from dataclasses import dataclass, field
from math import tanh
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
N = 10                      # 10x10 board; interior = cols/rows 1..8
PLY_CAP = 600               # hard draw cap on total plies
NO_PROGRESS_CAP = 100       # draw after this many plies without progress

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG

POOL_LETTERS = ("A", "C", "I", "L", "S", "W")   # legal promotion targets
NAMES = {WHITE: "White", BLACK: "Black"}


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


def _s(c: int, r: int) -> str:
    return f"{c},{r}"


def _on(c: int, r: int) -> bool:
    return 0 <= c < N and 0 <= r < N


def _edge(c: int, r: int) -> bool:
    return c == 0 or c == N - 1 or r == 0 or r == N - 1


@dataclass
class RState:
    # board: (c, r) -> (owner, letter)
    board: dict = field(default_factory=dict)
    to_move: int = WHITE
    winner: Optional[int] = None
    reason: str = ""                  # why the game ended (win or draw)
    draw: bool = False
    plies: int = 0
    since_progress: int = 0
    # swap-back ban: after a swap F<->T, a swap between exactly those two cells
    # is illegal on the immediately following turn.  ((fc,fr),(tc,tr)) or None.
    ban: Optional[tuple] = None
    # per-seat pool of removed non-Pawn pieces, available for Pawn promotion:
    # [{letter: count}, {letter: count}]
    pools: list = field(default_factory=lambda: [{}, {}])
    # position-key -> occurrence count (for the third-time-repetition loss)
    history: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# Files a..h = cols 1..8 (col 0 = ring file "x", col 9 = ring file "y").
# Official array (rococo.html diagram + the authors' ZRF; the page's prose
# "King e1" is a typo -- diagram and ZRF both put the King on d1/d8):
BACK = ["I", "W", "L", "K", "C", "L", "A", "S"]


def _setup() -> dict:
    b: dict = {}
    for i, l in enumerate(BACK):
        c = i + 1
        b[(c, 1)] = (WHITE, l)
        b[(c, 2)] = (WHITE, "P")
        b[(c, 7)] = (BLACK, "P")
        b[(c, 8)] = (BLACK, l)
    return b


# ---------------------------------------------------------------------------
# Immobilization
# ---------------------------------------------------------------------------

def _frozen(board: dict, c: int, r: int) -> bool:
    """A piece is frozen iff adjacent to an enemy Immobilizer; an Immobilizer
    is additionally frozen by an adjacent enemy Chameleon (the Chameleon
    freezes ONLY Immobilizers).  Freezing is a passive aura: a frozen
    Immobilizer still freezes its neighbours ("each frozen until the other is
    captured")."""
    me, letter = board[(c, r)]
    for dc, dr in ALL8:
        occ = board.get((c + dc, r + dr))
        if occ and occ[0] != me:
            if occ[1] == "I":
                return True
            if letter == "I" and occ[1] == "C":
                return True
    return False


# ---------------------------------------------------------------------------
# Candidate move generation (per piece), then the edge-square filter
# ---------------------------------------------------------------------------

# to: landing cell; victims: frozenset of captured cells; kind: "move"|"swap";
# swap: the swap-partner cell (None unless kind=="swap"); cross: number of edge
# squares in the path (start-exclusive, landing-inclusive) -- the "edge squares
# passed over" count used for the minimal-crossing rule.
Cand = namedtuple("Cand", "to victims kind swap cross")

Rec = namedtuple("Rec", "mv kind fro to victims swap promo")


def _slide_empties(board, c, r, dc, dr):
    """Yield ((c,r), cross) for each empty square along the ray."""
    nc, nr, cross = c + dc, r + dr, 0
    while _on(nc, nr) and (nc, nr) not in board:
        if _edge(nc, nr):
            cross += 1
        yield (nc, nr), cross
        nc += dc
        nr += dr


def _king_cands(board, c, r, me):
    out = []
    for dc, dr in ALL8:
        t = (c + dc, r + dr)
        if not _on(*t):
            continue
        occ = board.get(t)
        cross = 1 if _edge(*t) else 0
        if occ is None:
            out.append(Cand(t, frozenset(), "move", None, cross))
        elif occ[0] != me:
            out.append(Cand(t, frozenset({t}), "move", None, cross))
    return out


def _advancer_cands(board, c, r, me):
    out = []
    for dc, dr in ALL8:
        for t, cross in _slide_empties(board, c, r, dc, dr):
            beyond = (t[0] + dc, t[1] + dr)
            occ = board.get(beyond)
            v = frozenset({beyond}) if occ and occ[0] != me else frozenset()
            out.append(Cand(t, v, "move", None, cross))
    return out


def _withdrawer_cands(board, c, r, me):
    out = []
    for dc, dr in ALL8:
        behind = (c - dc, r - dr)
        occ = board.get(behind)
        v = frozenset({behind}) if occ and occ[0] != me else frozenset()
        for t, cross in _slide_empties(board, c, r, dc, dr):
            out.append(Cand(t, v, "move", None, cross))
    return out


def _leaper_cands(board, c, r, me):
    out = []
    for dc, dr in ALL8:
        nc, nr, cross = c + dc, r + dr, 0
        victims: list = []
        while _on(nc, nr):
            if _edge(nc, nr):
                cross += 1
            occ = board.get((nc, nr))
            if occ is None:
                out.append(Cand((nc, nr), frozenset(victims), "move", None, cross))
            else:
                if occ[0] == me:
                    break                       # may never leap a friendly piece
                jc, jr = nc + dc, nr + dr
                if not _on(jc, jr) or (jc, jr) in board:
                    break                       # no empty landing square beyond
                victims.append((nc, nr))
            nc += dc
            nr += dr
    return out


def _swapper_cands(board, c, r, me, ban):
    out = []
    for dc, dr in ALL8:
        nc, nr, cross = c + dc, r + dr, 0
        while _on(nc, nr):
            if _edge(nc, nr):
                cross += 1
            occ = board.get((nc, nr))
            if occ is None:
                out.append(Cand((nc, nr), frozenset(), "move", None, cross))
            else:
                # swap with ANY piece of either side (unobstructed queen move)
                if not (ban and {(c, r), (nc, nr)} == {tuple(ban[0]), tuple(ban[1])}):
                    out.append(Cand((nc, nr), frozenset(), "swap", (nc, nr), cross))
                break
            nc += dc
            nr += dr
    return out


def _immobilizer_cands(board, c, r, me):
    out = []
    for dc, dr in ALL8:
        for t, cross in _slide_empties(board, c, r, dc, dr):
            out.append(Cand(t, frozenset(), "move", None, cross))
    return out


def _pawn_cands(board, c, r, me):
    out = []
    for dc, dr in ALL8:
        s1 = (c + dc, r + dr)
        if not _on(*s1):
            continue
        occ1 = board.get(s1)
        if occ1 is None:
            out.append(Cand(s1, frozenset(), "move", None, 1 if _edge(*s1) else 0))
        else:
            # leap over the adjacent mount (either side) to the square beyond
            s2 = (c + 2 * dc, r + 2 * dr)
            if not _on(*s2):
                continue
            occ2 = board.get(s2)
            cross = (1 if _edge(*s1) else 0) + (1 if _edge(*s2) else 0)
            if occ2 is None:
                out.append(Cand(s2, frozenset(), "move", None, cross))
            elif occ2[0] != me:
                out.append(Cand(s2, frozenset({s2}), "move", None, cross))
    return out


def _cham_side_caps(board, me, c, r, dc, dr, tc, tr) -> set:
    """The Chameleon's combinable approach/withdrawal captures, applied to any
    move with direction (dc,dr) landing on (tc,tr): an enemy WITHDRAWER
    directly behind the start is withdrawn from; an enemy ADVANCER directly
    beyond the landing (in the direction of travel) is approached.  Per the
    official page, "it doesn't matter if the move is a slide or a leap"."""
    caps = set()
    b = (c - dc, r - dr)
    occ = board.get(b)
    if occ and occ[0] != me and occ[1] == "W":
        caps.add(b)
    a = (tc + dc, tr + dr)
    occ = board.get(a)
    if occ and occ[0] != me and occ[1] == "A":
        caps.add(a)
    return caps


def _chameleon_cands(board, c, r, me, ban):
    out = []
    for dc, dr in ALL8:
        # queen slide; may leap enemy LONG LEAPERS (capturing them, chainable);
        # may end by swapping with an enemy SWAPPER ("swaps may be combined
        # with other captures"); captures an ADJACENT enemy King king-wise.
        nc, nr, cross = c + dc, r + dr, 0
        jumped: list = []
        while _on(nc, nr):
            if _edge(nc, nr):
                cross += 1
            occ = board.get((nc, nr))
            if occ is None:
                v = frozenset(set(jumped)
                              | _cham_side_caps(board, me, c, r, dc, dr, nc, nr))
                out.append(Cand((nc, nr), v, "move", None, cross))
                nc += dc
                nr += dr
                continue
            if occ[0] == me:
                break
            if occ[1] == "K" and (nc, nr) == (c + dc, r + dr):
                # adjacent enemy King: capture by stepping onto it
                v = frozenset({(nc, nr)}
                              | _cham_side_caps(board, me, c, r, dc, dr, nc, nr))
                out.append(Cand((nc, nr), v, "move", None, cross))
                break
            if occ[1] == "S":
                if not (ban and {(c, r), (nc, nr)} == {tuple(ban[0]), tuple(ban[1])}):
                    v = frozenset(set(jumped)
                                  | _cham_side_caps(board, me, c, r, dc, dr, nc, nr))
                    out.append(Cand((nc, nr), v, "swap", (nc, nr), cross))
                break
            if occ[1] == "L":
                jc, jr = nc + dc, nr + dr
                if not _on(jc, jr) or (jc, jr) in board:
                    break                       # a jumped Leaper needs an empty
                jumped.append((nc, nr))         # square beyond it
                nc, nr = jc, jr
                continue
            break
        # cannon-style capture of an enemy CANNON PAWN: leap the adjacent
        # mount (either side), landing on the Pawn just beyond it.
        m = (c + dc, r + dr)
        t = (c + 2 * dc, r + 2 * dr)
        if m in board and _on(*t):
            occ = board.get(t)
            if occ and occ[0] != me and occ[1] == "P":
                cross = (1 if _edge(*m) else 0) + (1 if _edge(*t) else 0)
                v = frozenset({t} | _cham_side_caps(board, me, c, r, dc, dr, *t))
                out.append(Cand(t, v, "move", None, cross))
    return out


def _edge_filter(cands, letter, start_edge):
    """The edge-square rule (rococo.html, 'formal description'):
      * a move may END on an edge square only as part of a capture;
      * among all this piece's moves accomplishing the SAME capture (same
        victim set / swap partner), an edge landing is legal only if no
        interior landing accomplishes it, and then only the unique landing
        crossing the fewest edge squares;
      * swaps count as captures and their landing (the partner's square) is
        forced, so they are always allowed;
      * the Advancer NEVER enters an edge square by its own move ("may only
        enter an edge square if swapped there") -- except that once ON the
        ring it "may make capturing moves along the edge" (piece text
        overrides the generic uniqueness clause for it).
    Passive moves must land on interior squares (which also means no passive
    move ever passes OVER an edge square: a straight ray only meets the ring
    at its far end, or runs entirely along it)."""
    out = []
    groups: dict = {}
    for cd in cands:
        groups.setdefault((cd.victims, cd.swap), []).append(cd)
    for (victims, swap), ms in groups.items():
        if swap is not None:
            out.extend(ms)
            continue
        if not victims:
            out.extend(m for m in ms if not _edge(*m.to))
            continue
        if letter == "A":
            out.extend(m for m in ms if not _edge(*m.to) or start_edge)
            continue
        interior = [m for m in ms if not _edge(*m.to)]
        if interior:
            out.extend(interior)
        else:
            lo = min(m.cross for m in ms)
            best = [m for m in ms if m.cross == lo]
            if len(best) == 1:                 # "must be the ONLY legal move"
                out.extend(best)
    return out


def _promo_zone(me: int, r: int) -> bool:
    # the rank where the opposing King started, or the edge rank past it
    return r >= 8 if me == WHITE else r <= 1


def _gen_records(s: RState) -> list[Rec]:
    board, me = s.board, s.to_move
    recs: list[Rec] = []
    for (c, r), (o, l) in sorted(board.items()):
        if o != me:
            continue
        fro = _s(c, r)
        if _frozen(board, c, r):
            # a frozen piece may not move at all; a frozen non-King may
            # commit suicide (removing itself counts as the move)
            if l != "K":
                recs.append(Rec(f"{fro}>{fro}", "suicide", (c, r), (c, r),
                                frozenset(), None, None))
            continue
        if l == "K":
            cands = _king_cands(board, c, r, me)
        elif l == "A":
            cands = _advancer_cands(board, c, r, me)
        elif l == "W":
            cands = _withdrawer_cands(board, c, r, me)
        elif l == "L":
            cands = _leaper_cands(board, c, r, me)
        elif l == "S":
            cands = _swapper_cands(board, c, r, me, s.ban)
        elif l == "I":
            cands = _immobilizer_cands(board, c, r, me)
        elif l == "C":
            cands = _chameleon_cands(board, c, r, me, s.ban)
        else:  # "P"
            cands = _pawn_cands(board, c, r, me)
        for cd in _edge_filter(cands, l, _edge(c, r)):
            to = _s(*cd.to)
            if cd.kind == "swap":
                recs.append(Rec(f"{fro}>{to}=swap", "swap", (c, r), cd.to,
                                cd.victims, cd.swap, None))
            else:
                recs.append(Rec(f"{fro}>{to}", "move", (c, r), cd.to,
                                cd.victims, None, None))
                if l == "P" and _promo_zone(me, cd.to[1]):
                    # optional promotion to any captured friendly non-Pawn
                    # piece currently off the board (a Pawn only promotes on a
                    # move it makes ITSELF -- being swapped there never
                    # promotes, which holds structurally: swaps move the
                    # partner, not the Pawn's own record)
                    for pl in POOL_LETTERS:
                        if s.pools[me].get(pl, 0) > 0:
                            recs.append(Rec(f"{fro}>{to}={pl}", "move", (c, r),
                                            cd.to, cd.victims, None, pl))
        # mutual destruction: Swapper vs any adjacent enemy; Chameleon only
        # vs an adjacent enemy Swapper.  Not available when frozen (above).
        if l in ("S", "C"):
            for dc, dr in ALL8:
                t = (c + dc, r + dr)
                occ = board.get(t)
                if occ and occ[0] != me and (l == "S" or occ[1] == "S"):
                    recs.append(Rec(f"{fro}>{_s(*t)}=boom", "boom", (c, r), t,
                                    frozenset({t}), None, None))
    return recs


# ---------------------------------------------------------------------------
# Position key (repetition detection)
# ---------------------------------------------------------------------------

def _poskey(board: dict, to_move: int, ban) -> str:
    txt = ";".join(f"{c},{r}:{o}{l}" for (c, r), (o, l) in sorted(board.items()))
    txt += f"|{to_move}|{sorted(map(tuple, ban)) if ban else ''}"
    return hashlib.md5(txt.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Rococo(Game):
    uid = "rococo"
    name = "Rococo"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> RState:
        s = RState(board=_setup())
        s.history[_poskey(s.board, s.to_move, s.ban)] = 1
        return s

    def current_player(self, s: RState) -> int:
        return s.to_move

    def legal_moves(self, s: RState) -> list[str]:
        if self.is_terminal(s):
            return []
        return [r.mv for r in _gen_records(s)]

    def apply_move(self, s: RState, move: str, rng=None) -> RState:
        if self.is_terminal(s):
            raise ValueError("game already over")
        recs = {r.mv: r for r in _gen_records(s)}
        rec = recs.get(move)
        if rec is None:
            raise ValueError(f"illegal move {move!r}")
        me = s.to_move
        opp = 1 - me
        board = dict(s.board)
        pools = [dict(s.pools[0]), dict(s.pools[1])]
        removed: list = []          # (owner, letter) of every piece leaving play
        ban = None
        progress = False

        if rec.kind == "suicide":
            removed.append(board.pop(rec.fro))
            progress = True
        elif rec.kind == "boom":
            removed.append(board.pop(rec.fro))   # the Swapper/Chameleon itself
            removed.append(board.pop(rec.to))    # the adjacent enemy
            progress = True
        elif rec.kind == "swap":
            for cell in rec.victims:             # a Chameleon swap may also leap
                removed.append(board.pop(cell))
            a, b = board[rec.fro], board[rec.to]
            board[rec.fro], board[rec.to] = b, a
            ban = (rec.fro, rec.to)
            progress = bool(rec.victims)
        else:  # "move"
            owner, letter = board.pop(rec.fro)
            for cell in rec.victims:             # includes any displaced occupant
                removed.append(board.pop(cell))
            board[rec.to] = (owner, rec.promo or letter)
            progress = bool(rec.victims) or letter == "P"
            if rec.promo:
                pools[me][rec.promo] -= 1
                if pools[me][rec.promo] == 0:
                    del pools[me][rec.promo]

        winner = None
        for owner, letter in removed:
            if letter == "K":
                winner = me                      # only enemy Kings can be removed
            elif letter != "P":
                pools[owner][letter] = pools[owner].get(letter, 0) + 1

        plies = s.plies + 1
        if winner is not None:
            return RState(board=board, to_move=opp, winner=me,
                          reason="captured the King", plies=plies,
                          pools=pools, history=dict(s.history))

        nxt = RState(board=board, to_move=opp, plies=plies,
                     since_progress=0 if progress else s.since_progress + 1,
                     ban=ban, pools=pools, history=dict(s.history))
        key = _poskey(board, opp, ban)
        n = nxt.history.get(key, 0) + 1
        nxt.history[key] = n
        if n >= 3:
            # the mover caused the third repetition and loses
            nxt.winner = opp
            nxt.reason = f"{NAMES[me]} caused a threefold repetition"
        elif not _gen_records(nxt):
            # a player unable to move loses
            nxt.winner = me
            nxt.reason = f"{NAMES[opp]} has no legal moves"
        elif plies >= PLY_CAP:
            nxt.draw = True
            nxt.reason = "move limit reached"
        elif nxt.since_progress >= NO_PROGRESS_CAP:
            nxt.draw = True
            nxt.reason = "no progress"
        return nxt

    def is_terminal(self, s: RState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: RState) -> list[float]:
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # material eval for the MCTS rollout cutoff -- MUST return one payoff per
    # seat (same convention as returns())
    _VALS = {"P": 1.0, "W": 2.5, "A": 3.0, "L": 4.0, "S": 4.0, "C": 5.0,
             "I": 6.0, "K": 0.0}

    def heuristic(self, s: RState) -> list[float]:
        diff = 0.0
        for (o, l) in s.board.values():
            diff += self._VALS[l] if o == WHITE else -self._VALS[l]
        v = tanh(diff / 12.0)
        return [v, -v]

    def serialize(self, s: RState) -> dict:
        return {
            "board": {_s(c, r): [o, l] for (c, r), (o, l) in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "reason": s.reason,
            "draw": s.draw,
            "plies": s.plies,
            "since_progress": s.since_progress,
            "ban": [_s(*s.ban[0]), _s(*s.ban[1])] if s.ban else None,
            "pools": [dict(s.pools[0]), dict(s.pools[1])],
            "history": dict(s.history),
        }

    def deserialize(self, d: dict) -> RState:
        return RState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            reason=d.get("reason", ""),
            draw=d.get("draw", False),
            plies=d.get("plies", 0),
            since_progress=d.get("since_progress", 0),
            ban=tuple(_cell(x) for x in d["ban"]) if d.get("ban") else None,
            pools=[dict(p) for p in d.get("pools", [{}, {}])],
            history=dict(d.get("history", {})),
        )

    def describe_move(self, s: RState, move: str) -> str:
        rec = next((r for r in _gen_records(s) if r.mv == move), None)
        if rec is None:
            return move
        letter = s.board[rec.fro][1]
        fro, to = _s(*rec.fro), _s(*rec.to)
        if rec.kind == "suicide":
            return f"{letter} {fro} suicide"
        if rec.kind == "boom":
            return f"{letter} {fro}x{to} mutual destruction"
        base = f"{letter} {fro}<>{to} swap" if rec.kind == "swap" else f"{letter} {fro}-{to}"
        if rec.victims:
            base += f" x{len(rec.victims)}"
        if rec.promo:
            base += f"={rec.promo}"
        return base

    def render(self, s: RState, perspective=None) -> dict:
        pieces = [
            {"cell": _s(c, r), "owner": o, "label": l}
            for (c, r), (o, l) in s.board.items()
        ]
        tints = {_s(c, r): "#d9c79c"
                 for c in range(N) for r in range(N) if _edge(c, r)}
        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins ({s.reason})"
        elif s.draw:
            caption = f"Draw ({s.reason})"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
            "choiceNames": {
                "swap": "Swap places", "boom": "Mutual destruction",
                "A": "Advancer", "C": "Chameleon", "I": "Immobilizer",
                "L": "Long Leaper", "S": "Swapper", "W": "Withdrawer",
            },
        }
