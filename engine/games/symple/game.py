"""Symple, by Christian Freeling & Benedikt Rosenau (2010).

A group / area game played on the intersections of an odd-sized square board
(standard 19x19; smaller odd boards play the same). Two players, Black (0,
moves first) and White (1), place stones of their colour. Stones never move and
are never captured.

THE TWO TURN OPTIONS (the signature mechanic). On your turn you do EXACTLY ONE
of:

  (a) PLACE a new group -- put one stone on a vacant cell that is NOT
      orthogonally adjacent to any stone of your own colour (it starts a brand
      new group); OR
  (b) GROW -- add exactly one stone to EVERY one of your groups that CAN grow.
      A group grows by placing one stone on an empty cell orthogonally adjacent
      to it. No group may grow more than one stone in a turn. A single placed
      stone that is orthogonally adjacent to two-or-more of your groups grows
      ALL of them at once (a merge). It is illegal to place a growth stone that
      would (also) touch a group that has ALREADY grown this turn -- i.e. you
      may not grow the same group twice. Groups that are completely surrounded
      (no empty orthogonal neighbour reachable under those constraints) simply
      do not grow; "grow all POSSIBLE groups".

BALANCING (pie-style) RULE. White moves first; this is a known first-player
edge. To compensate: if, and only if, NEITHER player has grown yet, BLACK (the
SECOND player here -- see the seat note below) may, in a single turn, GROW all
of his groups AND THEN PLACE one new stone. This combined turn is available to
Black only while no growth has yet occurred by either side.

  Seat note: in the canonical rules White moves first and Black gets the
  balancing turn. This package keeps the platform convention that seat 0 moves
  first, so we label seat 0 "Black-first / first player" and give the BALANCING
  turn to the SECOND player (seat 1). The *mechanic* (the player who does NOT
  move first gets a one-time grow+place) is faithful; only the colour label is
  swapped so that "the first player" == seat 0. See rules.md.

END CONDITION. The game ends when the board is full (or, defensively, when
neither player has any legal action). Resignation is not modelled (async / bot).

SCORING. score(player) = (# of your stones on the board) - P * (# of your
groups), where P is an even constant agreed beforehand (the source allows
P in {4,6,8,10,12}; default 8 here -- see the manifest option). Most points
wins. P is even so the game is effectively drawless; we still resolve an exact
tie as a draw and add a hard ply-cap safety draw (flagged non-original).

MOVE ENCODING. Stones are placed, so notation is cell paths "c,r" (0-indexed
col,row).
  * A new-group placement is a single cell "c,r" (one click).
  * GROW is driven as a multi-step, same-player turn: the action button "grow"
    enters grow-mode, then the player clicks one growth cell per still-ungrown
    group (the engine offers only legal continuations and auto-ends the turn
    once every growable group has grown). Each growth sub-move is a single cell
    "c,r". Because a turn touches every group, encoding the whole grow as one
    fixed ">"-path would blow up combinatorially; the step-by-step same-player
    turn keeps legal_moves small and the generic click-to-move UI works
    unchanged. See rules.md for the UX.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # seat 0 = first player, seat 1 = second (gets balancing turn)
HARD_PLY_CAP_FACTOR = 4  # safety: cap total plies at FACTOR * cells (non-original draw)


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


def _neighbors(c: int, r: int, size: int):
    if c > 0:
        yield (c - 1, r)
    if c < size - 1:
        yield (c + 1, r)
    if r > 0:
        yield (c, r - 1)
    if r < size - 1:
        yield (c, r + 1)


def _group(board: dict, start: tuple[int, int], size: int) -> set:
    """Maximally-connected (4-orthogonal) same-colour group containing start."""
    colour = board[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for nb in _neighbors(c, r, size):
            if nb not in seen and board.get(nb) == colour:
                seen.add(nb)
                stack.append(nb)
    return seen


def _groups(board: dict, player: int, size: int) -> list[set]:
    """All connected same-colour groups owned by `player`, each as a cell set.
    Returned in a canonical order (by each group's minimum cell)."""
    seen: set = set()
    out: list[set] = []
    for cell, p in board.items():
        if p != player or cell in seen:
            continue
        grp = _group(board, cell, size)
        seen |= grp
        out.append(grp)
    out.sort(key=lambda g: min(g))
    return out


def _new_group_cells(board: dict, player: int, size: int) -> list[tuple]:
    """Empty cells where `player` may PLACE a NEW group: vacant and NOT
    orthogonally adjacent to any own stone."""
    out = []
    for c in range(size):
        for r in range(size):
            if (c, r) in board:
                continue
            if any(board.get(nb) == player for nb in _neighbors(c, r, size)):
                continue
            out.append((c, r))
    return out


def _growth_cells_for(board: dict, group: set, player: int, size: int,
                      forbidden: set) -> list[tuple]:
    """Empty cells that legally grow `group`: orthogonally adjacent to the
    group, vacant, and NOT orthogonally adjacent to any stone in `forbidden`
    (the cells of groups that already grew this turn -- you may not re-grow
    them). A cell adjacent to two *ungrown* groups is allowed (a merge)."""
    out = set()
    for (gc, gr) in group:
        for nb in _neighbors(gc, gr, size):
            if nb in board:
                continue
            # must not touch an already-grown group's stones
            if any(b in forbidden for b in _neighbors(nb[0], nb[1], size)):
                continue
            out.add(nb)
    return sorted(out)


@dataclass
class SympleState:
    size: int = 19
    P: int = 8
    board: dict = field(default_factory=dict)       # (c, r) -> 0/1
    to_move: int = BLACK
    grown_ever: bool = False                         # has ANY growth happened?
    ply: int = 0                                     # completed turns
    # --- transient mid-turn (a grow turn is a multi-step same-player turn) ---
    growing: bool = False                            # currently in grow-mode
    grown_cells: tuple = ()                          # stones placed THIS grow turn (also marks grown groups)
    balancing_place: bool = False                    # balancing turn: place owed after grow
    last: tuple = ()                                 # last placed cell(s) for highlight
    winner: Optional[int] = None                     # 0/1, or -1 for draw
    done: bool = False


def _board_full(s: SympleState) -> bool:
    return len(s.board) >= s.size * s.size


class Symple(Game):
    uid = "symple"
    name = "Symple"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SympleState:
        opts = options or {}
        size = int(opts.get("size", 19))
        if size % 2 == 0:
            size += 1  # board must be odd
        P = int(opts.get("penalty", 8))
        if P % 2 != 0:
            P += 1  # P must be even (drawless)
        return SympleState(size=size, P=P)

    def current_player(self, s: SympleState) -> int:
        return s.to_move

    # ---- balancing availability: only the SECOND player, before any growth ----
    def _balancing_available(self, s: SympleState) -> bool:
        return (not s.grown_ever) and (s.to_move == WHITE)

    def _groups_that_can_grow(self, board: dict, player: int, size: int,
                              forbidden: set) -> list[set]:
        """Ungrown groups of `player` that have at least one legal growth cell.
        A group counts as already-grown this turn iff any of its current cells
        is one of the stones placed this turn (`forbidden` == grown_cells). This
        membership test is robust to group merges renaming the group's min-cell.
        """
        res = []
        for g in _groups(board, player, size):
            if g & forbidden:  # contains a stone grown this turn -> already grown
                continue
            if _growth_cells_for(board, g, player, size, forbidden):
                res.append(g)
        return res

    def legal_moves(self, s: SympleState) -> list[str]:
        if self.is_terminal(s):
            return []
        mover = s.to_move
        size = s.size

        if s.growing:
            # Mid grow-turn: offer growth cells for the NEXT ungrown growable group.
            forbidden = set(s.grown_cells)
            pend = self._groups_that_can_grow(s.board, mover, size, forbidden)
            if pend:
                g = pend[0]  # canonical: lowest-min ungrown growable group
                cells = _growth_cells_for(s.board, g, mover, size, forbidden)
                return [f"{c},{r}" for (c, r) in cells]
            # No more groups can grow. If this is a balancing turn, the player
            # now owes a single NEW-group placement; otherwise the grow turn ends
            # (handled in apply_move via "growdone").
            if s.balancing_place:
                place = _new_group_cells(s.board, mover, size)
                moves = [f"{c},{r}" for (c, r) in place]
                moves.append("growdone")  # allow skipping the place if none/declined
                return moves
            return ["growdone"]

        # Start of a fresh turn: choose to PLACE a new group or to GROW.
        moves = [f"{c},{r}" for (c, r) in _new_group_cells(s.board, mover, size)]
        # GROW is available if at least one group can grow.
        if self._groups_that_can_grow(s.board, mover, size, set()):
            moves.append("grow")
            if self._balancing_available(s):
                moves.append("grow_place")  # second player's one-time grow+place
        if not moves:
            moves.append("pass")
        return moves

    def apply_move(self, s: SympleState, move: str, rng=None) -> SympleState:
        mover = s.to_move
        size = s.size

        # ---- entering grow-mode ----
        if move in ("grow", "grow_place"):
            if not self._groups_that_can_grow(s.board, mover, size, set()):
                raise ValueError("no group can grow")
            if move == "grow_place" and not self._balancing_available(s):
                raise ValueError("balancing grow+place not available")
            return self._copy(s,
                              growing=True,
                              grown_cells=(),
                              balancing_place=(move == "grow_place"),
                              last=())

        # ---- mid grow-turn: a growth cell, or finishing ----
        if s.growing:
            if move == "growdone":
                # The grow turn is complete (possibly with a balancing place skipped).
                return self._end_turn(s, mark_grown=True)
            c, r = _cell(move)
            # If a balancing place is owed and this cell is a NEW-group cell, it's the place.
            if s.balancing_place:
                forbidden = set(s.grown_cells)
                pend = self._groups_that_can_grow(s.board, mover, size, forbidden)
                if not pend and (c, r) in set(_new_group_cells(s.board, mover, size)):
                    board = dict(s.board)
                    board[(c, r)] = mover
                    ns = self._copy(s, board=board, last=(s.last + ((c, r),)))
                    return self._end_turn(ns, mark_grown=True)
            # Otherwise this is a growth stone for the current target group.
            self._validate_growth(s, (c, r))
            board = dict(s.board)
            board[(c, r)] = mover
            # The merge rule is handled implicitly: any group containing this
            # newly placed stone is now "already grown" (g & grown_cells), so a
            # stone bridging 2+ ungrown groups grows all of them at once, and
            # none of them can grow again this turn.
            ns = self._copy(s,
                            growing=True,
                            board=board,
                            grown_cells=(s.grown_cells + ((c, r),)),
                            last=(s.grown_cells + ((c, r),)))
            # If no more growable groups remain and no balancing place owed, auto-finish.
            forbidden = set(ns.grown_cells)
            pend = self._groups_that_can_grow(ns.board, mover, size, forbidden)
            if not pend and not ns.balancing_place:
                return self._end_turn(ns, mark_grown=True)
            return ns

        # ---- fresh turn, not growing ----
        if move == "pass":
            return self._end_turn(s, mark_grown=False)
        # PLACE a new group.
        c, r = _cell(move)
        if (c, r) not in set(_new_group_cells(s.board, mover, size)):
            raise ValueError(f"illegal new-group placement {move!r}")
        board = dict(s.board)
        board[(c, r)] = mover
        ns = self._copy(s, board=board, last=((c, r),))
        return self._end_turn(ns, mark_grown=False)

    # ---------------------------------------------------------------- helpers
    def _validate_growth(self, s: SympleState, cell: tuple) -> None:
        mover = s.to_move
        size = s.size
        forbidden = set(s.grown_cells)
        pend = self._groups_that_can_grow(s.board, mover, size, forbidden)
        if not pend:
            raise ValueError("no group left to grow")
        target = pend[0]
        legal = set(_growth_cells_for(s.board, target, mover, size, forbidden))
        if cell not in legal:
            raise ValueError(f"illegal growth cell {cell} for current group")

    def _copy(self, s: SympleState, **kw) -> SympleState:
        base = dict(
            size=s.size, P=s.P, board=s.board, to_move=s.to_move,
            grown_ever=s.grown_ever, ply=s.ply, growing=s.growing,
            grown_cells=s.grown_cells,
            balancing_place=s.balancing_place, last=s.last,
            winner=s.winner, done=s.done,
        )
        base.update(kw)
        # board copy if not explicitly replaced
        if "board" not in kw:
            base["board"] = dict(s.board)
        return SympleState(**base)

    def _end_turn(self, s: SympleState, mark_grown: bool) -> SympleState:
        """Finish the current player's turn: clear transient grow state, flip
        the player (skipping a player with no action), and check for game end."""
        grown_ever = s.grown_ever or (mark_grown and bool(s.grown_cells))
        ply = s.ply + 1
        board = dict(s.board)

        # Game end: board full, or hard ply cap.
        winner = None
        done = False
        cap = HARD_PLY_CAP_FACTOR * s.size * s.size
        if _board_full(s) or ply >= cap:
            winner = self._winner_by_score(board, s.size, s.P)
            done = True

        nxt = 1 - s.to_move
        base = SympleState(
            size=s.size, P=s.P, board=board, to_move=nxt,
            grown_ever=grown_ever, ply=ply,
            growing=False, grown_cells=(),
            balancing_place=False, last=s.last, winner=winner, done=done,
        )
        if done:
            return base
        # If the next player has no legal action AND the player who just moved
        # also can't act -> board is effectively dead -> end by score. Otherwise
        # skip a player who can only pass only if BOTH cannot act.
        if self._has_action(base):
            return base
        # next player cannot act; hand back to the mover
        back = SympleState(
            size=s.size, P=s.P, board=board, to_move=s.to_move,
            grown_ever=grown_ever, ply=ply,
            growing=False, grown_cells=(),
            balancing_place=False, last=s.last, winner=None, done=False,
        )
        if self._has_action(back):
            return back
        # neither can act -> terminal by score
        winner = self._winner_by_score(board, s.size, s.P)
        return SympleState(
            size=s.size, P=s.P, board=board, to_move=nxt,
            grown_ever=grown_ever, ply=ply,
            growing=False, grown_cells=(),
            balancing_place=False, last=s.last, winner=winner, done=True,
        )

    def _has_action(self, s: SympleState) -> bool:
        mover = s.to_move
        if _new_group_cells(s.board, mover, s.size):
            return True
        if self._groups_that_can_grow(s.board, mover, s.size, set()):
            return True
        return False

    def score(self, board: dict, player: int, size: int, P: int) -> int:
        stones = sum(1 for v in board.values() if v == player)
        ngroups = len(_groups(board, player, size))
        return stones - P * ngroups

    def _winner_by_score(self, board: dict, size: int, P: int) -> int:
        a = self.score(board, BLACK, size, P)
        b = self.score(board, WHITE, size, P)
        if a > b:
            return BLACK
        if b > a:
            return WHITE
        return -1  # draw

    # ------------------------------------------------------------- terminal
    def is_terminal(self, s: SympleState) -> bool:
        return s.done

    def returns(self, s: SympleState) -> list[float]:
        if not s.done or s.winner is None or s.winner == -1:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # ------------------------------------------------------------- serialize
    def serialize(self, s: SympleState) -> dict:
        return {
            "size": s.size,
            "P": s.P,
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "grown_ever": s.grown_ever,
            "ply": s.ply,
            "growing": s.growing,
            "grown_cells": [f"{c},{r}" for (c, r) in s.grown_cells],
            "balancing_place": s.balancing_place,
            "last": [f"{c},{r}" for (c, r) in s.last],
            "winner": s.winner,
            "done": s.done,
        }

    def deserialize(self, d: dict) -> SympleState:
        return SympleState(
            size=d["size"],
            P=d["P"],
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            grown_ever=d.get("grown_ever", False),
            ply=d.get("ply", 0),
            growing=d.get("growing", False),
            grown_cells=tuple(_cell(x) for x in d.get("grown_cells", [])),
            balancing_place=d.get("balancing_place", False),
            last=tuple(_cell(x) for x in d.get("last", [])),
            winner=d.get("winner"),
            done=d.get("done", False),
        )

    def describe_move(self, s: SympleState, move: str) -> str:
        if move == "grow":
            return "grow all groups"
        if move == "grow_place":
            return "grow all + place (balancing)"
        if move == "growdone":
            return "end grow"
        if move == "pass":
            return "pass"
        if s.growing:
            return f"grow {move}"
        return f"place {move}"

    # ------------------------------------------------------------- render
    def render(self, s: SympleState, perspective=None) -> dict:
        names = {BLACK: "Black", WHITE: "White"}
        pieces = [
            {"cell": f"{c},{r}", "owner": p, "label": ""}
            for (c, r), p in s.board.items()
        ]
        highlights = [{"cell": f"{c},{r}", "kind": "last-move"} for (c, r) in s.last]

        sB = self.score(s.board, BLACK, s.size, s.P)
        sW = self.score(s.board, WHITE, s.size, s.P)
        gB = len(_groups(s.board, BLACK, s.size))
        gW = len(_groups(s.board, WHITE, s.size))
        score_str = (f"P={s.P} | Black {sB} ({gB} grp) vs White {sW} ({gW} grp)")

        if s.done:
            if s.winner == -1 or s.winner is None:
                caption = f"Draw. {score_str}"
            else:
                caption = f"{names[s.winner]} wins. {score_str}"
        elif s.growing:
            verb = "growing (+ place owed)" if s.balancing_place else "growing"
            caption = f"{names[s.to_move]} {verb}. {score_str}"
        else:
            caption = f"{names[s.to_move]} to move. {score_str}"

        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
