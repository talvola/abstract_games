"""Gygès (Claude Leroy, 1984) -- a no-ownership abstract race on a 6x6 board.

The 12 pieces belong to NO ONE: each is a stack of height 1, 2 or 3, and the
height is purely a MOVEMENT RANK (how many orthogonal single steps the piece
takes), not ownership. On your turn you may move only a piece in the occupied
row CLOSEST to your own side (your "active" row). A moved piece travels EXACTLY
its height in orthogonal single steps (it may change direction between steps);
every intermediate square must be empty, but the FINAL square may be occupied.
If it ends on an occupied square it does not stop there -- you either BOUNCE
(immediately continue, now moving by the height of the piece you landed on,
chaining as far as it goes) or REPLACE (pick that piece up and drop it on any
empty square that is not behind the opponent's home row, ending your move).

There is a single GOAL cell beyond each player's far edge, adjacent to every
square of the row in front of it. You WIN by landing a piece (via a fresh move
or a bounce chain) exactly on YOUR goal -- the cell beyond the opponent's home
row. The count must be exact; the goal may only be a final landing square.

Cells are "c,r" on the 6x6 grid (r grows toward player 1). The two goals are the
special cell ids "G0" (player 0's goal, beyond r=5) and "G1" (player 1's goal,
beyond r=0). A move is a ">"-separated path; bounce chains and the replacement
drop are encoded in that path (a replacement appends "R<dest>").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

W = 6
H = 6
HEIGHTS = (1, 2, 3)
PLY_CAP = 300          # defensive draw cap (Gygès has no natural draw)

# player 0 = bottom (home row r=0), player 1 = top (home row r=5)
HOME_ROW = {0: 0, 1: H - 1}
GOAL_ROW = {0: H - 1, 1: 0}      # the board row the player's goal sits beyond
GOAL_ID = {0: "G0", 1: "G1"}     # virtual goal cell ids
GOAL_OWNER = {"G0": 0, "G1": 1}  # whose goal a virtual cell is

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _sid(cr):
    return f"{cr[0]},{cr[1]}"


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


# ---------------------------------------------------------------------------
# A board square holds either nothing or a piece of height 1/2/3.
# state.board: {(c, r): height}.  Pieces are NEUTRAL -- no owner is stored.
# ---------------------------------------------------------------------------
@dataclass
class GState:
    board: dict = field(default_factory=dict)   # (c, r) -> height (1/2/3)
    to_move: int = 0
    ply: int = 0
    winner: object = None


class Gyges(Game):
    uid = "gyges"
    name = "Gygès"

    @property
    def num_players(self):
        return 2

    # ---- setup ------------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        # Fixed, documented symmetric opening: each home row holds, left->right,
        # heights 2 3 1 1 3 2 (two of each rank per row, mirror-symmetric).
        layout = [2, 3, 1, 1, 3, 2]
        board = {}
        for c in range(W):
            board[(c, HOME_ROW[0])] = layout[c]
            board[(c, HOME_ROW[1])] = layout[c]
        return GState(board=board, to_move=0)

    def current_player(self, state):
        return state.to_move

    # ---- active row -------------------------------------------------------
    def _row_order(self, player):
        """Rows from the player's own side outward."""
        if player == 0:
            return list(range(H))          # 0,1,2,...,5
        return list(range(H - 1, -1, -1))  # 5,4,3,...,0

    def _movable_sources(self, board, player):
        """Cells whose pieces the player may move this turn.

        The active row is the occupied row nearest the player. Standard rule:
        only that row's pieces move. Fallback ("unusual circumstances"): if NO
        piece in the active row has a legal move, the next occupied row opens
        up, and so on -- this guarantees a non-empty move list (termination).
        """
        rows = [r for r in self._row_order(player)
                if any((c, r) in board for c in range(W))]
        for r in rows:
            srcs = [(c, r) for c in range(W) if (c, r) in board]
            if any(self._moves_from(board, s, player) for s in srcs):
                return srcs
        return []

    # ---- movement engine --------------------------------------------------
    def _neighbors(self, cell, player):
        """Orthogonal neighbours of a BOARD cell, plus the player's goal cell
        if `cell` lies on the goal's adjacent row. Goal cells have no exits."""
        c, r = cell
        out = []
        for dc, dr in DIRS:
            nc, nr = c + dc, r + dr
            if _on(nc, nr):
                out.append((nc, nr))
        if r == GOAL_ROW[player]:
            out.append(GOAL_ID[player])     # goal adjacent to all of its row
        return out

    def _walk(self, board, start, height, player, used_edges):
        """Squares reachable from `start` in EXACTLY `height` orthogonal steps,
        threading `used_edges` (no undirected edge reused anywhere in the whole
        move): intermediate squares empty, final square may be occupied; a goal
        cell may only be a final square.

        Returns a list of (dest, edges_used_to_reach_dest). `dest` is a board
        tuple or a goal id. Only landings are reported (one entry per (dest,
        edge-set) reached); different routes to the same landing are distinct
        only by which edges they consumed (which constrains later bounce legs)."""
        out = []

        def rec(pos, steps_left, used):
            if steps_left == 0:
                out.append((pos, used))
                return
            for nb in self._neighbors(pos, player):
                edge = frozenset((pos, nb))
                if edge in used:
                    continue
                if isinstance(nb, str):           # a goal id: last step only
                    if steps_left != 1:
                        continue
                else:
                    # intermediate squares must be empty (final may be occupied)
                    if steps_left > 1 and nb in board:
                        continue
                rec(nb, steps_left - 1, used | {edge})

        rec(start, height, used_edges)
        return out

    def _moves_from(self, board, src, player):
        """All legal moves that begin by moving the piece at `src`.

        Returns a list of move strings, one canonical string per distinct
        OUTCOME (final board + win flag). Many bounce/replace routes collapse to
        the same outcome; we keep the first path found for each.
        """
        mover_h = board[src]
        # The moving piece LEAVES `src` for the whole move (so `src` is empty
        # during the chain and cannot be bounced off or block intermediates). It
        # KEEPS its original height `mover_h` throughout -- bounces change only
        # its step count for the next leg, not its rank when it finally settles.
        b = dict(board)
        b.pop(src)
        outcomes = {}   # outcome-key -> canonical move string
        self._chain(b, src, mover_h, mover_h, player, set(), _sid(src),
                    outcomes, depth=0)
        return list(outcomes.values())

    def _chain(self, board, pos, step_h, mover_h, player, used_edges, path,
               outcomes, depth):
        """Resolve a leg from `pos`, taking exactly `step_h` steps, threading the
        whole-move `used_edges`. `mover_h` is the moving piece's own (unchanging)
        height -- what it deposits when it settles. `path` is the move string so
        far. On reaching a terminal landing (empty / goal / replace) we record
        one canonical move per OUTCOME (final board + win) in `outcomes`.

        - empty landing  -> the piece settles there; move ends.
        - goal landing    -> win; ends.
        - occupied landing-> BOUNCE (continue by that piece's height; it stays)
          or REPLACE (stop here, relocate the landed-on piece).
        """
        if depth > 80:                      # safety vs pathological chains
            return
        for dest, used in self._walk(board, pos, step_h, player, used_edges):
            seg = _sid_or_goal(dest)
            npath = path + ">" + seg
            if isinstance(dest, str):       # goal -> ends (a win)
                outcomes.setdefault(("WIN", player), npath)
                continue
            if dest not in board:           # empty -> the piece settles; ends
                nb = dict(board)
                nb[dest] = mover_h
                outcomes.setdefault(self._okey(nb), npath)
                continue
            # occupied -> bounce or replace
            # (a) BOUNCE: the SAME moving piece continues by dest's height; the
            #     landed-on piece STAYS (board unchanged).
            self._chain(board, dest, board[dest], mover_h, player, used, npath,
                        outcomes, depth + 1)
            # (b) REPLACE: stop on `dest`; relocate the landed-on piece.
            for drop in self._replace_targets(board, dest):
                nb = dict(board)
                relocated = nb.pop(dest)
                nb[drop] = relocated
                nb[dest] = mover_h
                outcomes.setdefault(self._okey(nb), npath + ">R" + _sid(drop))

    def _okey(self, board):
        return tuple(sorted((c, r, h) for (c, r), h in board.items()))

    def _replace_targets(self, board, dest):
        """Empty board squares onto which the landed-on piece may be dropped.

        The standard restriction is "not behind the opponent's first row". On a
        6x6 board with goals as virtual cells, every board square is in front of
        or on a home row (none is strictly behind one), and goals are not board
        squares -- so every empty square qualifies. `board` already excludes the
        moving piece; `dest`'s piece is being relocated, so `dest` itself frees
        up but is excluded (a null relocation is pointless)."""
        targets = []
        for r in range(H):
            for c in range(W):
                cell = (c, r)
                if cell == dest or cell in board:
                    continue
                targets.append(cell)
        return targets

    # ---- legal moves ------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        srcs = self._movable_sources(state.board, state.to_move)
        out = []
        for s in srcs:
            out.extend(self._moves_from(state.board, s, state.to_move))
        return out

    # ---- apply ------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        board = dict(state.board)
        player = state.to_move
        tokens = move.split(">")
        src = _cell(tokens[0])
        # The single moving piece leaves `src` for the whole move; bounced-off
        # pieces STAY put (the board is unchanged through a bounce chain).
        moving_h = board.pop(src)
        winner = None
        last_landing = src
        for tok in tokens[1:]:
            if tok.startswith("R"):
                # REPLACE: the mover stops on the previous (occupied) landing;
                # the landed-on piece there is relocated to `drop`.
                drop = _cell(tok[1:])
                relocated_h = board.pop(last_landing)   # landed-on piece leaves
                board[drop] = relocated_h               # ...moved to drop
                board[last_landing] = moving_h          # mover settles here
                moving_h = None
                break
            if tok in ("G0", "G1"):
                # reached a goal cell -> the mover wins if it's THEIR goal
                if GOAL_OWNER[tok] == player:
                    winner = player
                moving_h = None
                break
            cell = _cell(tok)
            if cell in board:
                # BOUNCE: the same piece keeps moving; the bounced piece stays.
                last_landing = cell
                continue
            # empty landing -> the mover settles here; move ends
            board[cell] = moving_h
            moving_h = None
            last_landing = cell
            break

        ns = GState(board=board, to_move=1 - player,
                    ply=state.ply + 1, winner=winner)
        return ns

    # ---- terminal ---------------------------------------------------------
    def is_terminal(self, state):
        return state.winner is not None or state.ply >= PLY_CAP

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialise --------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {_sid(k): v for k, v in state.board.items()},
            "to_move": state.to_move,
            "ply": state.ply,
            "winner": state.winner,
        }

    def deserialize(self, d):
        return GState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            winner=d.get("winner"),
        )

    # ---- presentation -----------------------------------------------------
    def describe_move(self, state, move):
        return move.replace(">", "-")

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), h in state.board.items():
            # reuse Lasca's stack glyph: a column of `h` neutral discs. We use
            # owner = -1 (no ownership) and a height label; stack is h neutral.
            pieces.append({
                "cell": f"{c},{r}",
                "owner": None,                 # NEUTRAL: belongs to no player
                "stack": [None] * h,           # height shown as a stack of h
                "label": str(h),               # the movement rank 1/2/3
            })
        # goal cells drawn as tinted squares in two extra rows? The 6x6 board
        # has no row for goals, so we surface them via tints on the goal rows
        # and a caption. (The generic renderer is square-only; goals live just
        # beyond r=5 / r=0 and are described, not drawn as grid cells.)
        tints = {}
        # mark the two goal-adjacent rows lightly so players see where to aim
        for c in range(W):
            tints[f"{c},{GOAL_ROW[0]}"] = "#fde6a8"   # player 0 aims past here
            tints[f"{c},{GOAL_ROW[1]}"] = "#bfe3f2"   # player 1 aims past here

        if state.winner is not None:
            cap = f"Player {state.winner + 1} wins (reached their goal)"
        elif state.ply >= PLY_CAP:
            cap = "Draw (ply cap)"
        else:
            srcs = self._movable_sources(state.board, state.to_move)
            ar = srcs[0][1] if srcs else "?"
            cap = (f"Player {state.to_move + 1} to move "
                   f"(active row r={ar})")
        return {
            "board": {"type": "square", "width": W, "height": H,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }


def _sid_or_goal(p):
    return p if isinstance(p, str) else _sid(p)
