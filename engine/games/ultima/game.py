"""Ultima (Baroque Chess), by Robert Abbott (1962).

8x8 board. The chess back rank is replaced by Ultima pieces; the second rank is
all Pincer Pawns. Almost every piece MOVES like a chess queen (slide any number
of empty squares orthogonally/diagonally, no jumping) but CAPTURES by a unique
method. Captures are a SIDE EFFECT of where you move -- a single move can remove
zero, one, or several enemy pieces.

Pieces / letters:
  I = Immobilizer  (queen move; never captures; freezes adjacent enemies)
  L = Long Leaper  (queen move; captures by jumping enemies in its line of travel)
  M = Chameleon    (queen move; captures by mimicking the victim's own method)
  C = Coordinator  (queen move; captures the enemy on each rook-cross intersection
                    with its own King)
  W = Withdrawer   (queen move; captures by moving directly away from an adjacent enemy)
  K = King         (one-square move; captures by displacement, like chess)
  P = Pincer Pawn  (ROOK move; captures by custodial flanking, orthogonal only)

Win by CAPTURING the enemy King (no check/checkmate enforcement -- see rules.md).
White = player 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1
W, H = 8, 8

ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG

# Movement rays per piece type (sliding directions).  King and Pawn handled
# specially: King steps ONE square in ALL8, Pawn slides ORTHO only.
QUEEN = ALL8

PLY_CAP = 600          # hard draw cap on total plies
NO_CAPTURE_CAP = 100   # draw if this many plies pass with no capture

PIECE_LETTERS = {"I", "L", "M", "C", "W", "K", "P"}


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


def _s(c: int, r: int) -> str:
    return f"{c},{r}"


def _on(c: int, r: int) -> bool:
    return 0 <= c < W and 0 <= r < H


@dataclass
class UState:
    # board: (c, r) -> (owner, letter)
    board: dict = field(default_factory=dict)
    to_move: int = WHITE
    winner: Optional[int] = None       # set when a King is captured
    draw: bool = False
    plies: int = 0                     # total plies played
    since_capture: int = 0             # plies since the last capture


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

# Canonical Ultima back rank (a1..h1), per Wikipedia/MacKay "pure rules":
# Immobilizer, Long Leaper, Chameleon, King, Withdrawer, Chameleon, Long Leaper,
# Coordinator.  (King d-file, Withdrawer e-file -- swapped vs. standard chess Q/K.)
BACK_RANK = ["I", "L", "M", "K", "W", "M", "L", "C"]


def _setup() -> dict:
    b: dict = {}
    for c in range(W):
        b[(c, 0)] = (WHITE, BACK_RANK[c])
        b[(c, 1)] = (WHITE, "P")
        b[(c, 6)] = (BLACK, "P")
        b[(c, 7)] = (BLACK, BACK_RANK[c])
    return b


# ---------------------------------------------------------------------------
# Immobilization
# ---------------------------------------------------------------------------

def _adjacent(c: int, r: int):
    for dc, dr in ALL8:
        nc, nr = c + dc, r + dr
        if _on(nc, nr):
            yield nc, nr


def _is_immobilized(board: dict, c: int, r: int) -> bool:
    """A piece at (c,r) is immobilized (cannot move at all) iff, per the MacKay
    'pure rules':
      (a) it is an Immobilizer adjacent to an enemy Chameleon, OR
      (b) it is adjacent to an enemy Immobilizer next to which there is no
          friendly Chameleon or Immobilizer other than this piece itself.
    """
    owner, letter = board[(c, r)]
    enemy = 1 - owner

    # (a) an Immobilizer frozen by an adjacent enemy Chameleon
    if letter == "I":
        for nc, nr in _adjacent(c, r):
            occ = board.get((nc, nr))
            if occ and occ[0] == enemy and occ[1] == "M":
                return True

    # (b) adjacent to an enemy Immobilizer
    for nc, nr in _adjacent(c, r):
        occ = board.get((nc, nr))
        if occ and occ[0] == enemy and occ[1] == "I":
            # The enemy immobilizer is at (nc,nr).  This piece is frozen UNLESS
            # there is a friendly (to this piece) Chameleon or Immobilizer --
            # other than this piece itself -- adjacent to that immobilizer,
            # which neutralizes / locks it.
            neutralized = False
            for ac, ar in _adjacent(nc, nr):
                if (ac, ar) == (c, r):
                    continue
                other = board.get((ac, ar))
                if other and other[0] == owner and other[1] in ("M", "I"):
                    neutralized = True
                    break
            if not neutralized:
                return True
    return False


# ---------------------------------------------------------------------------
# Move generation (raw destinations, ignoring capture side effects)
# ---------------------------------------------------------------------------

def _destinations(board: dict, c: int, r: int) -> list[tuple[int, int]]:
    owner, letter = board[(c, r)]
    out: list[tuple[int, int]] = []

    if letter == "K":
        for dc, dr in ALL8:
            nc, nr = c + dc, r + dr
            if not _on(nc, nr):
                continue
            occ = board.get((nc, nr))
            if occ is None or occ[0] != owner:
                out.append((nc, nr))   # king may step onto empty OR capture enemy
        return out

    if letter in ("L", "M"):
        # Long Leaper (and the Chameleon, which mimics it to capture an enemy
        # leaper): slides over empty squares, AND may leap over a run of enemy
        # pieces (each separated by no friendly piece, landing on an empty
        # square).  Generate every reachable landing square along each ray.
        # (For the Chameleon the leap only *captures* enemy Long Leapers -- see
        # _chameleon_caps -- but it must still be able to make the leaping move.)
        for dc, dr in QUEEN:
            nc, nr = c + dc, r + dr
            # phase 1: glide over empties
            while _on(nc, nr) and (nc, nr) not in board:
                out.append((nc, nr))
                nc += dc
                nr += dr
            # phase 2: leaping.  We may jump consecutive single enemies; the
            # landing square after each jumped enemy (if empty) is reachable, and
            # we can continue leaping from there.
            while _on(nc, nr):
                occ = board.get((nc, nr))
                if occ is None:
                    break  # handled in phase 1 already / no piece to jump
                if occ[0] == owner:
                    break  # cannot leap a friendly piece
                if letter == "M" and occ[1] != "L":
                    break  # the Chameleon may only leap enemy Long Leapers
                # an enemy: try to land just beyond it
                lc, lr = nc + dc, nr + dr
                if not _on(lc, lr) or (lc, lr) in board:
                    break  # no empty landing square -> cannot leap here
                out.append((lc, lr))
                # continue: glide over empties beyond the landing, then maybe leap again
                nc, nr = lc + dc, lr + dr
                while _on(nc, nr) and (nc, nr) not in board:
                    out.append((nc, nr))
                    nc += dc
                    nr += dr
        if letter == "M":
            # The Chameleon captures an enemy King the King's own way: by
            # stepping one square onto it.  Add adjacent enemy-King squares as
            # destinations (the only occupied squares it may move onto).
            for dc, dr in ALL8:
                ac, ar = c + dc, r + dr
                occ = board.get((ac, ar))
                if occ and occ[0] != owner and occ[1] == "K":
                    out.append((ac, ar))
        return out

    rays = ORTHO if letter == "P" else QUEEN
    for dc, dr in rays:
        nc, nr = c + dc, r + dr
        while _on(nc, nr) and (nc, nr) not in board:
            out.append((nc, nr))
            nc += dc
            nr += dr
    return out


# ---------------------------------------------------------------------------
# Capture resolution -- given a piece moving from (fc,fr) to (tc,tr), return the
# set of enemy cells captured.  King capture-by-displacement is handled before
# this (the destination square is cleared).
# ---------------------------------------------------------------------------

def _find_king(board: dict, owner: int):
    for (c, r), (o, l) in board.items():
        if o == owner and l == "K":
            return (c, r)
    return None


def _withdrawer_caps(board, owner, fc, fr, tc, tr):
    """Captures by moving directly away from an adjacent enemy along the move's
    own line of travel.  The enemy must have been adjacent to the START square,
    on the opposite side of the direction of motion."""
    dc = (tc > fc) - (tc < fc)
    dr = (tr > fr) - (tr < fr)
    bc, br = fc - dc, fr - dr   # square directly behind the start
    if not _on(bc, br):
        return set()
    occ = board.get((bc, br))
    if occ and occ[0] != owner:
        return {(bc, br)}
    return set()


def _coordinator_caps(board, owner, tc, tr):
    king = _find_king(board, owner)
    if king is None:
        return set()
    kc, kr = king
    caps = set()
    for (ic, ir) in ((tc, kr), (kc, tr)):
        occ = board.get((ic, ir))
        if occ and occ[0] != owner:
            caps.add((ic, ir))
    return caps


def _leaper_caps(board, owner, fc, fr, tc, tr, board_after_move):
    """Long Leaper: jumps enemies along its single straight line of travel,
    landing on empty squares.  Multiple enemies in the line may be captured as
    long as each jumped piece is alone (an empty square follows it -- which it
    does, since the leaper passes through).  Two enemies cannot be adjacent in
    the path (the leaper cannot pass two pieces with no gap)."""
    dc = (tc > fc) - (tc < fc)
    dr = (tr > fr) - (tr < fr)
    caps = set()
    c, r = fc + dc, fr + dr
    while (c, r) != (tc, tr):
        occ = board.get((c, r))
        if occ is not None:
            if occ[0] == owner:
                return set()  # cannot leap a friendly piece -> not a leaper move
            # enemy: must be followed by an empty square (the next step)
            nc, nr = c + dc, r + dr
            after = board.get((nc, nr))
            if after is not None:
                return set()  # two enemies back-to-back: illegal leap path
            caps.add((c, r))
        c, r = c + dc, r + dr
    return caps


def _pincer_caps(board_after_move, owner, tc, tr):
    """Custodial (pincer) capture: for each orthogonal direction, an adjacent
    enemy with a friendly piece directly beyond it is captured."""
    enemy = 1 - owner
    caps = set()
    for dc, dr in ORTHO:
        ac, ar = tc + dc, tr + dr           # adjacent square
        bc, br = tc + 2 * dc, tr + 2 * dr    # square beyond it
        a = board_after_move.get((ac, ar))
        b = board_after_move.get((bc, br))
        if a and a[0] == enemy and b and b[0] == owner:
            caps.add((ac, ar))
    return caps


def _chameleon_caps(board, board_after_move, owner, fc, fr, tc, tr):
    """The Chameleon captures each enemy by THAT enemy's own capture method,
    applied as if the Chameleon were a piece of the enemy's type:
      - vs enemy Withdrawer: by withdrawing away from it.
      - vs enemy Coordinator: by coordinating (rook-cross with own King).
      - vs enemy Long Leaper: by leaping over it.
      - vs enemy Pincer Pawn: by pincering it (custodial).
      - vs enemy King: by stepping onto it (handled as displacement before this).
      - vs enemy Immobilizer / Chameleon: NOT captured this way (it freezes
        adjacent enemy Immobilizers instead; it cannot capture a Chameleon).
    Only enemies whose type matches the method used are removed."""
    enemy = 1 - owner
    caps = set()

    # Withdrawer method: the enemy directly behind the start, if it is a Withdrawer.
    for cell in _withdrawer_caps(board, owner, fc, fr, tc, tr):
        occ = board.get(cell)
        if occ and occ[1] == "W":
            caps.add(cell)

    # Coordinator method: cross-intersection enemies that are Coordinators.
    for cell in _coordinator_caps(board_after_move, owner, tc, tr):
        occ = board.get(cell)
        if occ and occ[1] == "C":
            caps.add(cell)

    # Long Leaper method: leaped enemies that are Long Leapers.
    for cell in _leaper_caps(board, owner, fc, fr, tc, tr, board_after_move):
        occ = board.get(cell)
        if occ and occ[1] == "L":
            caps.add(cell)

    # Pincer method: pincered enemies that are Pincer Pawns.
    for cell in _pincer_caps(board_after_move, owner, tc, tr):
        occ = board.get(cell)
        if occ and occ[1] == "P":
            caps.add(cell)

    return caps


def _captures_for(board: dict, fc, fr, tc, tr) -> set:
    """All cells captured by moving the piece at (fc,fr) to (tc,tr).
    `board` is the position BEFORE the move (the moving piece still at origin)."""
    owner, letter = board[(fc, fr)]

    # King displacement capture (target square cleared regardless of method).
    if letter == "K":
        occ = board.get((tc, tr))
        return {(tc, tr)} if occ and occ[0] != owner else set()

    # Build the post-move board (piece relocated) for methods that key off it.
    after = dict(board)
    del after[(fc, fr)]
    after[(tc, tr)] = (owner, letter)

    if letter == "W":
        return _withdrawer_caps(board, owner, fc, fr, tc, tr)
    if letter == "C":
        return _coordinator_caps(after, owner, tc, tr)
    if letter == "L":
        return _leaper_caps(board, owner, fc, fr, tc, tr, after)
    if letter == "P":
        return _pincer_caps(after, owner, tc, tr)
    if letter == "M":
        return _chameleon_caps(board, after, owner, fc, fr, tc, tr)
    if letter == "I":
        return set()  # the Immobilizer never captures
    return set()


# ---------------------------------------------------------------------------
# Legal moves
# ---------------------------------------------------------------------------

def _legal_move_list(s: UState) -> list[str]:
    board = s.board
    me = s.to_move
    out: list[str] = []
    for (c, r), (owner, letter) in board.items():
        if owner != me:
            continue
        if _is_immobilized(board, c, r):
            continue
        for (tc, tr) in _destinations(board, c, r):
            # Chameleon may NOT land on an enemy by displacement (only the King
            # captures by displacement; the Chameleon does so only vs the King,
            # which is the enemy occupying the destination -- allowed).
            occ = board.get((tc, tr))
            if occ is not None:
                # destination occupied -> only the King (and Chameleon onto an
                # enemy King) may move there.
                if letter == "K" and occ[0] != owner:
                    pass
                elif letter == "M" and occ[0] != owner and occ[1] == "K":
                    pass
                else:
                    continue
            out.append(f"{_s(c, r)}>{_s(tc, tr)}")
    return out


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Ultima(Game):
    uid = "ultima"
    name = "Ultima (Baroque Chess)"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> UState:
        return UState(board=_setup())

    def current_player(self, s: UState) -> int:
        return s.to_move

    def legal_moves(self, s: UState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = _legal_move_list(s)
        if not moves:
            # No legal move available (all pieces frozen / stuck): pass.  The UI
            # surfaces this as a "pass" button.
            return ["pass"]
        return moves

    def apply_move(self, s: UState, move: str, rng=None) -> UState:
        if self.is_terminal(s):
            raise ValueError("game already over")
        me = s.to_move
        opp = 1 - me

        if move == "pass":
            return self._advance(s, dict(s.board), captured_any=False)

        fro, to = move.split(">")
        fc, fr = _cell(fro)
        tc, tr = _cell(to)

        if (fc, fr) not in s.board or s.board[(fc, fr)][0] != me:
            raise ValueError(f"no movable {me} piece at {fro}")
        if move not in set(_legal_move_list(s)):
            raise ValueError(f"illegal move {move!r}")

        owner, letter = s.board[(fc, fr)]
        board = dict(s.board)

        # King (or chameleon-vs-king) displacement: clear the destination first.
        dest_occ = board.get((tc, tr))
        captured = set(_captures_for(s.board, fc, fr, tc, tr))
        if dest_occ is not None and dest_occ[0] == opp:
            captured.add((tc, tr))  # the occupied destination is captured/displaced

        # Relocate the moving piece.
        del board[(fc, fr)]
        # Remove captured pieces (the destination square is overwritten below).
        for cell in captured:
            if cell in board:
                del board[cell]
        board[(tc, tr)] = (owner, letter)

        # Win if an enemy King was captured.
        if any(s.board[cell][1] == "K" for cell in captured if cell in s.board):
            return UState(board=board, to_move=opp, winner=me,
                          plies=s.plies + 1, since_capture=0)

        return self._advance(s, board, captured_any=bool(captured), tc=tc, tr=tr)

    def _advance(self, s: UState, board: dict, captured_any: bool,
                 tc=None, tr=None) -> UState:
        plies = s.plies + 1
        since = 0 if captured_any else s.since_capture + 1
        nxt = UState(board=board, to_move=1 - s.to_move,
                     plies=plies, since_capture=since)
        # Draw caps (guarantee termination).
        if plies >= PLY_CAP or since >= NO_CAPTURE_CAP:
            nxt.draw = True
        # If a side has lost its King already (shouldn't happen via normal play,
        # but be safe), the other side wins.
        return nxt

    def is_terminal(self, s: UState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: UState) -> list[float]:
        if s.winner == WHITE:
            return [1.0, -1.0]
        if s.winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: UState) -> dict:
        return {
            "board": {_s(c, r): [o, l] for (c, r), (o, l) in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "plies": s.plies,
            "since_capture": s.since_capture,
        }

    def deserialize(self, d: dict) -> UState:
        return UState(
            board={_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            winner=d["winner"],
            draw=d.get("draw", False),
            plies=d.get("plies", 0),
            since_capture=d.get("since_capture", 0),
        )

    def describe_move(self, s: UState, move: str) -> str:
        if move == "pass":
            return "pass"
        fro, to = move.split(">")
        occ = s.board.get(_cell(fro))
        letter = occ[1] if occ else "?"
        return f"{letter} {fro}-{to}"

    def render(self, s: UState, perspective=None) -> dict:
        names = {WHITE: "White", BLACK: "Black"}
        pieces = [
            {"cell": _s(c, r), "owner": o, "label": l}
            for (c, r), (o, l) in s.board.items()
        ]
        if s.winner is not None:
            caption = f"{names[s.winner]} wins (captured the King)"
        elif s.draw:
            caption = "Draw (move/no-capture limit)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
