"""Lielow — Michael Amundsen & Alek Erickson, 2021.

Eight checkers a side on the second rank of a chessboard.  A stack moves
queenwise **exactly its own height**, jumping freely over anything in between;
landing on an empty square grows it by one, landing on an enemy stack removes
that stack and resets the mover to height 1, and landing outside the board
removes the mover.  After every move each player's crown jumps to their unique
tallest stack (it stays put while the tallest is tied).  Lose your crowned stack
— captured, or walked off the edge — and you lose.

Rules as implemented are documented in `rules.md`; the differential against the
AbstractPlay reference implementation lives in `_diff_ap.py`.
"""

from dataclasses import dataclass, replace
from typing import Optional

from agp.game import Game

SIZE = 8
NCELLS = SIZE * SIZE

# Queenwise: the eight directions, as (dcol, drow).
DIRS = ((0, 1), (0, -1), (1, 0), (-1, 0),
        (1, 1), (1, -1), (-1, 1), (-1, -1))

# `king` sentinels.  A player starts with NO crown at all (all eight stacks are
# height 1, so there is no *unique* tallest); DEAD is set the instant the
# crowned stack leaves the board, and is what ends the game.
NO_KING = -1
DEAD = -2

# Termination backstop.  It is provably unreachable — see `rules.md`
# ("Why the game always ends"): no game can exceed 352 plies, because every move
# either adds exactly 1 to the total height standing on the board (which can
# never exceed 8 x 16 = 128) or permanently removes a stack (at most 15 of those
# before someone's crown falls).  The cap exists so a future rule change cannot
# hang a live match; it has never fired in any test — the longest of 1,500
# random games ran 73 plies.  `max_random_plies` in the manifest is 400 — above
# the proven bound, below this cap — so a termination regression is reported by
# conformance as "did not terminate" rather than absorbed here as a silent draw.
PLY_CAP = 512


def idx(c: int, r: int) -> int:
    return r * SIZE + c


def cell_name(i: int) -> str:
    """Engine cell id: "col,row" with col = file a..h = 0..7, row = rank 1..8 = 0..7."""
    return f"{i % SIZE},{i // SIZE}"


def parse_cell(text: str) -> int:
    c, r = (int(x) for x in text.split(","))
    if not (0 <= c < SIZE and 0 <= r < SIZE):
        raise ValueError(f"off-board cell {text!r}")
    return idx(c, r)


def algebraic(i: int) -> str:
    """Chess names, used only for the move log and captions.  a1 = 0,0."""
    return f"{chr(ord('a') + i % SIZE)}{i // SIZE + 1}"


def owner(v: int) -> int:
    """Seat owning a board value (seat 0 stores +height, seat 1 -height)."""
    return 0 if v > 0 else 1


def height(v: int) -> int:
    return v if v > 0 else -v


def signed(seat: int, h: int) -> int:
    return h if seat == 0 else -h


@dataclass(frozen=True)
class LState:
    board: tuple           # NCELLS ints: 0 empty, +h = seat 0 stack, -h = seat 1
    king: tuple            # per seat: cell index, or NO_KING, or DEAD
    to_move: int
    ply: int
    over: bool
    winner: Optional[int] = None      # None + over == honest draw
    last: Optional[tuple] = None      # (from_idx, to_idx); from == to means "off"


class Lielow(Game):
    """Lielow (Michael Amundsen & Alek Erickson, 2021)."""

    @property
    def num_players(self) -> int:
        return 2

    # ---------------- setup ----------------

    def initial_state(self, options: Optional[dict] = None, rng=None) -> LState:
        board = [0] * NCELLS
        for c in range(SIZE):
            board[idx(c, 1)] = signed(0, 1)          # rank 2
            board[idx(c, SIZE - 2)] = signed(1, 1)   # rank 7
        return LState(board=tuple(board), king=(NO_KING, NO_KING),
                      to_move=0, ply=0, over=False, winner=None, last=None)

    def current_player(self, state: LState) -> int:
        return state.to_move

    # ---------------- movement ----------------

    @staticmethod
    def _gen(board, seat):
        """Yield (from_idx, to_idx) for every legal move of ``seat``.

        A stack of height h steps h squares in one of the eight directions.
        Nothing in between matters — stacks jump.  ``to == from`` is the INTERNAL
        encoding of "the landing square is off the board, so the stack is
        removed"; every off-board direction gives the same result, so they
        collapse into one move.  On the wire that move is written ``"c,r>off"``
        (see ``legal_moves``).
        """
        for i, v in enumerate(board):
            if v == 0 or owner(v) != seat:
                continue
            h = height(v)
            c, r = i % SIZE, i // SIZE
            off = False
            for dc, dr in DIRS:
                nc, nr = c + dc * h, r + dr * h
                if not (0 <= nc < SIZE and 0 <= nr < SIZE):
                    off = True
                    continue
                j = idx(nc, nr)
                t = board[j]
                if t == 0 or owner(t) != seat:
                    yield i, j
            if off:
                yield i, i

    @staticmethod
    def _fmt(i: int, j: int) -> str:
        """Move string.  A stack that walks off the board is written
        ``"c,r>off"`` — deliberately NOT a cell path.  The web renderer routes
        any move whose ">"-segments are all cell ids to the board's click
        handler, so a self-path "c,r>c,r" would fire on the second click of the
        SAME square, i.e. on the instinctive "never mind, deselect" click.  In
        Lielow that click permanently destroys a stack and, if it is the crowned
        one, loses the game on the spot.  Writing "off" instead sends the move
        down the labelled action-button channel (see `actionNames` in
        ``render``), where it has to be chosen on purpose."""
        return f"{cell_name(i)}>" + ("off" if i == j else cell_name(j))

    def legal_moves(self, state: LState) -> list:
        if state.over:
            return []
        return [self._fmt(i, j)
                for i, j in self._gen(state.board, state.to_move)]

    @staticmethod
    def _has_move(board, seat) -> bool:
        for _ in Lielow._gen(board, seat):
            return True
        return False

    @staticmethod
    def _parse(move: str) -> tuple:
        """-> (from_idx, to_idx); to == from is the internal "walks off" form.

        The self-path SPELLING ``"c,r>c,r"`` is rejected outright: only the
        ``"c,r>off"`` wire form may mean "walk this stack off the board".  That
        keeps the guarantee whole at the engine level too — an accidental
        second click on an already-selected stack cannot destroy it, whatever
        the caller."""
        frm, _, to = move.partition(">")
        if not to:
            raise ValueError(f"bad move {move!r}")
        i = parse_cell(frm)
        if to == "off":
            return i, i
        j = parse_cell(to)
        if j == i:
            raise ValueError(
                f"{move!r}: a stack cannot move to its own square — "
                f'walking off the board is spelled "{cell_name(i)}>off"')
        return i, j

    # ---------------- the crown ----------------

    @staticmethod
    def _crown(board, seat: int, cur: int) -> int:
        """Where ``seat``'s crown sits after the position changed.

        "If, at the end of your turn, you have a unique tallest stack, that stack
        becomes your king.  If you have no unique tallest stack, your crown stays
        wherever it was."  A player with no stacks at all keeps their crown value
        unchanged (that situation cannot arise while the game is live — the last
        stack a player owns is always their crowned one).
        """
        best, who, cnt = 0, -1, 0
        for i, v in enumerate(board):
            if v == 0 or owner(v) != seat:
                continue
            h = height(v)
            if h > best:
                best, who, cnt = h, i, 1
            elif h == best:
                cnt += 1
        return who if cnt == 1 and who != cur else cur

    # ---------------- play ----------------

    def apply_move(self, state: LState, move: str, rng=None) -> LState:
        if state.over:
            raise ValueError("game is over")
        seat = state.to_move
        i, j = self._parse(move)
        v = state.board[i]
        if v == 0 or owner(v) != seat:
            raise ValueError(f"no stack of yours on {cell_name(i)}")
        board = list(state.board)
        king = list(state.king)
        h = height(v)

        if i == j:
            # Off the board: legal only if some direction actually leaves it.
            c, r = i % SIZE, i // SIZE
            if not (c - h < 0 or c + h >= SIZE or r - h < 0 or r + h >= SIZE):
                raise ValueError(f"{algebraic(i)} cannot reach the edge")
            board[i] = 0
            if king[seat] == i:
                king[seat] = DEAD
        else:
            c, r = i % SIZE, i // SIZE
            tc, tr = j % SIZE, j // SIZE
            dc, dr = tc - c, tr - r
            if (abs(dc), abs(dr)) not in ((h, 0), (0, h), (h, h)):
                raise ValueError(f"{algebraic(i)}-{algebraic(j)} is not {h} queenwise")
            t = board[j]
            if t == 0:
                board[j] = signed(seat, h + 1)          # grow by one
            elif owner(t) != seat:
                if king[1 - seat] == j:
                    king[1 - seat] = DEAD               # the crown falls
                board[j] = signed(seat, 1)              # capture resets to 1
            else:
                raise ValueError("cannot land on your own stack")
            board[i] = 0
            if king[seat] == i:
                king[seat] = j

        # Accession, for BOTH players ("after each move, both players check the
        # levels of their pieces" — BGA).  The two sets are disjoint, so order is
        # irrelevant; a dead crown is never revived.
        for s in (seat, 1 - seat):
            if king[s] != DEAD:
                king[s] = self._crown(board, s, king[s])

        board = tuple(board)
        ply = state.ply + 1
        # A DECISIVE RESULT OUTRANKS EVERY COUNTER: the crown check comes first
        # and, once `over` is set with a winner, neither the no-move fallback nor
        # the ply cap can touch it.
        winner = None
        if king[seat] == DEAD:
            winner = 1 - seat
        elif king[1 - seat] == DEAD:
            winner = seat
        out = LState(board=board, king=(king[0], king[1]), to_move=1 - seat,
                     ply=ply, over=winner is not None, winner=winner, last=(i, j))
        if out.over:
            return out
        if not self._has_move(board, out.to_move):
            # Provably unreachable (see rules.md): a player's right-most stack
            # always has a move.  Kept so a rule change can never hand the
            # server an empty move list.
            return replace(out, over=True, winner=seat)
        if ply >= PLY_CAP:
            return replace(out, over=True, winner=None)
        return out

    # ---------------- results ----------------

    def is_terminal(self, state: LState) -> bool:
        return state.over

    def returns(self, state: LState) -> list:
        if not state.over or state.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if state.winner == 0 else [-1.0, 1.0]

    # ---------------- bot eval ----------------

    @staticmethod
    def _attacks(board, seat: int, target: int) -> bool:
        """Could ``seat`` capture the stack on ``target`` right now?"""
        if target < 0:
            return False
        tc, tr = target % SIZE, target // SIZE
        for i, v in enumerate(board):
            if v == 0 or owner(v) != seat:
                continue
            h = height(v)
            dc, dr = tc - i % SIZE, tr - i // SIZE
            if (abs(dc), abs(dr)) in ((h, 0), (0, h), (h, h)):
                return True
        return False

    def heuristic(self, state: LState) -> list:
        """Material, plus a big term for having the enemy crown en prise.

        Returns ONE payoff PER SEAT (never a bare float) — MCTS indexes it as
        ``payoffs[p]``.
        """
        if state.over:
            return self.returns(state)
        mat = [0, 0]
        for v in state.board:
            if v:
                mat[owner(v)] += 1
        v = 0.30 * (mat[0] - mat[1])
        for s in (0, 1):
            if self._attacks(state.board, s, state.king[1 - s]):
                v += 0.9 if s == 0 else -0.9
        # Cheap bounded squash into (-1, 1); no math import needed.
        x = v / (1.0 + abs(v))
        return [x, -x]

    # ---------------- persistence ----------------

    def serialize(self, state: LState) -> dict:
        return {
            "board": list(state.board),
            "king": list(state.king),
            "to_move": state.to_move,
            "ply": state.ply,
            "over": state.over,
            "winner": state.winner,
            "last": list(state.last) if state.last is not None else None,
        }

    def deserialize(self, data: dict) -> LState:
        last = data.get("last")
        return LState(
            board=tuple(int(x) for x in data["board"]),
            king=tuple(int(x) for x in data["king"]),
            to_move=int(data["to_move"]),
            ply=int(data["ply"]),
            over=bool(data["over"]),
            winner=None if data.get("winner") is None else int(data["winner"]),
            last=None if last is None else (int(last[0]), int(last[1])),
        )

    # ---------------- presentation ----------------

    def describe_move(self, state: LState, move: str) -> str:
        i, j = self._parse(move)
        if i == j:
            text = f"{algebraic(i)}-off"
        else:
            text = f"{algebraic(i)}{'x' if state.board[j] else '-'}{algebraic(j)}"
        after = self.apply_move(state, move)
        if after.over and after.winner is not None:
            text += "#"
        return text

    def render(self, state: LState, perspective: Optional[int] = None) -> dict:
        pieces = []
        for i, v in enumerate(state.board):
            if v == 0:
                continue
            seat = owner(v)
            p = {"cell": cell_name(i), "owner": seat, "stack": [seat] * height(v)}
            if state.king[seat] == i:
                p["label"] = "♚"      # the crown marker
            pieces.append(p)

        highlights = []
        if state.last is not None:
            for k in dict.fromkeys(state.last):
                highlights.append({"cell": cell_name(k), "kind": "last-move"})

        names = ("White", "Black")
        if state.over:
            if state.winner is None:
                caption = f"Draw (move limit reached at ply {state.ply})"
            else:
                caption = f"{names[state.winner]} wins — {names[1 - state.winner]}'s king is gone"
        else:
            crowns = []
            for s in (0, 1):
                k = state.king[s]
                crowns.append(f"{names[s]} {algebraic(k) if k >= 0 else '—'}")
            caption = f"{names[state.to_move]} to move — crowns: " + ", ".join(crowns)

        # Walking a stack off the board is a non-cell move, so the renderer
        # gives it a button; name each one after its square (several can be
        # legal at once) and flag the one that would end the game.
        actions = {}
        for i, j in self._gen(state.board, state.to_move) if not state.over else ():
            if i == j:
                lost = state.king[state.to_move] == i
                actions[self._fmt(i, j)] = (
                    f"Walk {algebraic(i)} off the board"
                    + (" — RESIGNS (your king)" if lost else ""))

        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "actionNames": actions,
        }
