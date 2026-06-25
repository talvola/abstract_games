"""Alice Chess — V. R. Parton, 1953 ("through the looking-glass" chess).

Two 8x8 boards, A (id 0) and B (id 1). All pieces start on board A in the
standard array; board B starts empty. A piece moves by its NORMAL chess move on
the board it currently occupies, then — "through the looking-glass" — transfers
to the CORRESPONDING square on the OTHER board. The move is legal only if that
mirror square on the other board is VACANT.

THE THREE LOOKING-GLASS RULES (Wikipedia "Alice chess"):
  1. The move must be a legal chess move on whichever board the piece occupies.
  2. The square transferred to on the OTHER board must be vacant.
  3. After the (capturing or non-capturing) move, the piece transfers to the
     corresponding square on the other board.

CAPTURES: a piece can capture only on the board on which it currently stands
(the captured piece is removed from THAT board); the capturing piece then
transfers to the empty mirror square on the other board. Sliding pieces' transit
squares must be empty on the board they are moving on (normal chess).

CHECK / CHECKMATE (the subtle part — implemented per Wikipedia):
  * After making the move on the moving board BUT BEFORE the transfer, the mover
    must NOT be in check on that board. (So you cannot escape check merely by
    transferring the king away — the move itself must resolve the check on the
    board it is played on.)
  * After the transfer, the mover must NOT be in check on EITHER board.
  * Corollary (handled automatically by the two tests above): you may be in check
    on the OTHER board before your move as long as the transferred piece
    interposes / the post-transfer position is check-free on both boards.
A king is "in check on a board" iff it is attacked, on that board, by an enemy
piece standing on that same board (attacks never cross boards). Checkmate = the
side to move is in check (on the board its king occupies) and has no legal move.

CASTLING: permitted (commonly regarded as legal in Alice chess). King and rook
must both be on board A, on their home squares, unmoved; the king's two transit
squares + landing square must be empty on board A AND vacant on board B (both
king and rook transfer to board B after castling); the king may not be in check,
move through check, or land in check (evaluated by the standard post-move tests).

EN PASSANT: OMITTED. (Wikipedia: "normally excluded"; opinions differ on the
target square. We take the common simple interpretation and leave it out.)

PROMOTION: a pawn promotes on reaching the far rank OF THE BOARD IT IS MOVING ON
(rank 7 for White, rank 0 for Black). Promotion choice =Q/R/B/N; the promoted
piece then transfers to the other board as usual.

MOVE ENCODING: "b,c,r>b2,c2,r2". Convention: BOTH endpoints name squares ON THE
MOVING BOARD, so b2 == b always (the source board). The transfer to the other
board (1-b) is IMPLICIT and applied automatically. This makes the move a simple
from>to cell path on one board for click-to-move. Promotion appends "=Q" etc.

TERMINATION: checkmate => loss; stalemate / insufficient material / a hard ply
cap / repetition => draw.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH = HEIGHT = 8
WHITE, BLACK = 0, 1
PLY_CAP = 400

# Direction sets.
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL8 = ORTHO + DIAG
KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1),
          (1, -2), (2, -1), (-1, -2), (-2, -1)]

# Sliders by (slide_dirs, leap_offsets). Pawns & kings handled specially.
SLIDERS = {
    "R": ORTHO,
    "B": DIAG,
    "Q": ALL8,
}
LEAPERS = {
    "N": KNIGHT,
    "K": ALL8,
}

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

PROMO_CHOICES = ("Q", "R", "B", "N")


def _in_bounds(c: int, r: int) -> bool:
    return 0 <= c < WIDTH and 0 <= r < HEIGHT


def _key(b: int, c: int, r: int) -> str:
    return f"{b},{c},{r}"


def _parse_cell(s: str) -> tuple:
    b, c, r = s.split(",")
    return int(b), int(c), int(r)


# A board is a dict: (c, r) -> (owner, letter).
# State.boards = (boardA, boardB).


@dataclass
class AliceState:
    boards: tuple = field(default_factory=tuple)   # (dictA, dictB)
    to_move: int = 0
    winner: Optional[int] = None                   # 0, 1, or None (draw if terminal)
    draw: bool = False
    ply: int = 0
    # repetition: count of position keys seen
    seen: dict = field(default_factory=dict)
    last: Optional[tuple] = None                    # (b, c, r) landing square (on other board)


def _setup_boards() -> tuple:
    a: dict = {}
    for c in range(WIDTH):
        a[(c, 0)] = (WHITE, BACK_RANK[c])
        a[(c, 1)] = (WHITE, "P")
        a[(c, 6)] = (BLACK, "P")
        a[(c, 7)] = (BLACK, BACK_RANK[c])
    b: dict = {}
    return (a, b)


def _enemy(p: int) -> int:
    return 1 - p


# ------------------------------------------------------------------ attacks ---
def _attacked(board: dict, c: int, r: int, by: int) -> bool:
    """Is square (c,r) attacked on this single board by side ``by``?"""
    # Sliders (rook/bishop/queen) and king (adjacent) and knight and pawn.
    # Pawns: side `by` attacks diagonally forward.
    pawn_dir = 1 if by == WHITE else -1
    for dc in (-1, 1):
        sc, sr = c - dc, r - pawn_dir
        if _in_bounds(sc, sr):
            occ = board.get((sc, sr))
            if occ is not None and occ[0] == by and occ[1] == "P":
                return True
    # Knights.
    for dc, dr in KNIGHT:
        sc, sr = c + dc, r + dr
        occ = board.get((sc, sr))
        if occ is not None and occ[0] == by and occ[1] == "N":
            return True
    # King (adjacent).
    for dc, dr in ALL8:
        sc, sr = c + dc, r + dr
        occ = board.get((sc, sr))
        if occ is not None and occ[0] == by and occ[1] == "K":
            return True
    # Sliders.
    for dirs, letters in ((ORTHO, ("R", "Q")), (DIAG, ("B", "Q"))):
        for dc, dr in dirs:
            sc, sr = c + dc, r + dr
            while _in_bounds(sc, sr):
                occ = board.get((sc, sr))
                if occ is not None:
                    if occ[0] == by and occ[1] in letters:
                        return True
                    break
                sc, sr = sc + dc, sr + dr
    return False


def _king_pos(boards: tuple, player: int):
    """Return (board_idx, c, r) of player's king, or None."""
    for bi in (0, 1):
        for (c, r), (owner, letter) in boards[bi].items():
            if owner == player and letter == "K":
                return (bi, c, r)
    return None


def _in_check_on_own_board(boards: tuple, player: int) -> bool:
    """Is player's king attacked on the board it currently stands on?"""
    kp = _king_pos(boards, player)
    if kp is None:
        return False
    bi, c, r = kp
    return _attacked(boards[bi], c, r, _enemy(player))


# --------------------------------------------------------- pseudo-legal gen ---
def _pseudo_moves(boards: tuple, player: int):
    """Yield (src_board, fc, fr, tc, tr, promo_or_None, is_castle_side).

    src_board = the board the piece moves on. (tc,tr) is the landing on that
    board. promo is a letter for pawn promotion (Q/R/B/N) else None.
    is_castle_side is None for normal moves, or 'K'/'Q' for castling.
    """
    for bi in (0, 1):
        board = boards[bi]
        other = boards[1 - bi]
        for (c, r), (owner, letter) in list(board.items()):
            if owner != player:
                continue
            if letter in SLIDERS:
                for dc, dr in SLIDERS[letter]:
                    sc, sr = c + dc, r + dr
                    while _in_bounds(sc, sr):
                        occ = board.get((sc, sr))
                        if occ is None:
                            yield (bi, c, r, sc, sr, None, None)
                        else:
                            if occ[0] != player:
                                yield (bi, c, r, sc, sr, None, None)
                            break
                        sc, sr = sc + dc, sr + dr
            elif letter in LEAPERS:
                for dc, dr in LEAPERS[letter]:
                    sc, sr = c + dc, r + dr
                    if not _in_bounds(sc, sr):
                        continue
                    occ = board.get((sc, sr))
                    if occ is None or occ[0] != player:
                        yield (bi, c, r, sc, sr, None, None)
                # Castling (king on board A only, standard squares).
                if letter == "K":
                    yield from _castle_moves(board, player, c, r, bi)
            elif letter == "P":
                yield from _pawn_moves(board, player, c, r, bi)


def _pawn_moves(board, player, c, r, bi):
    fwd = 1 if player == WHITE else -1
    start_rank = 1 if player == WHITE else 6
    promo_rank = 7 if player == WHITE else 0
    # Single push.
    nr = r + fwd
    if _in_bounds(c, nr) and board.get((c, nr)) is None:
        if nr == promo_rank:
            for pc in PROMO_CHOICES:
                yield (bi, c, r, c, nr, pc, None)
        else:
            yield (bi, c, r, c, nr, None, None)
        # Double push.
        if r == start_rank:
            nr2 = r + 2 * fwd
            if board.get((c, nr2)) is None:
                yield (bi, c, r, c, nr2, None, None)
    # Captures.
    for dc in (-1, 1):
        nc, nr = c + dc, r + fwd
        if not _in_bounds(nc, nr):
            continue
        occ = board.get((nc, nr))
        if occ is not None and occ[0] != player:
            if nr == promo_rank:
                for pc in PROMO_CHOICES:
                    yield (bi, c, r, nc, nr, pc, None)
            else:
                yield (bi, c, r, nc, nr, None, None)


def _castle_moves(board, player, c, r, bi):
    """King-side / queen-side castling on board A only, standard home squares."""
    if bi != 0:
        return
    home_r = 0 if player == WHITE else 7
    if (c, r) != (4, home_r):
        return
    if board.get((4, home_r)) != (player, "K"):
        return
    # King-side: rook on (7,home), squares 5,6 empty.
    if board.get((7, home_r)) == (player, "R") and \
            board.get((5, home_r)) is None and board.get((6, home_r)) is None:
        yield (0, 4, home_r, 6, home_r, None, "K")
    # Queen-side: rook on (0,home), squares 1,2,3 empty.
    if board.get((0, home_r)) == (player, "R") and \
            board.get((1, home_r)) is None and board.get((2, home_r)) is None and \
            board.get((3, home_r)) is None:
        yield (0, 4, home_r, 2, home_r, None, "Q")


# ------------------------------------------------------------ apply one move ---
def _resolve(boards: tuple, player: int, mv: tuple):
    """Apply a pseudo-move `mv` and return the resulting (boards, intermediate).

    Returns (new_boards, intermediate_boards) where:
      * intermediate_boards = position AFTER the on-board move (capture done) but
        BEFORE the transfer — used for the "not in check before transfer" test.
      * new_boards = position after the transfer to the other board.
    Returns None if the OTHER-board mirror landing square is occupied (illegal).
    For castling, both king and rook transfer.
    """
    bi, fc, fr, tc, tr, promo, castle = mv
    moving = dict(boards[bi])
    other = dict(boards[1 - bi])

    if castle is not None:
        home_r = fr
        # Mirror squares on the other board for king's & rook's landings.
        if castle == "K":
            king_to, rook_from, rook_to = (6, home_r), (7, home_r), (5, home_r)
        else:
            king_to, rook_from, rook_to = (2, home_r), (0, home_r), (3, home_r)
        # Other-board mirror squares (king dest + rook dest) must be vacant.
        if other.get(king_to) is not None or other.get(rook_to) is not None:
            return None
        owner = player
        # Remove king & rook from moving board.
        del moving[(fc, fr)]
        del moving[rook_from]
        # Intermediate (on moving board, before transfer): king & rook placed.
        inter = dict(moving)
        inter[king_to] = (owner, "K")
        inter[rook_to] = (owner, "R")
        inter_boards = (inter, other) if bi == 0 else (other, inter)
        # Transfer king & rook to the other board.
        new_other = dict(other)
        new_other[king_to] = (owner, "K")
        new_other[rook_to] = (owner, "R")
        new_boards = (moving, new_other) if bi == 0 else (new_other, moving)
        return (new_boards, inter_boards)

    # Normal move.
    owner, letter = boards[bi][(fc, fr)]
    if promo is not None:
        letter = promo
    # Other-board mirror landing must be vacant.
    if other.get((tc, tr)) is not None:
        return None
    # Capture on the moving board.
    del moving[(fc, fr)]
    moving.pop((tc, tr), None)  # captured piece (if any) removed
    # Intermediate position: piece sits on the moving board landing square.
    inter = dict(moving)
    inter[(tc, tr)] = (owner, letter)
    inter_boards = (inter, other) if bi == 0 else (other, inter)
    # Transfer: piece goes to the other board's mirror square.
    new_other = dict(other)
    new_other[(tc, tr)] = (owner, letter)
    new_boards = (moving, new_other) if bi == 0 else (new_other, moving)
    return (new_boards, inter_boards)


def _legal_after(boards: tuple, player: int, mv: tuple):
    """Return resulting boards if `mv` is fully legal (passes check tests), else
    None."""
    res = _resolve(boards, player, mv)
    if res is None:
        return None
    new_boards, inter_boards = res
    # 1. Not in check on the moving board AFTER the move but BEFORE the transfer.
    if _in_check_on_own_board(inter_boards, player):
        return None
    # 2. Not in check on either board AFTER the transfer. The king sits on one
    #    board; attacks never cross boards, so checking its current board suffices
    #    — but a discovered check could expose the king on whichever board it is
    #    on. _in_check_on_own_board checks exactly the board the king stands on
    #    after the transfer.
    if _in_check_on_own_board(new_boards, player):
        return None
    return new_boards


def _move_str(mv: tuple) -> str:
    bi, fc, fr, tc, tr, promo, castle = mv
    s = f"{_key(bi, fc, fr)}>{_key(bi, tc, tr)}"
    if promo is not None:
        s += f"={promo}"
    return s


def _legal_moves(boards: tuple, player: int):
    """All fully-legal move strings (with resulting boards), de-duplicated."""
    out = []
    seen_str = set()
    for mv in _pseudo_moves(boards, player):
        nb = _legal_after(boards, player, mv)
        if nb is None:
            continue
        ms = _move_str(mv)
        if ms in seen_str:
            continue
        seen_str.add(ms)
        out.append((ms, mv, nb))
    return out


def _pos_key(boards: tuple, to_move: int) -> str:
    parts = []
    for bi in (0, 1):
        for (c, r), (owner, letter) in sorted(boards[bi].items()):
            parts.append(f"{bi}{c}{r}{owner}{letter}")
    return "|".join(parts) + f"#{to_move}"


def _insufficient(boards: tuple) -> bool:
    """K vs K, K+minor vs K (ignoring which board pieces are on)."""
    pieces = []
    for bi in (0, 1):
        for (c, r), (owner, letter) in boards[bi].items():
            if letter != "K":
                pieces.append((owner, letter))
    if not pieces:
        return True
    if len(pieces) == 1 and pieces[0][1] in ("N", "B"):
        return True
    return False


class AliceChess(Game):
    uid = "alice_chess"
    name = "Alice Chess"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> AliceState:
        boards = _setup_boards()
        s = AliceState(boards=boards, to_move=WHITE, ply=0)
        s.seen = {_pos_key(boards, WHITE): 1}
        return s

    def current_player(self, s: AliceState) -> int:
        return s.to_move

    def legal_moves(self, s: AliceState):
        if self.is_terminal(s):
            return []
        return [ms for (ms, _mv, _nb) in _legal_moves(s.boards, s.to_move)]

    def apply_move(self, s: AliceState, move: str, rng=None) -> AliceState:
        if self.is_terminal(s):
            raise ValueError("game over")
        player = s.to_move
        target = None
        for (ms, mv, nb) in _legal_moves(s.boards, player):
            if ms == move:
                target = (mv, nb)
                break
        if target is None:
            raise ValueError(f"illegal move {move!r}")
        mv, new_boards = target
        bi, fc, fr, tc, tr, promo, castle = mv
        opp = _enemy(player)

        seen = dict(s.seen)
        pk = _pos_key(new_boards, opp)
        rep = seen.get(pk, 0) + 1
        seen[pk] = rep
        ply = s.ply + 1

        ns = AliceState(
            boards=new_boards, to_move=opp, winner=None, draw=False,
            ply=ply, seen=seen, last=(1 - bi, tc, tr),
        )

        # Did this move checkmate / stalemate the opponent?
        opp_moves = _legal_moves(new_boards, opp)
        if not opp_moves:
            if _in_check_on_own_board(new_boards, opp):
                ns.winner = player          # checkmate
            else:
                ns.draw = True              # stalemate
            return ns
        # Draw conditions.
        if rep >= 3 or _insufficient(new_boards) or ply >= PLY_CAP:
            ns.draw = True
        return ns

    def is_terminal(self, s: AliceState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: AliceState):
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def serialize(self, s: AliceState) -> dict:
        return {
            "boards": [
                {f"{c},{r}": [owner, letter]
                 for (c, r), (owner, letter) in s.boards[bi].items()}
                for bi in (0, 1)
            ],
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "ply": s.ply,
            "seen": dict(s.seen),
            "last": (list(s.last) if s.last is not None else None),
        }

    def deserialize(self, d: dict) -> AliceState:
        boards = tuple(
            {
                (lambda cr: (int(cr[0]), int(cr[1])))(k.split(",")):
                    (int(v[0]), v[1])
                for k, v in d["boards"][bi].items()
            }
            for bi in (0, 1)
        )
        last = d.get("last")
        return AliceState(
            boards=boards,
            to_move=d["to_move"],
            winner=d.get("winner"),
            draw=d.get("draw", False),
            ply=d.get("ply", 0),
            seen=dict(d.get("seen", {})),
            last=(tuple(last) if last is not None else None),
        )

    def describe_move(self, s: AliceState, move: str) -> str:
        head = move.split("=")
        promo = head[1] if len(head) > 1 else None
        frm, to = head[0].split(">")
        bi, fc, fr = _parse_cell(frm)
        _, tc, tr = _parse_cell(to)
        occ = s.boards[bi].get((fc, fr))
        letter = occ[1] if occ else "?"
        board_name = "A" if bi == 0 else "B"
        files = "abcdefgh"
        src = f"{files[fc]}{fr + 1}"
        dst = f"{files[tc]}{tr + 1}"
        # Castling shorthand.
        if letter == "K" and abs(tc - fc) == 2:
            base = "O-O" if tc > fc else "O-O-O"
            return f"{base}({board_name})"
        s2 = f"{letter}{src}-{dst}({board_name})"
        if promo:
            s2 += f"={promo}"
        return s2

    # ---- presentation ------------------------------------------------------
    def render(self, s: AliceState, perspective=None) -> dict:
        GAP = 1.5
        # Two 8x8 boards side by side: board 0 left, board 1 right.
        # Row 0 (White home) at the BOTTOM, so draw oy = (HEIGHT-1 - r).
        light = "#ecdab9"
        dark = "#b58863"
        # Slightly tint board B distinctly so the two are easy to tell apart.
        lightB = "#cfe0ec"
        darkB = "#7fa6c9"
        cells = []
        tints = {}
        for bi in (0, 1):
            bx = bi * (WIDTH + GAP)
            for c in range(WIDTH):
                for r in range(HEIGHT):
                    ox = bx + c
                    oy = (HEIGHT - 1 - r)
                    pts = [
                        [round(ox, 3), round(oy, 3)],
                        [round(ox + 1, 3), round(oy, 3)],
                        [round(ox + 1, 3), round(oy + 1, 3)],
                        [round(ox, 3), round(oy + 1, 3)],
                    ]
                    cid = _key(bi, c, r)
                    cells.append({"id": cid, "points": pts})
                    is_light = (c + r) % 2 == 1
                    if bi == 0:
                        tints[cid] = light if is_light else dark
                    else:
                        tints[cid] = lightB if is_light else darkB

        pieces = []
        for bi in (0, 1):
            for (c, r), (owner, letter) in s.boards[bi].items():
                pieces.append({"cell": _key(bi, c, r), "owner": owner,
                               "label": letter})

        highlights = []
        if s.last is not None:
            highlights.append({"cell": _key(*s.last), "kind": "last-move"})

        names = {0: "White", 1: "Black"}
        if s.winner is not None:
            caption = f"{names[s.winner]} wins by checkmate"
        elif s.draw:
            caption = "Draw"
        else:
            chk = _in_check_on_own_board(s.boards, s.to_move)
            caption = f"{names[s.to_move]} to move (board A left, B right)"
            if chk:
                caption += " — CHECK"

        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
