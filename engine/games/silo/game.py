"""Silo -- Mark Steere's 2021 1xN stacking / consolidation game.

A 1xN strip is set up with alternating single-colour stacks (default 1x6 with
stacks of 3: cells 0,2,4 hold three red checkers each and cells 1,3,5 hold three
blue checkers each, 18 checkers in all -- Fig 1 of the rules).

The two players, **Red** and **Blue**, sit on OPPOSITE sides of the board, so
"your right" is the opposite direction for each: Red moves toward the high-index
end (cell W-1), Blue moves toward the low-index end (cell 0). Red moves first,
then they alternate. Passing is not allowed, but a player with no legal move is
skipped. Silo uses the **pie rule**: on Blue's first turn only, Blue may "swap"
(switch colours / claim the first move) instead of moving.

A move: take your **highest** (topmost) own checker within a stack and move it one
square to *your* right, **carrying with it any enemy checkers stacked above it**
(everything above your highest own checker is, by definition, enemy). Drop that
carried substack on TOP of the destination square's stack (or onto the empty
square). One substack per turn.

Object: get **all** of your checkers into **one contiguous substack** -- a single
unbroken run of your colour inside one cell (there may be enemy checkers above
and/or below the run). Fig 2 shows Red having won.

Termination: the game is finite in practice but is not obviously loop-free
(carried enemy checkers move backward), so a hard ply cap yields an honest DRAW.
A genuine both-players-stuck position implies a completed run (a winner is
detected first), so the only draw is the ply cap.

Board is a 1xW square strip; cells are "c,0". A move is the path "c,0>d,0" where
d = c +/- 1 in the mover's right direction. The pie action is the string "swap".
Stacks render as Lasca-style towers via `piece.stack` (owners, bottom -> top).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

RED, BLUE = 0, 1

# Named setups: (width, height-per-stack).
SETUPS = {
    "1x6": (6, 3),   # default -- Fig 1
    "1x8": (8, 4),   # the larger setup mentioned in the rules ("a 1x8 board and stacks of height 4")
}


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _dir(player):
    """The mover's 'right' as a delta on the cell index."""
    return 1 if player == RED else -1


@dataclass
class SState:
    board: list = field(default_factory=list)   # list[cell]; cell = list of owners bottom->top
    width: int = 6
    height: int = 3
    to_move: int = RED
    ply: int = 0
    swapped: bool = False
    winner: object = None                        # 0 / 1 / None
    draw: bool = False


class Silo(Game):
    uid = "silo"
    name = "Silo"

    @property
    def num_players(self):
        return 2

    # ---- geometry / helpers ------------------------------------------------
    def _n(self, st):
        """Number of checkers each player owns."""
        return (st.width // 2) * st.height

    def _ply_cap(self, st):
        return 45 * self._n(st)

    @staticmethod
    def _has_move(board, player, width):
        dr = _dir(player)
        for c, cell in enumerate(board):
            if player in cell and 0 <= c + dr < width:
                return True
        return False

    def _next_mover(self, board, mover, width):
        """Who moves next: opponent, or the mover again if the opponent is
        skipped; None if neither can move (unreachable without a winner)."""
        opp = 1 - mover
        if self._has_move(board, opp, width):
            return opp
        if self._has_move(board, mover, width):
            return mover
        return None

    @staticmethod
    def _do_move(board, c, dst, player):
        """Return a new board after moving player's highest checker in cell c
        (carrying enemies above it) onto the top of cell dst."""
        nb = [list(cell) for cell in board]
        cell = nb[c]
        # topmost own checker
        i = max(idx for idx, o in enumerate(cell) if o == player)
        sub = cell[i:]
        nb[c] = cell[:i]
        nb[dst] = nb[dst] + sub
        return nb

    def _won(self, board, player, n):
        """True iff all n of player's checkers form one contiguous run in one cell."""
        locs = [(c, idx)
                for c, cell in enumerate(board)
                for idx, o in enumerate(cell) if o == player]
        if len(locs) != n:
            return False
        cells = {c for c, _ in locs}
        if len(cells) != 1:
            return False
        idxs = sorted(idx for _, idx in locs)
        return idxs == list(range(idxs[0], idxs[0] + len(idxs)))

    def _check_winner(self, board, mover, n):
        if self._won(board, mover, n):
            return mover
        opp = 1 - mover
        if self._won(board, opp, n):
            return opp
        return None

    # ---- lifecycle ---------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        setup = str(opts.get("setup", "1x6"))
        width, height = SETUPS.get(setup, SETUPS["1x6"])
        board = []
        for c in range(width):
            colour = RED if c % 2 == 0 else BLUE
            board.append([colour] * height)
        return SState(board=board, width=width, height=height, to_move=RED, ply=0)

    def current_player(self, st):
        return st.to_move

    def legal_moves(self, st):
        if st.winner is not None or st.draw:
            return []
        p = st.to_move
        dr = _dir(p)
        moves = []
        for c, cell in enumerate(st.board):
            if p in cell and 0 <= c + dr < st.width:
                moves.append(f"{c},0>{c + dr},0")
        # Pie rule: Blue's first turn only.
        if (not st.swapped) and st.ply == 1 and p == BLUE:
            moves.append("swap")
        return moves

    def apply_move(self, st, move, rng=None):
        n = self._n(st)
        p = st.to_move

        if move == "swap":
            # Reflect + recolour: the game symmetry that swaps the two roles,
            # keeping seat 0 = Red. Net effect: Blue claims the opening move.
            nb = [[1 - o for o in st.board[st.width - 1 - c]]
                  for c in range(st.width)]
            ns = SState(board=nb, width=st.width, height=st.height,
                        to_move=RED, ply=st.ply + 1, swapped=True)
            nm = self._next_mover(nb, BLUE, st.width)  # after swap it's Red's move
            # (Red is the seat that now responds; resolve any skip defensively.)
            ns.to_move = nm if nm is not None else RED
            if nm is None:
                ns.draw = True
            return ns

        c, _ = _cell(move.split(">")[0])
        dst, _ = _cell(move.split(">")[1])
        nb = self._do_move(st.board, c, dst, p)

        winner = self._check_winner(nb, p, n)
        ns = SState(board=nb, width=st.width, height=st.height,
                    to_move=p, ply=st.ply + 1, swapped=st.swapped)
        if winner is not None:
            ns.winner = winner
            return ns
        nm = self._next_mover(nb, p, st.width)
        if nm is None:
            ns.draw = True
            return ns
        ns.to_move = nm
        if ns.ply >= self._ply_cap(st):
            ns.draw = True
        return ns

    def is_terminal(self, st):
        return st.winner is not None or st.draw

    def returns(self, st):
        if st.winner == RED:
            return [1.0, -1.0]
        if st.winner == BLUE:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, st):
        return {
            "board": [list(cell) for cell in st.board],
            "width": st.width,
            "height": st.height,
            "to_move": st.to_move,
            "ply": st.ply,
            "swapped": st.swapped,
            "winner": st.winner,
            "draw": st.draw,
        }

    def deserialize(self, d):
        return SState(
            board=[list(cell) for cell in d["board"]],
            width=d["width"],
            height=d["height"],
            to_move=d["to_move"],
            ply=d.get("ply", 0),
            swapped=d.get("swapped", False),
            winner=d.get("winner"),
            draw=d.get("draw", False),
        )

    def describe_move(self, st, move):
        if move == "swap":
            return "swap (pie)"
        src = move.split(">")[0]
        dst = move.split(">")[1]
        c, _ = _cell(src)
        d, _ = _cell(dst)
        cell = st.board[c]
        p = st.to_move
        i = max(idx for idx, o in enumerate(cell) if o == p)
        carried = len(cell) - i - 1
        tag = f" +{carried}" if carried else ""
        return f"{c}→{d}{tag}"

    def render(self, st, perspective=None):
        pieces = []
        for c, cell in enumerate(st.board):
            if not cell:
                continue
            pieces.append({
                "cell": f"{c},0",
                "owner": cell[-1],            # controller = top checker's owner
                "stack": list(cell),          # owners bottom -> top
                "label": "",
            })
        names = {RED: "Red", BLUE: "Blue"}
        if st.winner is not None:
            caption = f"{names[st.winner]} wins"
        elif st.draw:
            caption = "Draw"
        else:
            side = "→ right" if st.to_move == RED else "left ←"
            caption = f"{names[st.to_move]} to move ({side})"
        return {
            "board": {"type": "square", "width": st.width, "height": 1},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
