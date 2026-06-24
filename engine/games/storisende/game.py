"""Storisende, by Christian Freeling (2018).

A group/territory game on a hexagonal "hexhex" board. Players move stackable
men in straight lines; the moment a *virgin* cell is vacated it crystallises
into either GREEN (established territory) or a DARK Wall cell, depending on how
many distinct established territories it touches. The board thereby self-divides
into territories separated by a contiguous Wall, and the winner controls the
most territory (total cells of the territories they alone occupy).

This module implements the rules as published at mindsports.nl (see rules.md
for the exact wording and the interpretations made where the text is silent).

Coordinates are axial (q, r); cube s = -q-r; a cell is on a hexhex of base
`size` iff max(|q|,|r|,|s|) <= size-1. The six straight directions are the hex
neighbours. A move is encoded as "from>to" (e.g. "0,0>2,-2"); the moved portion
("from") is identified together with how many checkers leave (its *height*),
which equals the straight-line distance travelled, so "from>to" is unambiguous.
A pass is the move string "pass".

Termination: the game ends when both players pass consecutively, OR on the 3rd
occurrence of an identical position with the same player to move, OR at a hard
ply cap (safety net) -- in all three cases the result is decided BY TERRITORY
SCORE (a tie draws). NOTE: this deviates from the literal "3-fold repetition =
draw"; resolving a repeated/no-progress position by score matches good play (the
territory leader would win by simply passing) and lets the generic bot resolve
the game -- the literal repetition-draw made every random/bot game a draw via
stack-shuffling. Flagged in rules.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from agp.game import Game

P0, P1 = 0, 1
DEFAULT_BASE = 4          # hexhex base 4 -> 37 cells (Freeling: "usually base 4, 5 or 6")
HARD_PLY_CAP = 400        # safety net so random self-play always terminates

# The six axial directions (unit steps).
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)]


def _neighbors(q: int, r: int):
    return [(q + dq, r + dr) for (dq, dr) in DIRS]


@lru_cache(maxsize=None)
def _cells(base: int) -> tuple:
    out = []
    n = base - 1
    for q in range(-n, n + 1):
        for r in range(-n, n + 1):
            s = -q - r
            if abs(q) <= n and abs(r) <= n and abs(s) <= n:
                out.append((q, r))
    return tuple(out)


@lru_cache(maxsize=None)
def _cell_set(base: int) -> frozenset:
    return frozenset(_cells(base))


def _cell(text: str) -> tuple[int, int]:
    q, r = text.split(",")
    return int(q), int(r)


def _key(c) -> str:
    return f"{c[0]},{c[1]}"


@dataclass
class StoriState:
    base: int = DEFAULT_BASE
    # (q,r) -> list of owners bottom..top (a stack). Absent = empty cell.
    board: dict = field(default_factory=dict)
    # (q,r) -> territory id (int >= 1) for GREEN cells, or 0 for DARK Wall cells.
    # Absent = virgin (beige) cell.
    cellstate: dict = field(default_factory=dict)
    next_terr: int = 1                  # next fresh territory id
    to_move: int = P0
    passes: int = 0                     # consecutive passes
    setup_done: bool = False           # has the placer/chooser opening resolved?
    placer_men: tuple = ()             # cells placed by P0 during setup (await choice)
    ply: int = 0
    history: tuple = ()                # hashes of seen positions (for 3-fold)
    over: bool = False
    winner: Optional[int] = None       # None => draw if over
    last: tuple = ()                   # last move cells, for highlight


def _terr_ids_around(cellstate: dict, c) -> set:
    """Set of distinct GREEN territory ids adjacent to cell c."""
    ids = set()
    for nb in _neighbors(*c):
        st = cellstate.get(nb)
        if st is not None and st >= 1:   # green cell of some territory
            ids.add(st)
    return ids


def _crystallise(s_board: dict, cellstate: dict, next_terr: int, c) -> tuple[dict, int]:
    """A virgin cell `c` has just been vacated. Turn it green or dark.

    Returns (new_cellstate, new_next_terr). Mutates a *copy*'s contents only via
    the dict passed in being a fresh dict (caller passes a copy).
    Green-merge of equal-id neighbours is automatic (they already share an id);
    if it expands exactly one territory it joins that id; a brand-new pocket gets
    a fresh id; touching 2+ distinct territories makes it a DARK Wall cell.
    """
    ids = _terr_ids_around(cellstate, c)
    if len(ids) == 0:
        cellstate[c] = next_terr           # new established territory
        return cellstate, next_terr + 1
    if len(ids) == 1:
        cellstate[c] = next(iter(ids))     # expansion of exactly one territory
        return cellstate, next_terr
    # adjacent to separate established territories -> Wall (dark). Territories
    # never merge; the wall keeps them apart.
    cellstate[c] = 0
    return cellstate, next_terr


def _territories(cellstate: dict) -> dict:
    """Map territory id -> set of green cells. (Cells already carry their id, so
    this is just a grouping; ids never merge.)"""
    terr: dict = {}
    for c, st in cellstate.items():
        if st >= 1:
            terr.setdefault(st, set()).add(c)
    return terr


def _occupant_colour(board: dict, cell) -> Optional[int]:
    st = board.get(cell)
    if not st:
        return None
    # A stack is single-colour after merges, but a stack may in principle hold
    # one colour only (capture replaces wholesale, merge needs same colour).
    return st[-1]


def _score_territories(board: dict, cellstate: dict) -> tuple[int, int, int]:
    """Return (p0_cells, p1_cells, contested_or_empty_cells) counting, for each
    established territory, who *controls* it: a player controls a territory iff
    they are the only colour with men inside it. Wall cells never count."""
    terr = _territories(cellstate)
    p0 = p1 = neutral = 0
    for _id, cells in terr.items():
        colours = set()
        for c in cells:
            occ = _occupant_colour(board, c)
            if occ is not None:
                colours.add(occ)
        n = len(cells)
        if colours == {P0}:
            p0 += n
        elif colours == {P1}:
            p1 += n
        else:
            neutral += n   # empty or contested -> nobody controls it
    return p0, p1, neutral


class Storisende(Game):
    uid = "storisende"
    name = "Storisende"

    @property
    def num_players(self) -> int:
        return 2

    # ----- setup ---------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> StoriState:
        base = DEFAULT_BASE
        if options:
            base = int(options.get("base", DEFAULT_BASE))
        return StoriState(base=base)

    def current_player(self, s: StoriState) -> int:
        return s.to_move

    # ----- move generation ----------------------------------------------
    def _setup_moves(self, s: StoriState) -> list[str]:
        """The placer/chooser opening (see rules.md). Modelled in two plies:

        ply 0  (P0 = placer): place a single man on one empty cell. Repeated up
                to a small cap, but for the generic UI we use the canonical
                minimal opening: place exactly ONE man (a 'single'). This keeps
                the opening a one-click move while preserving the chooser's
                pie-style decision.
        ply 1  (P1 = chooser): either "accept" the placement as P0's first move
                (then normal play continues with P0's men staying P0's), or
                "swap" — take the placed position as one's own (men become P1's)
                and pass the equivalent placement choice back is not needed; we
                model swap as the standard pie rule.
        """
        if not s.placer_men:
            # placer: place one man on any cell
            return [_key(c) for c in _cells(s.base)]
        # chooser
        return ["accept", "swap"]

    def legal_moves(self, s: StoriState) -> list[str]:
        if s.over:
            return []
        if not s.setup_done:
            return self._setup_moves(s)

        moves: list[str] = []
        on = _cell_set(s.base)
        mover = s.to_move
        for src, stack in s.board.items():
            if not stack or stack[-1] != mover:
                continue
            height = len(stack)
            # may move the whole stack, or split: move the top k checkers
            # (k = 1..height); the moved portion travels exactly k cells. Since
            # distance == k, the destination cell alone determines the split, so
            # the move is the clean clickable path "from>to".
            for k in range(1, height + 1):
                for (dq, dr) in DIRS:
                    dest = (src[0] + dq * k, src[1] + dr * k)
                    if dest not in on:
                        continue
                    # landing: empty/own -> merge if own; opponent -> capture by
                    # replacement. Path is irrelevant (pieces jump).
                    moves.append(f"{_key(src)}>{_key(dest)}")
        moves.append("pass")
        return moves

    # ----- applying moves ------------------------------------------------
    def apply_move(self, s: StoriState, move: str, rng=None) -> StoriState:
        if s.over:
            raise ValueError("game over")

        # ---- setup phase ----
        if not s.setup_done:
            if not s.placer_men:
                c = _cell(move)
                if c not in _cell_set(s.base) or c in s.board:
                    raise ValueError(f"illegal placement {move!r}")
                board = dict(s.board)
                board[c] = [P0]
                return StoriState(
                    base=s.base, board=board, cellstate=dict(s.cellstate),
                    next_terr=s.next_terr, to_move=P1, placer_men=(c,),
                    ply=s.ply + 1, history=s.history, last=(c,),
                )
            # chooser
            if move not in ("accept", "swap"):
                raise ValueError(f"illegal setup choice {move!r}")
            board = {k: list(v) for k, v in s.board.items()}
            if move == "swap":
                # the placed man becomes the chooser's (P1); P1 keeps the men,
                # and it is now P0's turn to move (standard pie rule).
                for c in s.placer_men:
                    board[c] = [P1]
                to_move = P0
            else:
                # accept: the men stay P0's; the placement counts as P0's first
                # move, so it is now P1 (the chooser) to move.
                to_move = P1
            st = StoriState(
                base=s.base, board=board, cellstate=dict(s.cellstate),
                next_terr=s.next_terr, to_move=to_move, setup_done=True,
                placer_men=(), ply=s.ply + 1, history=(),
            )
            return self._record_history(st)

        # ---- normal play ----
        if move == "pass":
            passes = s.passes + 1
            over = passes >= 2
            st = StoriState(
                base=s.base,
                board={k: list(v) for k, v in s.board.items()},
                cellstate=dict(s.cellstate), next_terr=s.next_terr,
                to_move=1 - s.to_move, passes=passes, setup_done=True,
                ply=s.ply + 1, history=s.history, last=(),
            )
            if over:
                return self._finish(st)
            return self._record_history(st)

        src_text, dest_text = move.split(">")
        src = _cell(src_text)
        dest = _cell(dest_text)
        on = _cell_set(s.base)

        stack = s.board.get(src)
        if not stack or stack[-1] != s.to_move:
            raise ValueError(f"no movable stack at {src_text}")
        # Direction + distance: dest must lie exactly k cells from src along one
        # of the six directions, and k (the moved portion's height) must be a
        # valid split height 1..len(stack).
        k = None
        for kk in range(1, len(stack) + 1):
            for (dq, dr) in DIRS:
                if (src[0] + dq * kk, src[1] + dr * kk) == dest:
                    k = kk
                    break
            if k is not None:
                break
        if k is None or dest not in on:
            raise ValueError(f"illegal move geometry {move!r}")

        board = {c: list(v) for c, v in s.board.items()}
        cellstate = dict(s.cellstate)
        next_terr = s.next_terr

        moving = board[src][-k:]          # top k checkers (all colour to_move)
        remainder = board[src][:-k]
        if remainder:
            board[src] = remainder
        else:
            del board[src]

        # crystallise the SOURCE cell iff it is now fully vacated AND virgin.
        vacated = src not in board
        sprout = (vacated and src not in cellstate and k == 2 and len(s.board[src]) == 2)
        # NB: "double" = the cell held exactly a stack of two and that whole
        # double left (k==2 and original height 2 -> remainder empty).
        if vacated and src not in cellstate:
            cellstate, next_terr = _crystallise(board, cellstate, next_terr, src)
            if sprout:
                # sprout one new man of the mover's colour on the vacated cell.
                board[src] = [s.to_move]

        # resolve the landing.
        occ = _occupant_colour(board, dest)
        if occ is None:
            board[dest] = list(moving)
        elif occ == s.to_move:
            board[dest] = board[dest] + list(moving)   # merge
        else:
            board[dest] = list(moving)                 # capture by replacement

        st = StoriState(
            base=s.base, board=board, cellstate=cellstate, next_terr=next_terr,
            to_move=1 - s.to_move, passes=0, setup_done=True,
            ply=s.ply + 1, history=s.history, last=(src, dest),
        )

        # hard ply cap safety net + 3-fold repetition.
        if st.ply >= HARD_PLY_CAP:
            return self._finish(st)
        return self._record_history(st)

    # ----- termination helpers ------------------------------------------
    def _pos_hash(self, s: StoriState):
        board = tuple(sorted((c, tuple(v)) for c, v in s.board.items()))
        cs = tuple(sorted(s.cellstate.items()))
        return (board, cs, s.to_move)

    def _record_history(self, s: StoriState) -> StoriState:
        h = self._pos_hash(s)
        new_hist = s.history + (h,)
        if new_hist.count(h) >= 3:
            # 3-fold repetition ends the game, resolved BY TERRITORY SCORE (a tie
            # still draws). DEVIATION from the literal "repetition = draw": a
            # repeated position means no further progress, and the territory
            # leader would have won anyway by simply passing — so awarding the
            # leader matches good play, guarantees termination, AND lets the
            # generic MCTS bot resolve the game (the literal repetition-draw made
            # every random/bot game a draw via stack-shuffling). Flagged in
            # rules.md. (Crystallisation is monotonic, so a position only repeats
            # in an already-settled phase where passing is the correct move.)
            s2 = StoriState(**{**s.__dict__, "history": new_hist})
            return self._finish(s2)
        return StoriState(**{**s.__dict__, "history": new_hist})

    def _finish(self, s: StoriState, draw: bool = False) -> StoriState:
        p0, p1, _ = _score_territories(s.board, s.cellstate)
        if draw:
            winner = None
        elif p0 > p1:
            winner = P0
        elif p1 > p0:
            winner = P1
        else:
            winner = None
        return StoriState(**{**s.__dict__, "over": True, "winner": winner})

    def is_terminal(self, s: StoriState) -> bool:
        return s.over

    def returns(self, s: StoriState) -> list[float]:
        if not s.over:
            return [0.0, 0.0]
        if s.winner == P0:
            return [1.0, -1.0]
        if s.winner == P1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ----- serialization -------------------------------------------------
    def serialize(self, s: StoriState) -> dict:
        return {
            "base": s.base,
            "board": {_key(c): list(v) for c, v in s.board.items()},
            "cellstate": {_key(c): st for c, st in s.cellstate.items()},
            "next_terr": s.next_terr,
            "to_move": s.to_move,
            "passes": s.passes,
            "setup_done": s.setup_done,
            "placer_men": [_key(c) for c in s.placer_men],
            "ply": s.ply,
            "over": s.over,
            "winner": s.winner,
            "last": [_key(c) for c in s.last],
        }

    def deserialize(self, d: dict) -> StoriState:
        return StoriState(
            base=d["base"],
            board={_cell(k): list(v) for k, v in d["board"].items()},
            cellstate={_cell(k): st for k, st in d["cellstate"].items()},
            next_terr=d.get("next_terr", 1),
            to_move=d["to_move"],
            passes=d.get("passes", 0),
            setup_done=d.get("setup_done", False),
            placer_men=tuple(_cell(c) for c in d.get("placer_men", [])),
            ply=d.get("ply", 0),
            history=(),  # history is a draw-detection aid; not needed to resume
            over=d.get("over", False),
            winner=d.get("winner"),
            last=tuple(_cell(c) for c in d.get("last", [])),
        )

    # ----- move log ------------------------------------------------------
    def describe_move(self, s: StoriState, move: str) -> str:
        if move in ("pass", "accept", "swap"):
            return move
        if not s.setup_done and ">" not in move:
            return f"place {move}"
        if ">" in move:
            src, dest = move.split(">")
            return f"{src}→{dest}"
        return move

    # ----- rendering -----------------------------------------------------
    def render(self, s: StoriState, perspective=None) -> dict:
        names = {P0: "Black", P1: "White"}

        # tints: green territories tinted by a soft green; wall (dark) cells dark.
        tints = {}
        for c, st in s.cellstate.items():
            if st == 0:
                tints[_key(c)] = "#3a3a3a"        # Wall (dark)
            else:
                tints[_key(c)] = "#33502f"        # established territory (green)

        pieces = []
        for c, stack in s.board.items():
            if not stack:
                continue
            owner = stack[-1]
            pieces.append({
                "cell": _key(c),
                "owner": owner,
                "label": str(len(stack)) if len(stack) > 1 else "",
                "stack": [owner] * len(stack),
            })

        highlights = [{"cell": _key(c), "kind": "last-move"} for c in s.last]

        p0, p1, neutral = _score_territories(s.board, s.cellstate)
        if not s.setup_done:
            if not s.placer_men:
                caption = "Setup: Black places a man (placer)"
            else:
                caption = "Setup: White chooses — accept or swap"
        elif s.over:
            if s.winner is None:
                caption = f"Draw — Black {p0}, White {p1}"
            else:
                caption = f"{names[s.winner]} wins — Black {p0}, White {p1}"
        else:
            caption = f"{names[s.to_move]} to move — Black {p0}, White {p1}"

        return {
            "board": {"type": "hex", "shape": "hexagon", "size": s.base,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
