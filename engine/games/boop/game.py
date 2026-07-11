"""boop. (Scott Brady, Smirk & Dagger 2022) -- the kitten-booping N-in-a-row duel.

Board: 6x6 (the quilted "bed"), cell ids "c,r" with c,r in 0..5.

Each player has 8 KITTENS and 8 CATS in their colour. You start with the
8 Kittens in your pool; the 8 Cats begin out of play and are earned by
graduation. You always have exactly 8 ACTIVE pieces (pool + board).
(Rulebook: "Players begin the game with 8 Kittens of their color. The 8 Cats
of their color begin 'out of play'." / "You will ALWAYS have 8 active pieces.")

TURN.  Place one piece from your pool (a Kitten, or a Cat once you have one)
on any empty square. The placed piece then "boops" every ADJACENT piece
(all 8 directions): each is pushed one square directly away, UNLESS the
square behind it is occupied (then it does not move). A piece pushed off the
board returns to its owner's pool (as the same piece type). Booped pieces do
NOT cause chain reactions. KITTENS CANNOT BOOP CATS; Cats boop both Cats and
Kittens. (Rulebook: "it 'boops' all of the pieces adjacent to it, pushing
them one space away, including diagonally" / "A booped piece does not cause a
chain reaction" / "Cats CANNOT be booped by Kittens. However, Cats can boop
other Cats, as well as Kittens.")

GRADUATION (after the boop, mover's pieces only).  Three of your pieces in a
row (horizontally, vertically or diagonally) containing at least one Kitten:
all three are removed from the board and THREE CATS go to your pool (Kittens
graduate; any Cats in the line return to the pool as Cats). With multiple
rows (or >3 in a row) you choose ONE group of 3 to graduate. If all 8 of your
pieces are on the bed (and no win), you must instead/also choose: graduate a
row of 3, OR pick up any ONE of your pieces -- a picked-up Kitten graduates
into a Cat, a picked-up Cat returns to your pool. (Rulebook: "Alternatively,
if all 8 of your pieces are on the bed, you may graduate any one Kitten ...
you could place a Cat back into your pool, instead" / "if you have both a
three in a row and eight pieces on the board, choose which you would
activate.")

WIN (checked only for the MOVER, after all booped pieces settle -- official
FAQ: "The win condition happens at the END of the turn, so only the active
player can win on their turn"): three of your CATS in a row, or all 8 of
your pieces on the bed being Cats. A row you boop your OPPONENT into does
not score for them until the end of THEIR next turn (if it survives).

DRAWS (engine backstops; the physical game has no draw rule): threefold
repetition of a full position (board + pools + player to move at placement)
or a hard cap of MAX_PLIES total moves is an honest draw.

Move encoding
  placement:   "c,r=K"  /  "c,r=C"       (=CHOICE picker: Kitten or Cat)
  graduation:  "c,r=Ga,b;c,d;e,f"        (anchored on ANY cell of the row;
                                          the suffix names the whole row --
                                          each row is offered once per cell)
  pick-up:     "c,r=LIFT"                (all 8 on the bed: lift this piece)
All resolve-phase moves are single-cell paths with =CHOICE suffixes, so the
click UI never hits a prefix trap: clicking a cell either plays the only
option or opens a labelled picker (labels via spec.choiceNames).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

W = H = 6
DIRS8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
DIRS4 = [(1, 0), (0, 1), (1, 1), (1, -1)]  # line directions for rows of 3
MAX_PLIES = 600      # hard honest-draw cap (see selftest playout stats)
REP_LIMIT = 3        # threefold repetition of a placement position = draw


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _cid(c: int, r: int) -> str:
    return f"{c},{r}"


def _on(c: int, r: int) -> bool:
    return 0 <= c < W and 0 <= r < H


@dataclass
class BoopState:
    # board[(c,r)] -> (owner, kind)  kind in {"K","C"}
    board: dict = field(default_factory=dict)
    # pools[owner] -> {"K": n, "C": n}  pieces in hand (active but off-board)
    pools: dict = field(default_factory=dict)
    to_move: int = 0
    phase: str = "place"          # "place" | "resolve" (graduation choice)
    winner: Optional[int] = None  # set in apply_move
    draw: Optional[str] = None    # "repetition" | "plycap"
    ply: int = 0
    last: Optional[str] = None    # last placed cell id (highlight)
    reps: dict = field(default_factory=dict)  # position key -> count


class Boop(Game):
    uid = "boop"
    name = "boop."

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> BoopState:
        s = BoopState(board={},
                      pools={0: {"K": 8, "C": 0}, 1: {"K": 8, "C": 0}},
                      to_move=0)
        s.reps = {self._poskey(s): 1}
        return s

    def current_player(self, s: BoopState) -> int:
        return s.to_move

    # --- position bookkeeping ---------------------------------------------
    @staticmethod
    def _poskey(s: BoopState) -> str:
        cells = ";".join(f"{c},{r}:{o}{k}"
                         for (c, r), (o, k) in sorted(s.board.items()))
        pools = ",".join(str(s.pools[p][k]) for p in (0, 1) for k in ("K", "C"))
        return f"{cells}|{pools}|{s.to_move}"

    # --- line detection -----------------------------------------------------
    @staticmethod
    def _triples(board: dict, who: int):
        """All rows of exactly-3 consecutive cells owned by `who` (a 4-in-a-row
        contributes its two overlapping triples), as sorted cell tuples."""
        out = []
        for c in range(W):
            for r in range(H):
                for dc, dr in DIRS4:
                    cells = [(c + i * dc, r + i * dr) for i in range(3)]
                    if all(_on(x, y) and board.get((x, y), (None,))[0] == who
                           for x, y in cells):
                        out.append(tuple(sorted(cells)))
        return out

    def _resolve_options(self, s: BoopState):
        """(graduation triples, liftable cells) for the mover, from the board.
        All-cat triples never appear here (they are a win, checked earlier)."""
        me = s.to_move
        grads = [t for t in self._triples(s.board, me)
                 if any(s.board[c][1] == "K" for c in t)]
        my_cells = [c for c, (o, _k) in s.board.items() if o == me]
        lifts = sorted(my_cells) if len(my_cells) == 8 else []
        return grads, lifts

    @staticmethod
    def _gspec(triple) -> str:
        return "G" + ";".join(_cid(c, r) for c, r in triple)

    # --- moves ---------------------------------------------------------------
    def legal_moves(self, s: BoopState):
        if self.is_terminal(s):
            return []
        me = s.to_move
        if s.phase == "place":
            kinds = [k for k in ("K", "C") if s.pools[me][k] > 0]
            return [f"{_cid(c, r)}={k}"
                    for r in range(H) for c in range(W)
                    if (c, r) not in s.board for k in kinds]
        # resolve: one single-cell move per (cell, option)
        grads, lifts = self._resolve_options(s)
        moves = []
        for t in grads:
            spec = self._gspec(t)
            for cell in t:
                moves.append(f"{_cid(*cell)}={spec}")
        for cell in lifts:
            moves.append(f"{_cid(*cell)}=LIFT")
        return moves

    # --- turn resolution ------------------------------------------------------
    def _boop(self, board: dict, pools: dict, c: int, r: int, kind: str):
        """Resolve the placed piece's boop, mutating the (fresh) board/pools.
        Destinations are all distinct and never other booped neighbours, so
        the outcome is order-independent."""
        for dc, dr in DIRS8:
            n = (c + dc, r + dr)
            if n not in board:
                continue
            o, k = board[n]
            if kind != "C" and k == "C":
                continue                       # Kittens cannot boop Cats
            t = (c + 2 * dc, r + 2 * dr)
            if not _on(*t):
                del board[n]                   # booped off the bed -> pool
                pools[o][k] += 1
            elif t not in board:
                board[t] = board.pop(n)        # pushed one square away
            # else: blocked by the piece behind -- does not move

    def _finish_turn(self, s: BoopState) -> BoopState:
        """Hand the turn to the opponent and apply the draw backstops."""
        s.to_move = 1 - s.to_move
        s.phase = "place"
        key = self._poskey(s)
        s.reps = dict(s.reps)
        s.reps[key] = s.reps.get(key, 0) + 1
        if s.reps[key] >= REP_LIMIT:
            s.draw = "repetition"
        elif s.ply >= MAX_PLIES:
            s.draw = "plycap"
        return s

    def apply_move(self, s: BoopState, move: str, rng=None) -> BoopState:
        me = s.to_move
        board = dict(s.board)
        pools = {p: dict(h) for p, h in s.pools.items()}
        ns = BoopState(board=board, pools=pools, to_move=me, phase=s.phase,
                       winner=None, draw=None, ply=s.ply + 1, last=s.last,
                       reps=s.reps)

        cell_s, choice = move.split("=", 1)
        c, r = _cell(cell_s)

        if s.phase == "place":
            if choice not in ("K", "C"):
                raise ValueError(f"bad placement move {move!r}")
            if (c, r) in board or pools[me][choice] <= 0:
                raise ValueError(f"illegal placement {move!r}")
            pools[me][choice] -= 1
            board[(c, r)] = (me, choice)
            ns.last = cell_s
            self._boop(board, pools, c, r, choice)

            # --- end-of-turn checks (mover only; FAQ: only the active player
            # can win on their turn) ---
            triples = self._triples(board, me)
            my_board = [(o, k) for (o, k) in board.values() if o == me]
            if any(all(board[cl][1] == "C" for cl in t) for t in triples) or \
               (len(my_board) == 8 and all(k == "C" for _o, k in my_board)):
                ns.winner = me
                return ns
            grads, lifts = self._resolve_options(ns)
            noptions = len(grads) + len(lifts)
            if noptions == 0:
                return self._finish_turn(ns)
            if noptions == 1:                  # a single forced graduation
                self._graduate(board, pools, me, grads[0])
                return self._finish_turn(ns)
            ns.phase = "resolve"               # mover chooses next sub-move
            return ns

        # --- resolve phase: graduate a chosen row, or lift one piece ---------
        if choice == "LIFT":
            if board.get((c, r), (None,))[0] != me:
                raise ValueError(f"illegal lift {move!r}")
            del board[(c, r)]
            pools[me]["C"] += 1                # Kitten graduates / Cat returns
        elif choice.startswith("G"):
            triple = tuple(sorted(_cell(x) for x in choice[1:].split(";")))
            if any(board.get(cl, (None,))[0] != me for cl in triple):
                raise ValueError(f"illegal graduation {move!r}")
            self._graduate(board, pools, me, triple)
        else:
            raise ValueError(f"bad resolve move {move!r}")
        return self._finish_turn(ns)

    @staticmethod
    def _graduate(board: dict, pools: dict, me: int, triple):
        """Remove the row of 3; three Cats go to the mover's pool (Kittens
        graduate out of the game, Cats in the row return as Cats)."""
        for cl in triple:
            del board[cl]
        pools[me]["C"] += 3

    # --- terminal ----------------------------------------------------------
    def is_terminal(self, s: BoopState) -> bool:
        return s.winner is not None or s.draw is not None

    def returns(self, s: BoopState):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    # --- MCTS rollout-cutoff eval -------------------------------------------
    def heuristic(self, s: BoopState) -> list:
        """Cats earned (pool + board) dominate; on-board cats add a little."""
        import math
        sc = [0.0, 0.0]
        for p in (0, 1):
            sc[p] += s.pools[p]["C"]
        for (o, k) in s.board.values():
            if k == "C":
                sc[o] += 1.3
        bal = math.tanh((sc[0] - sc[1]) / 4.0)
        return [bal, -bal]

    # --- serialization -------------------------------------------------------
    def serialize(self, s: BoopState) -> dict:
        return {
            "board": {_cid(c, r): [o, k] for (c, r), (o, k) in s.board.items()},
            "pools": {str(p): dict(h) for p, h in s.pools.items()},
            "to_move": s.to_move,
            "phase": s.phase,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "last": s.last,
            "reps": dict(s.reps),
        }

    def deserialize(self, d: dict) -> BoopState:
        return BoopState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            pools={int(p): dict(h) for p, h in d["pools"].items()},
            to_move=d["to_move"],
            phase=d.get("phase", "place"),
            winner=d.get("winner"),
            draw=d.get("draw"),
            ply=d.get("ply", 0),
            last=d.get("last"),
            reps=dict(d.get("reps", {})),
        )

    # --- presentation ---------------------------------------------------------
    KIND_NAME = {"K": "Kitten", "C": "Cat"}

    def describe_move(self, s: BoopState, move: str) -> str:
        cell_s, choice = move.split("=", 1)
        if choice in ("K", "C"):
            return f"{self.KIND_NAME[choice]} @ {cell_s}"
        if choice == "LIFT":
            k = s.board.get(_cell(cell_s), (None, "K"))[1]
            return (f"pick up {self.KIND_NAME[k]} @ {cell_s} "
                    f"({'graduates' if k == 'K' else 'returns'} as Cat)")
        cells = choice[1:].split(";")
        return f"graduate {cells[0]} - {cells[-1]}"

    def render(self, s: BoopState, perspective=None) -> dict:
        pieces = []
        for (c, r), (o, k) in s.board.items():
            if k == "C":
                pieces.append({"cell": _cid(c, r), "owner": o,
                               "size": 4, "label": "C"})
            else:
                pieces.append({"cell": _cid(c, r), "owner": o, "size": 1})

        choice_names = {"K": "Kitten", "C": "Cat",
                        "LIFT": "Pick up (becomes a Cat in your pool)"}
        highlights = []
        if s.last:
            highlights.append({"cell": s.last, "kind": "last-move"})
        if s.phase == "resolve" and not self.is_terminal(s):
            grads, _lifts = self._resolve_options(s)
            for t in grads:
                ids = [_cid(*cl) for cl in t]
                choice_names[self._gspec(t)] = f"Graduate {ids[0]} - {ids[-1]}"

        names = {0: "Red", 1: "Blue"}

        def pool_str(p):
            h = s.pools[p]
            return f"{h['K']}K {h['C']}C"

        if s.winner is not None:
            w = s.winner
            trips = self._triples(s.board, w)
            how = ("three Cats in a row"
                   if any(all(s.board[cl][1] == "C" for cl in t) for t in trips)
                   else "all 8 Cats on the bed")
            cap = f"{names[w]} wins — {how}!"
        elif s.draw is not None:
            cap = ("Draw — threefold repetition" if s.draw == "repetition"
                   else "Draw — move limit reached")
        elif s.phase == "resolve":
            _grads, lifts = self._resolve_options(s)
            extra = " or pick up a piece (all 8 on the bed)" if lifts else ""
            cap = (f"{names[s.to_move]}: choose a row of 3 to graduate{extra} "
                   f"· pools — Red {pool_str(0)}, Blue {pool_str(1)}")
        else:
            cap = (f"{names[s.to_move]} to place "
                   f"· pools — Red {pool_str(0)}, Blue {pool_str(1)}")

        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": highlights,
            "caption": cap,
            "choiceNames": choice_names,
        }
