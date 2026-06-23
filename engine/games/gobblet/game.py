"""Gobblet (Thierry Denoual / Blue Orange) -- nesting tic-tac-toe.

The 2nd platform render-primitive investment: the NESTING glyph. Each cup is
drawn via the RenderSpec ``"size": <1..4>`` field (a disc scaled by size, so a
bigger cup visibly covers a smaller one). We emit ONLY the TOP cup of each
cell's nest -- what is underneath is hidden, exactly as in the physical game --
and the off-board nested stacks ride the existing ``reserve`` tray + click-to-
drop mechanic (the size DIGIT is the reserve "letter"; a placement drop move is
``"<size>@c,r"``).

Rules as implemented (4x4 original; see rules.md, verified against the Blue
Orange rulebook / Wikipedia / UltraBoardGames):

* Board 4x4, coords "c,r". Each player owns 12 cups = THREE off-board nested
  STACKS, each holding sizes 4(big),3,2,1 nested. Only the TOP (largest
  remaining) cup of a stack is available to place.
* A cell is an ordered NEST of (owner,size) cups; only the top cup is
  visible/controllable.
* A cup may be placed onto / moved onto another cell's TOP cup ONLY IF strictly
  larger (size > covered size), or onto an empty cell. You may gobble ANY
  smaller cup -- yours or the opponent's -- not just the next size down.
* A turn is EITHER (a) place the top cup of one of your off-board stacks
  (drop "<size>@c,r"), OR (b) MOVE one of your cups that is the TOP of some cell
  to another cell ("c,r>c2,r2"); moving UNCOVERS the cup beneath its old cell.
* OFF-BOARD-GOBBLE restriction: a cup placed FROM OFF the board may cover an
  OPPONENT's on-board cup ONLY IF that opponent cup is part of a line in which
  the opponent has THREE same-colour tops. (On-board cups gobble freely; and a
  drop may always cover an EMPTY cell or your OWN cup.)
* WIN: four of your colour showing as the TOP cup along a row / column /
  diagonal. Re-evaluated after every move (uncovering can change tops):
    - move creates the MOVER's 4-in-a-row -> mover wins;
    - move (by uncovering) creates only the OPPONENT's 4-in-a-row -> opponent
      wins;
    - if BOTH appear at once -> the MOVER wins (your completed line takes
      priority; documented tie-break).
* Termination guard: a ply cap -> draw (Gobblet can shuffle indefinitely).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

PLY_CAP = 400  # defensive: Gobblet has no natural draw; cap shuffling -> draw


@dataclass
class GobbletState:
    # board[(c, r)] -> list of (owner, size) cups, bottom -> top (top == [-1])
    board: dict = field(default_factory=dict)
    # stacks[owner] -> list of 3 (or 2) stacks, each a list of sizes bottom->top
    #   e.g. [[1,2,3,4],[1,2,3,4],[1,2,3,4]] ; the TOP (largest) is sizes[-1]
    stacks: dict = field(default_factory=dict)
    to_move: int = 0
    winner: Optional[int] = None  # 0, 1, or None
    width: int = 4
    ply: int = 0


def _cell(s: str) -> tuple:
    c, r = s.split(",")
    return int(c), int(r)


def _lines(n: int) -> list:
    L = []
    for i in range(n):
        L.append([(c, i) for c in range(n)])  # rows
        L.append([(i, r) for r in range(n)])  # cols
    L.append([(i, i) for i in range(n)])       # main diag
    L.append([(i, n - 1 - i) for i in range(n)])  # anti diag
    return L


class Gobblet(Game):
    uid = "gobblet"
    name = "Gobblet"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> GobbletState:
        options = options or {}
        n = int(options.get("size", 4))
        if n == 3:
            # Gobblet Gobblers: 3x3, 2 stacks of sizes 1..3 per player.
            sizes = [1, 2, 3]
            nstacks = 2
        else:
            n = 4
            sizes = [1, 2, 3, 4]
            nstacks = 3
        stacks = {0: [list(sizes) for _ in range(nstacks)],
                  1: [list(sizes) for _ in range(nstacks)]}
        return GobbletState(board={}, stacks=stacks, to_move=0, width=n)

    def current_player(self, s: GobbletState) -> int:
        return s.to_move

    # --- helpers ----------------------------------------------------------
    @staticmethod
    def _top(s: GobbletState, cell) -> Optional[tuple]:
        nest = s.board.get(cell)
        return nest[-1] if nest else None

    def _restricted(self, n: int) -> bool:
        """Off-board-gobble restriction only applies to the 4x4 original."""
        return n == 4

    def _opp_three_cells(self, s: GobbletState, opp: int) -> set:
        """Cells whose TOP cup belongs to `opp` and lies on a line where `opp`
        owns >= 3 of the tops -- the only opponent cups a DROP may cover."""
        n = s.width
        out = set()
        for line in _lines(n):
            tops = [self._top(s, c) for c in line]
            cnt = sum(1 for t in tops if t and t[0] == opp)
            if cnt >= 3:
                for c, t in zip(line, tops):
                    if t and t[0] == opp:
                        out.add(c)
        return out

    def legal_moves(self, s: GobbletState) -> list:
        if self.is_terminal(s):
            return []
        n = s.width
        me = s.to_move
        opp = 1 - me
        cells = [(c, r) for c in range(n) for r in range(n)]
        moves = []

        # (a) DROPS from off-board stacks: only distinct top sizes available.
        avail_sizes = sorted({st[-1] for st in s.stacks[me] if st})
        opp_three = self._opp_three_cells(s, opp) if self._restricted(n) else None
        for size in avail_sizes:
            for cell in cells:
                top = self._top(s, cell)
                if top is None:
                    moves.append(f"{size}@{cell[0]},{cell[1]}")
                    continue
                t_owner, t_size = top
                if size <= t_size:
                    continue  # must be strictly larger
                if t_owner == opp and self._restricted(n) and cell not in opp_three:
                    continue  # drop may not cover a loose opponent cup
                moves.append(f"{size}@{cell[0]},{cell[1]}")

        # (b) MOVES of an on-board top cup I control to another cell.
        for src in cells:
            top = self._top(s, src)
            if top is None or top[0] != me:
                continue
            _, size = top
            for dst in cells:
                if dst == src:
                    continue
                dtop = self._top(s, dst)
                if dtop is None:
                    moves.append(f"{src[0]},{src[1]}>{dst[0]},{dst[1]}")
                elif size > dtop[1]:  # on-board cups gobble freely
                    moves.append(f"{src[0]},{src[1]}>{dst[0]},{dst[1]}")
        return moves

    def apply_move(self, s: GobbletState, move: str, rng=None) -> GobbletState:
        board = {k: list(v) for k, v in s.board.items()}
        stacks = {p: [list(st) for st in s.stacks[p]] for p in s.stacks}
        me = s.to_move

        if "@" in move:
            size_s, cell_s = move.split("@")
            size = int(size_s)
            cell = _cell(cell_s)
            # remove from the first off-board stack whose top is this size
            for st in stacks[me]:
                if st and st[-1] == size:
                    st.pop()
                    break
            board.setdefault(cell, []).append((me, size))
        else:
            src_s, dst_s = move.split(">")
            src, dst = _cell(src_s), _cell(dst_s)
            cup = board[src].pop()           # lift the top cup (uncovers below)
            if not board[src]:
                del board[src]
            board.setdefault(dst, []).append(cup)

        ply = s.ply + 1
        ns = GobbletState(board=board, stacks=stacks, to_move=1 - me,
                          winner=None, width=s.width, ply=ply)
        ns.winner = self._eval_winner(ns, mover=me)
        return ns

    def _eval_winner(self, s: GobbletState, mover: int) -> Optional[int]:
        """Lines of 4 (or 3) same-colour tops. Mover's own line wins the
        tie-break if both colours complete at once (documented choice)."""
        n = s.width
        mover_win = False
        opp_win = False
        for line in _lines(n):
            tops = [self._top(s, c) for c in line]
            if all(t is not None for t in tops):
                owners = {t[0] for t in tops}
                if len(owners) == 1:
                    w = owners.pop()
                    if w == mover:
                        mover_win = True
                    else:
                        opp_win = True
        if mover_win:
            return mover
        if opp_win:
            return 1 - mover
        return None

    def is_terminal(self, s: GobbletState) -> bool:
        return s.winner is not None or s.ply >= PLY_CAP

    def returns(self, s: GobbletState) -> list:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # --- serialization ----------------------------------------------------
    def serialize(self, s: GobbletState) -> dict:
        return {
            "board": {f"{c},{r}": [[o, z] for (o, z) in nest]
                      for (c, r), nest in s.board.items()},
            "stacks": {str(p): [list(st) for st in sts]
                       for p, sts in s.stacks.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "width": s.width,
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> GobbletState:
        return GobbletState(
            board={_cell(k): [(o, z) for (o, z) in nest]
                   for k, nest in d["board"].items()},
            stacks={int(p): [list(st) for st in sts]
                    for p, sts in d["stacks"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            width=d["width"],
            ply=d["ply"],
        )

    # --- rendering --------------------------------------------------------
    def render(self, s: GobbletState, perspective=None) -> dict:
        n = s.width
        pieces = []
        for cell, nest in s.board.items():
            if not nest:
                continue
            owner, size = nest[-1]  # ONLY the top cup is shown
            pieces.append({
                "cell": f"{cell[0]},{cell[1]}",
                "owner": owner,
                "size": size,
            })
        # Off-board reserve: how many cups of each top-available size per seat.
        reserve = {}
        for p in (0, 1):
            counts = {}
            for st in s.stacks[p]:
                if st:
                    z = st[-1]  # only the TOP of each stack is placeable
                    counts[str(z)] = counts.get(str(z), 0) + 1
            reserve[str(p)] = counts

        names = {0: "Red", 1: "Blue"}
        if s.winner is not None:
            cap = f"{names[s.winner]} wins"
        elif s.ply >= PLY_CAP:
            cap = "Draw (ply cap)"
        else:
            cap = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": n, "height": n},
            "pieces": pieces,
            "reserve": reserve,
            "highlights": [],
            "caption": cap,
        }

    def describe_move(self, s: GobbletState, move: str) -> str:
        if "@" in move:
            size_s, cell_s = move.split("@")
            return f"drop size-{size_s} @ {cell_s}"
        src_s, dst_s = move.split(">")
        return f"{src_s} -> {dst_s}"
