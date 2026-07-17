"""Ludus Latrunculorum — the Roman "game of little soldiers".

Implemented as Ulrich Schädler's reconstruction in the playable form published
by the Locus Ludi project (University of Fribourg, ERC #741520):
https://locusludi.ch/wp-content/uploads/2022/08/LUDUS-LATRUNCULORUM_rules_GB.pdf
That leaflet (both variant rulesets + worked figures) is the source of truth;
see rules.md for every documented interpretation and each place where the Ludii
encoding of the same rulesets differs (the leaflet wins).

Board: fixed 8x8. Counters per player: 20 (leaflet); 16/24 offered as an option
per Schädler 2001 ("players agree on a number of pieces between 16 and 24").

PHASE 1 — PLACEMENT ("vagi"). Players alternate placing ONE counter on any
vacant square until all counters are down. No captures/traps are made in this
phase; sandwiches formed by placement never trap. Move = "c,r".

PHASE 2 — MOVEMENT ("ordinarii").
* Seneca variant (default): a turn is [forced removal ply, if any] + one move.
  - Forced removal: if you have trapped ("incitus") enemy counters on the
    board at the start of your turn, you MUST first remove exactly one of them
    (your choice which). Encoded as its own ply: the trapped counter's "c,r".
  - Move: one FREE counter one step orthogonally to an empty square, OR a
    draughts-style multi-leap "a>b>c" — each hop jumps a single orthogonally
    adjacent counter OF YOUR OWN COLOUR (free or trapped) landing on the empty
    square directly beyond; a leap path may not revisit a square (nor return
    to its origin). Leaps never capture by themselves.
  - Trapping (custodial), evaluated at the FINAL landing square: an enemy
    counter enclosed between the arriving counter and another FREE counter of
    yours on the opposite orthogonal side — or, for a counter on a corner
    square, on the two squares orthogonally adjacent to the corner — becomes
    "incitus": trapped/flipped, still on the board. It cannot move and cannot
    serve as a trapping guard. One move may trap several counters at once.
  - Freeing (Seneca, Letters 117.30): a trapped counter is set free
    immediately if either of its two recorded guards is itself trapped, or
    leaves its square (or is otherwise gone). Hence every surviving incitus
    always has both guards standing free — the leaflet's removal proviso
    ("provided his two surrounding stones themselves are still free") is an
    invariant here.
  - No suicide: moving between two enemy counters does not trap the mover.
  - No shuttling: a player may not move the same counter straight back
    (exactly reversing their own previous move's endpoints).
* Piso variant (option): no leaps; enclosure (straight or corner) captures
  IMMEDIATELY — all counters trapped by one move are removed together. No
  incitus state. Same placement phase, no-suicide and no-shuttling rules.

END: when a player is reduced to one counter, or the player to move has no
legal move (blockade), the game ends and the player who captured MOST counters
wins; equal captures is an honest draw. Backstops: 120 movement plies without
a placement/trap/capture, or 600 movement plies total, end the game with the
same most-captures scoring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

W = H = 8
ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))
CORNERS = {(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)}
PLACE, MOVE = "place", "move"
ST_REMOVE, ST_MOVE = "remove", "move"
SENECA, PISO = "seneca", "piso"

NO_PROGRESS_CAP = 120   # movement plies without a trap/capture -> score & end
HARD_PLY_CAP = 600      # total movement plies -> score & end


def _cell(txt: str):
    c, r = txt.split(",")
    return int(c), int(r)


def _cid(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _on(cell) -> bool:
    return 0 <= cell[0] < W and 0 <= cell[1] < H


@dataclass
class LState:
    board: dict = field(default_factory=dict)    # (c,r) -> owner 0/1
    trapped: dict = field(default_factory=dict)  # (c,r) -> (guard1, guard2)
    variant: str = SENECA
    n_pieces: int = 20
    phase: str = PLACE
    stage: str = ST_MOVE          # within a Seneca movement turn
    to_move: int = 0
    placed: list = field(default_factory=lambda: [0, 0])
    captures: list = field(default_factory=lambda: [0, 0])
    last: list = field(default_factory=lambda: [None, None])  # per player (frm,to)
    winner: Optional[int] = None
    over: bool = False
    no_progress: int = 0
    ply: int = 0


class LudusLatrunculorum(Game):
    name = "Ludus Latrunculorum"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> LState:
        variant = SENECA
        n = 20
        if options:
            v = str(options.get("variant", SENECA)).lower()
            if v in (SENECA, PISO):
                variant = v
            try:
                cand = int(options.get("pieces", 20))
                if cand in (16, 20, 24):
                    n = cand
            except (TypeError, ValueError):
                pass
        return LState(variant=variant, n_pieces=n)

    # ---------- helpers ----------
    def current_player(self, s: LState) -> int:
        return s.to_move

    def _count(self, s_board: dict, p: int) -> int:
        return sum(1 for v in s_board.values() if v == p)

    def _removable(self, s: LState, p: int) -> list:
        """Trapped enemy counters player p must remove (Seneca)."""
        if s.variant != SENECA:
            return []
        return sorted(c for c in s.trapped if s.board.get(c) == 1 - p)

    def _copy(self, s: LState) -> LState:
        return LState(board=dict(s.board), trapped=dict(s.trapped),
                      variant=s.variant, n_pieces=s.n_pieces, phase=s.phase,
                      stage=s.stage, to_move=s.to_move, placed=list(s.placed),
                      captures=list(s.captures), last=list(s.last),
                      winner=s.winner, over=s.over,
                      no_progress=s.no_progress, ply=s.ply)

    # ---------- move generation ----------
    def _steps(self, s: LState, frm, p) -> list:
        out = []
        for d in ORTHO:
            to = (frm[0] + d[0], frm[1] + d[1])
            if _on(to) and to not in s.board:
                out.append([frm, to])
        return out

    def _leap_paths(self, s: LState, frm, p) -> list:
        """All leap paths (each prefix is itself a legal move). Jumped counter
        must be the mover's OWN colour (free or trapped, leaflet wording);
        landing squares must be empty and unvisited (origin counts visited)."""
        bd = dict(s.board)
        del bd[frm]  # the leaper has left its origin square
        out = []

        def dfs(cur, path, visited):
            for d in ORTHO:
                mid = (cur[0] + d[0], cur[1] + d[1])
                land = (cur[0] + 2 * d[0], cur[1] + 2 * d[1])
                if not _on(land) or land in bd or land in visited:
                    continue
                if bd.get(mid) != p:      # own colour only — NOT enemies
                    continue
                np_ = path + [land]
                out.append(np_)
                dfs(land, np_, visited | {land})

        dfs(frm, [frm], {frm})
        return out

    def _movement_paths(self, s: LState) -> list:
        p = s.to_move
        paths = []
        for cell, owner in s.board.items():
            if owner != p or cell in s.trapped:
                continue
            paths.extend(self._steps(s, cell, p))
            if s.variant == SENECA:
                paths.extend(self._leap_paths(s, cell, p))
        # no shuttling: may not exactly reverse your own previous move
        prev = s.last[p]
        if prev is not None:
            pf, pt = prev
            paths = [pa for pa in paths if not (pa[0] == pt and pa[-1] == pf)]
        return sorted(paths)

    def legal_moves(self, s: LState) -> list:
        if self.is_terminal(s):
            return []
        if s.phase == PLACE:
            return [f"{c},{r}" for r in range(H) for c in range(W)
                    if (c, r) not in s.board]
        if s.variant == SENECA and s.stage == ST_REMOVE:
            rem = self._removable(s, s.to_move)
            if rem:
                return [_cid(c) for c in rem]
        return [">".join(_cid(c) for c in path)
                for path in self._movement_paths(s)]

    # ---------- trapping / freeing ----------
    def _find_traps(self, board, trapped, to, p):
        """Enemy counters newly enclosed by the arrival at `to`.
        Returns {cell: (guard1, guard2)}. Guards must be FREE own counters."""
        new = {}
        opp = 1 - p
        for d in ORTHO:
            mid = (to[0] + d[0], to[1] + d[1])
            if board.get(mid) != opp or mid in trapped:
                continue
            if mid in CORNERS:
                adj = [(mid[0] + dd[0], mid[1] + dd[1]) for dd in ORTHO
                       if _on((mid[0] + dd[0], mid[1] + dd[1]))]
                other = [a for a in adj if a != to]
                if len(other) == 1 and board.get(other[0]) == p \
                        and other[0] not in trapped:
                    new[mid] = (to, other[0])
            else:
                beyond = (to[0] + 2 * d[0], to[1] + 2 * d[1])
                if _on(beyond) and board.get(beyond) == p \
                        and beyond not in trapped:
                    new[mid] = (to, beyond)
        return new

    def _free_by_guard(self, trapped: dict, guard_cell) -> None:
        """Free every incitus that lists guard_cell among its guards."""
        for cell in [c for c, g in trapped.items() if guard_cell in g]:
            del trapped[cell]

    # ---------- apply ----------
    def apply_move(self, s: LState, move: str, rng=None) -> LState:
        if s.phase == PLACE:
            return self._apply_place(s, move)
        if s.variant == SENECA and s.stage == ST_REMOVE:
            return self._apply_remove(s, move)
        return self._apply_movement(s, move)

    def _apply_place(self, s: LState, move: str) -> LState:
        ns = self._copy(s)
        cell = _cell(move)
        ns.board[cell] = s.to_move
        ns.placed[s.to_move] += 1
        if sum(ns.placed) >= 2 * s.n_pieces:
            ns.phase = MOVE
            ns.stage = ST_MOVE
            ns.to_move = 0       # placer 1 (seat 0) also opens the movement phase
            if not self.legal_moves(ns):    # freak full-board blockade
                return self._score(ns)
            return ns
        ns.to_move = 1 - s.to_move
        return ns

    def _apply_remove(self, s: LState, move: str) -> LState:
        ns = self._copy(s)
        p = s.to_move
        cell = _cell(move)
        del ns.board[cell]
        ns.trapped.pop(cell, None)
        self._free_by_guard(ns.trapped, cell)   # defensive; invariant makes it a no-op
        ns.captures[p] += 1
        ns.no_progress = 0
        if self._count(ns.board, 1 - p) <= 1:
            return self._score(ns)
        ns.stage = ST_MOVE          # same player now moves
        if not self.legal_moves(ns):
            return self._score(ns)  # blocked after the forced removal
        return ns

    def _apply_movement(self, s: LState, move: str) -> LState:
        ns = self._copy(s)
        p = s.to_move
        path = [_cell(x) for x in move.split(">")]
        frm, to = path[0], path[-1]
        owner = ns.board.pop(frm)
        ns.board[to] = owner

        # 1. departure-freeing: leaving a square frees anything it guarded
        self._free_by_guard(ns.trapped, frm)

        # 2. new enclosures at the final landing square
        new_traps = self._find_traps(ns.board, ns.trapped, to, p)
        captured_now = 0
        if s.variant == SENECA:
            ns.trapped.update(new_traps)
            # 3. Seneca freeing: trapping a guard frees its victim at once
            for cell in new_traps:
                self._free_by_guard(ns.trapped, cell)
        else:  # Piso: immediate capture, all trapped counters removed together
            for cell in new_traps:
                del ns.board[cell]
            captured_now = len(new_traps)
            ns.captures[p] += captured_now

        ns.last[p] = (frm, to)
        if captured_now and self._count(ns.board, 1 - p) <= 1:
            return self._score(ns)
        progressed = bool(new_traps) or captured_now > 0
        return self._end_turn(ns, progressed)

    def _end_turn(self, ns: LState, progressed: bool) -> LState:
        ns.ply += 1
        ns.no_progress = 0 if progressed else ns.no_progress + 1
        if ns.no_progress >= NO_PROGRESS_CAP or ns.ply >= HARD_PLY_CAP:
            return self._score(ns)
        opp = 1 - ns.to_move
        ns.to_move = opp
        ns.stage = ST_REMOVE if self._removable(ns, opp) else ST_MOVE
        if not self.legal_moves(ns):
            return self._score(ns)      # blockade: opp cannot act at all
        return ns

    def _score(self, ns: LState) -> LState:
        ns.over = True
        c0, c1 = ns.captures
        ns.winner = 0 if c0 > c1 else 1 if c1 > c0 else None
        return ns

    # ---------- terminal ----------
    def is_terminal(self, s: LState) -> bool:
        return s.over

    def returns(self, s: LState) -> list:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    def heuristic(self, s: LState) -> list:
        # material balance, discounting trapped counters (nearly captured).
        eff = [0.0, 0.0]
        for cell, owner in s.board.items():
            eff[owner] += 0.25 if cell in s.trapped else 1.0
        v = math.tanh((eff[0] - eff[1]) / 6.0)
        return [v, -v]

    # ---------- serialize ----------
    def serialize(self, s: LState) -> dict:
        return {
            "board": {_cid(c): v for c, v in sorted(s.board.items())},
            "trapped": {_cid(c): [_cid(g[0]), _cid(g[1])]
                        for c, g in sorted(s.trapped.items())},
            "variant": s.variant,
            "n_pieces": s.n_pieces,
            "phase": s.phase,
            "stage": s.stage,
            "to_move": s.to_move,
            "placed": list(s.placed),
            "captures": list(s.captures),
            "last": [None if m is None else [_cid(m[0]), _cid(m[1])]
                     for m in s.last],
            "winner": s.winner,
            "over": s.over,
            "no_progress": s.no_progress,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> LState:
        return LState(
            board={_cell(k): v for k, v in d["board"].items()},
            trapped={_cell(k): (_cell(g[0]), _cell(g[1]))
                     for k, g in d.get("trapped", {}).items()},
            variant=d.get("variant", SENECA),
            n_pieces=d.get("n_pieces", 20),
            phase=d.get("phase", PLACE),
            stage=d.get("stage", ST_MOVE),
            to_move=d.get("to_move", 0),
            placed=list(d.get("placed", [0, 0])),
            captures=list(d.get("captures", [0, 0])),
            last=[None if m is None else (_cell(m[0]), _cell(m[1]))
                  for m in d.get("last", [None, None])],
            winner=d.get("winner"),
            over=d.get("over", False),
            no_progress=d.get("no_progress", 0),
            ply=d.get("ply", 0),
        )

    # ---------- presentation ----------
    def describe_move(self, s: LState, move: str) -> str:
        if s.phase == PLACE:
            return f"place {move}"
        if s.variant == SENECA and s.stage == ST_REMOVE:
            return f"remove {move}"
        cells = move.split(">")
        if len(cells) > 2:
            return "leap " + "-".join(cells)
        return f"{cells[0]}-{cells[1]}"

    def render(self, s: LState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
        pieces = []
        for cell, owner in sorted(s.board.items()):
            spec = {"cell": _cid(cell), "owner": owner}
            if cell in s.trapped:
                # incitus: flipped / disarmed — washed-out fill, flat look
                if owner == 0:
                    spec["fill"], spec["stroke"] = "#ecc9c9", "#b98181"
                else:
                    spec["fill"], spec["stroke"] = "#c5d2ea", "#7d94bd"
            pieces.append(spec)
        c0, c1 = s.captures
        score = f"captures {c0}:{c1}"
        if self.is_terminal(s):
            caption = ("Draw — " + score if s.winner is None
                       else f"{names[s.winner]} wins — {score}")
        elif s.phase == PLACE:
            left = s.n_pieces - s.placed[s.to_move]
            caption = f"Placement — {names[s.to_move]} places ({left} left)"
        elif s.variant == SENECA and s.stage == ST_REMOVE:
            caption = f"{names[s.to_move]} must remove a trapped counter — {score}"
        else:
            caption = f"{names[s.to_move]} to move — {score}"
        highlights = []
        prev = s.last[1 - s.to_move]
        if s.phase == MOVE and prev is not None:
            highlights = [{"cell": _cid(prev[0]), "kind": "last-move"},
                          {"cell": _cid(prev[1]), "kind": "last-move"}]
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
