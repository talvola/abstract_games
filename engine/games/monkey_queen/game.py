"""Monkey Queen -- Mark Steere, January 2011.

A 12x12 checkerboard regicide game.  Each player owns exactly ONE *queen* -- a
single-colour stack of two or more checkers, starting 20 high on **g1** (Ivory)
and **f12** (Cigar) -- plus any number of *babies*, which are singletons of the
player's own colour.

Every piece captures exactly like a chess queen: slide any distance along one of
the eight directions over EMPTY squares and take the first enemy piece you reach,
by replacement (the whole enemy stack is removed from the game).  A capturing
queen move carries the WHOLE stack and leaves nothing behind.

Non-capturing moves differ by piece:

* a **queen** slides like a chess queen but **leaves its bottom checker behind
  on the square it came from** -- it gives birth to a baby and loses one
  checker.  A queen of height two therefore has no non-capturing move at all
  (it would stop being a queen).
* a **baby** slides like a chess queen but only to a square that **strictly
  shortens its straight-line (Euclidean) distance to the ENEMY queen**.  Equal
  distance is not enough (Figure 6 of the rule sheet).

There is never an obligation to capture.

**Object:** kill the enemy queen, or leave your opponent with no legal move --
the player to move with no legal move LOSES.  A draw cannot occur; see
``rules.md`` for the monovariant that proves the game always ends.

The **pie rule** is part of the published rules: on Cigar's first turn he may
instead play ``swap`` and claim Ivory's opening as his own.

Rules verified against the designer's own rule sheet (HTML, and its nine
figures): https://www.marksteeregames.com/Monkey_Queen_rules.html
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 12
IVORY, CIGAR = 0, 1
NAMES = {IVORY: "Ivory", CIGAR: "Cigar"}

# The eight chess-queen directions, in a fixed order so move lists are stable.
DIRS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))

# The largest squared Euclidean distance between two squares of the board.
MAX_D2 = 2 * (SIZE - 1) ** 2                       # 242

# Starting squares, read off Figure 1 of the rule sheet by pixel-measuring the
# printed 12x12 grid: the ivory 20-stack sits on g1 and the cigar 20-stack on
# f12.  The two are 180-degree rotations of one another, which is what makes the
# pie-rule swap below an exact symmetry of the game.
START = {IVORY: (6, 0), CIGAR: (5, 11)}

# "More advanced players may wish to start the game with stacks of 20 or more
# checkers" -- the manifest offers 20 (published default), 30 and 40.
HEIGHTS = (20, 30, 40)
MAX_START = max(HEIGHTS)

PIE_RULE = True     # "The pie rule is used in Monkey Queen."


def ply_cap(start: int = MAX_START) -> int:
    """A PROVABLY DEAD termination backstop, derived from the game's own bound.

    Let ``H`` be the total number of checkers on the board, ``Q`` the sum of the
    two queens' heights, and ``D`` the sum, over every baby, of the SQUARED
    distance from that baby to the enemy queen.  Then every move strictly
    decreases the triple ``(H, Q, D)`` lexicographically:

    * a **capture** deletes an entire enemy stack, so ``H`` drops by >= 1;
    * a **queen non-capturing move** keeps ``H`` (one checker becomes a baby) and
      drops that queen's height by one, so ``Q`` drops by exactly 1;
    * a **baby non-capturing move** keeps ``H`` and ``Q`` and strictly shortens
      that baby's own distance to the enemy queen, while every other baby and
      both queens stay put -- so ``D`` strictly drops.

    The LEXICOGRAPHIC order on triples of naturals is well-founded, so the game
    must end.  (The one pie swap is an isometry: it preserves all three.)
    Neither ``H`` nor ``Q`` ever increases anywhere in the game, and both stay
    >= 4 while play CONTINUES (each side keeps a queen of height >= 2), so with
    ``m = 2*start - 4``:

    * **births <= m** -- each drops ``Q`` by exactly one, and ``Q >= 4`` after
      every one of them (the mover keeps a queen of height >= 2, so does the
      opponent, or the game is already over);
    * **captures <= m + 1** -- at most ``m`` of them while play continues, PLUS
      the game-ending queen kill, which is the one capture after which ``H >= 4``
      need NOT hold.  Dropping that ``+ 1`` is how this bound gets published one
      ply short;
    * **D <= m * MAX_D2** (at most ``m`` babies, each at squared distance
      <= MAX_D2), and only a capture or a birth can reset it.  The pie swap is an
      *isometry* -- it leaves ``H``, ``Q`` and ``D`` exactly as they were -- so
      the baby-step runs either side of it share one ``D`` budget and it does not
      buy an extra run.

    Those <= ``2m + 1`` resetting plies cut the baby-steps into at most
    ``2m + 1`` runs (there is no run after the game-ending capture), each of
    length <= ``m * MAX_D2``, so counting the one pie swap:

        plies <= (2m + 1) + 1 + (2m + 1) * m * MAX_D2

    For the default 20-high start that is 636 050 plies; the constant below uses
    the largest offered start so it is option-independent.
    """
    m = 2 * start - 4
    return 2 * m + 2 + (2 * m + 1) * m * MAX_D2


PLY_CAP = ply_cap()                                # 2 814 130 -- never reached


def _cell(txt: str):
    c, r = txt.split(",")
    return int(c), int(r)


def cid(c: int, r: int) -> str:
    return f"{c},{r}"


def alg(c: int, r: int) -> str:
    """'6,0' -> 'g1' -- the rule sheet's / a1-l12 algebraic notation."""
    return f"{chr(ord('a') + c)}{r + 1}"


def on_board(c: int, r: int) -> bool:
    return 0 <= c < SIZE and 0 <= r < SIZE


def d2(a, b) -> int:
    """Squared Euclidean distance -- exact integer arithmetic, no floats."""
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


@dataclass
class MQState:
    board: dict = field(default_factory=dict)   # (c, r) -> (owner, height)
    to_move: int = IVORY
    ply: int = 0
    last: Optional[str] = None                  # last move string (for highlights)
    winner: Optional[int] = None                # set when a QUEEN is killed


class MonkeyQueen(Game):
    """Monkey Queen (Mark Steere, January 2011)."""

    @property
    def num_players(self):
        return 2

    # ---------------------------------------------------------------- setup
    def initial_state(self, options=None, rng=None) -> MQState:
        opts = options or {}
        h = int(opts.get("height", 20))
        if h not in HEIGHTS:
            h = 20
        board = {START[IVORY]: (IVORY, h), START[CIGAR]: (CIGAR, h)}
        return MQState(board=board, to_move=IVORY, ply=0)

    def current_player(self, state):
        return state.to_move

    # ------------------------------------------------------------ geometry
    @staticmethod
    def queen_of(s: MQState, player: int):
        """The cell of `player`'s queen (their unique stack of height >= 2)."""
        for cell, (o, h) in s.board.items():
            if o == player and h >= 2:
                return cell
        return None

    def queen_attacked(self, s: MQState, defender: int) -> bool:
        """Could the opponent capture `defender`'s queen from where they stand?

        This is a REVERSE lookup -- it fires rays OUT of the queen's square and
        asks who is at the end of each -- and therefore a different code path
        from move generation.  It is exact because captures have no height or
        piece restriction: any enemy piece with a clear line to the queen can
        take it, and 'sees along a clear line' is symmetric.
        """
        q = self.queen_of(s, defender)
        if q is None:
            return False
        c, r = q
        for dc, dr in DIRS:
            k = 1
            while True:
                tc, tr = c + k * dc, r + k * dr
                if not on_board(tc, tr):
                    break
                occ = s.board.get((tc, tr))
                if occ is not None:
                    if occ[0] != defender:
                        return True
                    break
                k += 1
        return False

    # ------------------------------------------------------------ movegen
    def board_moves(self, s: MQState, player: int) -> list:
        """Every legal board move for `player` (the pie swap is not a board move)."""
        board = s.board
        eq = self.queen_of(s, 1 - player)          # the enemy queen: babies' target
        out = []
        for (c, r) in sorted(board):
            owner, h = board[(c, r)]
            if owner != player:
                continue
            here = (c, r)
            baby = h == 1
            can_birth = h >= 3          # a queen of height two may not give birth
            for dc, dr in DIRS:
                k = 1
                while True:
                    tc, tr = c + k * dc, r + k * dr
                    if not on_board(tc, tr):
                        break
                    occ = board.get((tc, tr))
                    if occ is not None:
                        # First occupied square on the ray ends it either way.
                        if occ[0] != player:
                            out.append(f"{c},{r}>{tc},{tr}")     # capture
                        break
                    if baby:
                        # A baby may only move to a square strictly CLOSER
                        # (straight-line) to the enemy queen.
                        if eq is not None and d2((tc, tr), eq) < d2(here, eq):
                            out.append(f"{c},{r}>{tc},{tr}")
                    elif can_birth:
                        out.append(f"{c},{r}>{tc},{tr}")         # birth
                    k += 1
        return out

    def _all_moves(self, s: MQState) -> list:
        """Every move available to the player to move, ignoring the ply cap."""
        if s.winner is not None:
            return []
        out = self.board_moves(s, s.to_move)
        if PIE_RULE and s.ply == 1:
            out.append("swap")
        return out

    def legal_moves(self, state: MQState) -> list:
        if state.ply >= PLY_CAP:
            return []
        return self._all_moves(state)

    # ------------------------------------------------------------- apply
    @staticmethod
    def parse(move: str):
        frm_s, _, to_s = move.partition(">")
        return _cell(frm_s), _cell(to_s)

    @staticmethod
    def _rot_cell(cell):
        return (SIZE - 1 - cell[0], SIZE - 1 - cell[1])

    @classmethod
    def conjugate(cls, s: MQState) -> MQState:
        """The seat-swapping symmetry: rotate the board 180 degrees AND exchange
        the two colours.  The starting position is a fixed point of this map (g1
        and f12 are 180-degree images), the rules are direction-symmetric and
        Euclidean distance is rotation-invariant, so this is an exact isomorphism
        of the game onto itself with the seats exchanged.  It is what the pie-rule
        ``swap`` applies, and it is also the identity the selftest checks move
        generation against.
        """
        board = {cls._rot_cell(cell): (1 - o, h) for cell, (o, h) in s.board.items()}
        last = s.last
        if last is not None and ">" in last:
            frm, to = cls.parse(last)
            last = f"{cid(*cls._rot_cell(frm))}>{cid(*cls._rot_cell(to))}"
        return MQState(board=board, to_move=1 - s.to_move, ply=s.ply, last=last,
                       winner=(None if s.winner is None else 1 - s.winner))

    def apply_move(self, state: MQState, move: str, rng=None) -> MQState:
        s = state
        if move == "swap":
            # Cigar claims Ivory's opening move as his own and the players
            # exchange colours -- exactly the conjugation above, with the turn
            # passing to the seat that has now become the second player.
            ns = self.conjugate(s)
            ns.ply = s.ply + 1
            return ns

        frm, to = self.parse(move)
        board = dict(s.board)                       # values are tuples: safe copy
        owner, h = board[frm]
        victim = board.get(to)
        if victim is not None:
            # Capture by replacement: the ENTIRE moving stack relocates and the
            # entire enemy stack leaves the game.  Nothing is left behind, so a
            # queen never gives birth and kills in the same move.
            del board[frm]
            board[to] = (owner, h)
        elif h == 1:
            del board[frm]
            board[to] = (owner, 1)
        else:
            board[frm] = (owner, 1)                 # the newborn baby
            board[to] = (owner, h - 1)

        winner = owner if (victim is not None and victim[1] >= 2) else None
        return MQState(board=board, to_move=1 - s.to_move, ply=s.ply + 1,
                       last=move, winner=winner)

    # ------------------------------------------------------------ terminal
    def is_terminal(self, state: MQState) -> bool:
        # A DECISIVE RESULT OUTRANKS THE PLY CAP: both the killed-queen winner
        # and the no-legal-move loss are tested before the cap in `returns`.
        return (state.winner is not None
                or not self._all_moves(state)
                or state.ply >= PLY_CAP)

    def returns(self, state: MQState) -> list:
        if state.winner is not None:
            w = state.winner
        elif not self._all_moves(state):
            # "Deprive your opponent of legal moves" -- the player to move with
            # no move LOSES.  This is checked before the ply cap so a stuck-loss
            # delivered on the capping ply is still a loss, not a draw.
            w = 1 - state.to_move
        else:
            # Only reachable at the (provably dead) ply cap, or if `returns` is
            # called on a live position.  An honest 0-0 rather than a fabricated
            # winner; the rule sheet's "a draw cannot occur" is proved in rules.md.
            return [0.0, 0.0]
        return [1.0 if p == w else -1.0 for p in range(2)]

    # --------------------------------------------------------------- bot
    def heuristic(self, state: MQState) -> list:
        """Material, plus pressure on the enemy queen.  Returns ONE PAYOFF PER
        SEAT, as `returns` does."""
        if self.is_terminal(state):
            return self.returns(state)
        mat = [0, 0]
        close = [0.0, 0.0]
        q = [self.queen_of(state, 0), self.queen_of(state, 1)]
        for cell, (o, h) in state.board.items():
            mat[o] += h
            eq = q[1 - o]
            if h == 1 and eq is not None:
                close[o] += 1.0 - d2(cell, eq) / float(MAX_D2)
        thr = [1.0 if self.queen_attacked(state, 1 - p) else 0.0 for p in (0, 1)]
        v = ((mat[0] - mat[1])
             + 3.0 * (thr[0] - thr[1])
             + 0.6 * (close[0] - close[1]))
        x = math.tanh(v / 8.0)
        return [x, -x]

    # ------------------------------------------------------- (de)serialize
    def serialize(self, state: MQState) -> dict:
        return {
            "board": {cid(c, r): [o, h]
                      for (c, r), (o, h) in sorted(state.board.items())},
            "to_move": state.to_move,
            "ply": state.ply,
            "last": state.last,
            "winner": state.winner,
        }

    def deserialize(self, data: dict) -> MQState:
        return MQState(
            board={_cell(k): (int(v[0]), int(v[1])) for k, v in data["board"].items()},
            to_move=int(data["to_move"]),
            ply=int(data["ply"]),
            last=data["last"],
            winner=(None if data["winner"] is None else int(data["winner"])),
        )

    # --------------------------------------------------------------- notation
    def describe_move(self, state: MQState, move: str) -> str:
        who = NAMES[state.to_move]
        if move == "swap":
            return f"{who} swap (pie rule)"
        frm, to = self.parse(move)
        _o, h = state.board[frm]
        victim = state.board.get(to)
        head = ("Q" if h >= 2 else "") + alg(*frm)
        if victim is not None:
            what = "queen" if victim[1] >= 2 else "baby"
            tail = f" takes {what}"
            if victim[1] >= 2:
                tail += f" ({victim[1]})"
            return f"{who} {head}x{alg(*to)}{tail}"
        if h >= 2:
            return f"{who} {head}-{alg(*to)} (birth {alg(*frm)}, {h}>{h - 1})"
        return f"{who} {head}-{alg(*to)}"

    # --------------------------------------------------------------- render
    def render(self, state: MQState, perspective=None) -> dict:
        pieces = []
        for (c, r) in sorted(state.board):
            o, h = state.board[(c, r)]
            p = {"cell": cid(c, r), "owner": o}
            if h > 1:
                # Queen: side-view tower of same-colour bands with a height
                # badge (all checkers in a Monkey Queen stack share one colour,
                # so the badge carries all the information).  A baby stays a
                # plain disc, exactly the distinction the rule sheet's figures
                # draw between a numbered queen and an unnumbered singleton.
                p["stack"] = [o] * h
            pieces.append(p)

        highlights = []
        if state.last and ">" in state.last:
            frm, to = self.parse(state.last)
            highlights.append({"cell": cid(*frm), "kind": "last-move"})
            highlights.append({"cell": cid(*to), "kind": "last-move"})

        mat = [0, 0]
        qh = [0, 0]
        for (o, h) in state.board.values():
            mat[o] += h
            if h >= 2:
                qh[o] = h
        tally = (f"Ivory {mat[IVORY]} (Q{qh[IVORY]}) - "
                 f"Cigar {mat[CIGAR]} (Q{qh[CIGAR]})")

        if state.winner is not None:
            cap = f"{NAMES[state.winner]} wins -- enemy queen killed  ({tally})"
        elif not self._all_moves(state):
            cap = (f"{NAMES[1 - state.to_move]} wins -- {NAMES[state.to_move]} "
                   f"has no legal move  ({tally})")
        elif state.ply >= PLY_CAP:
            cap = f"Draw (ply cap)  ({tally})"
        else:
            cap = f"{NAMES[state.to_move]} to move  ({tally})"
            att = [p for p in (IVORY, CIGAR) if self.queen_attacked(state, p)]
            if att:
                cap += "  -- " + " and ".join(
                    f"{NAMES[p]}'s queen is attacked" for p in att)

        spec = {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
        }
        if PIE_RULE and state.ply == 1 and state.winner is None:
            spec["actionNames"] = {"swap": "Swap (pie rule): claim Ivory's opening"}
        return spec
