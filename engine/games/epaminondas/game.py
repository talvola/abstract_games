"""Epaminondas (Robert Abbott, 1975) -- the phalanx war game.

Board: 14 columns x 12 rows. Coordinates are "c,r" with 0 <= c < 14 and
0 <= r < 12. Player 0 starts on rows 0-1 (its home/back row is row 0); player 1
starts on rows 10-11 (its home/back row is row 11). Player 0 (Red) moves first.

PHALANX
    A phalanx is a MAXIMAL straight line of one or more friendly pieces that are
    adjacent to each other along one of the eight directions (the four
    orthogonals and the four diagonals). "Maximal" means it cannot be extended
    by another friendly piece at either end along that same axis. A single piece
    is a phalanx of length 1 (in any of the four axes).

MOVE
    Pick a phalanx and a direction ALONG ITS OWN AXIS (forward or backward along
    the line). A phalanx of length L may advance 1..L squares: the whole line of
    pieces slides that many steps, the trailing k squares vacating and k new
    squares at the front being occupied. Every square the front passes through,
    and every destination square, must be EMPTY -- a phalanx may not move onto or
    through a friendly piece, and may not jump any piece.

CAPTURE
    A phalanx may capture an opposing phalanx that lies directly ahead on the
    SAME line if and only if the moving phalanx is STRICTLY LONGER. The mover
    advances so its FRONT piece lands exactly on the FRONT square of the enemy
    phalanx (the enemy front must be reachable within the move distance, i.e.
    within L squares of the mover's front, and all squares between the mover's
    front and the enemy front must be empty). The ENTIRE enemy phalanx lying on
    that line is then removed. You may never capture an enemy phalanx of equal or
    greater length, and you may never capture by moving through any piece.

WIN -- the "crossing"
    Player 0's back row is row 0; player 1's back row is row 11. You achieve a
    "crossing" when you have pieces on the OPPONENT's back row. The win is the
    standard deferred crossing: a crossing wins only if the opponent cannot
    immediately equalize-or-better it on their single reply.

    Implemented precisely: after EVERY move, we look at the player who is NOT to
    move next (the opponent of the mover -- the player who just received a free
    reply). Let X = that player's piece count on the mover's back row, and
    Y = the mover's piece count on that player's back row. If X > Y, that player
    wins immediately. Equivalently: when you cross, your opponent gets exactly
    one move to capture your crossing piece or to place an equal-or-greater
    count on YOUR back row; if at the end of that reply you still hold a strict
    majority on their back row, you win. (A player who crosses and whose
    opponent then fails to reduce the deficit to <= 0 wins.)

    See rules.md for the worked statement of this rule and the documented
    interpretation. A player with no pieces, or with no legal move on their
    turn, loses.

A ply cap declares a draw if play drags on (guarantees termination).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

W, H = 14, 12
PLY_CAP = 400
# Four axes (each used in both directions); diagonals included.
AXES = [(1, 0), (0, 1), (1, 1), (1, -1)]
# Back (home) row of each player.
BACK_ROW = {0: 0, 1: H - 1}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


def _start_board() -> dict:
    b = {}
    for c in range(W):
        b[(c, 0)] = 0
        b[(c, 1)] = 0
        b[(c, H - 2)] = 1
        b[(c, H - 1)] = 1
    return b


def _phalanx_length(board: dict, c: int, r: int, dc: int, dr: int, player: int) -> int:
    """Length of the maximal friendly line through (c,r) along axis (dc,dr)."""
    count = 1
    for sgn in (1, -1):
        cc, rr = c + sgn * dc, r + sgn * dr
        while _on(cc, rr) and board.get((cc, rr)) == player:
            count += 1
            cc += sgn * dc
            rr += sgn * dr
    return count


def _is_head(board: dict, c: int, r: int, dc: int, dr: int, player: int) -> bool:
    """True if (c,r) is the leading end of its phalanx in direction (dc,dr):
    i.e. there's no friendly piece one step further along (dc,dr)."""
    nc, nr = c + dc, r + dr
    return board.get((nc, nr)) != player


def _back_count(board: dict, player: int) -> int:
    """How many of `player`'s pieces sit on the OPPONENT's back row (a crossing)."""
    opp_back = BACK_ROW[1 - player]
    return sum(1 for (c, r), p in board.items() if p == player and r == opp_back)


@dataclass
class EpamState:
    board: dict = field(default_factory=dict)  # (c, r) -> 0/1
    to_move: int = 0
    winner: Optional[int] = None
    drawn: bool = False
    ply: int = 0
    last_move: Optional[tuple] = None  # (from_cell, to_cell) for rendering


class Epaminondas(Game):
    uid = "epaminondas"
    name = "Epaminondas"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> EpamState:
        return EpamState(board=_start_board())

    def current_player(self, s: EpamState) -> int:
        return s.to_move

    # ----- move generation -------------------------------------------------
    def _raw_moves(self, s: EpamState) -> list[str]:
        board, player = s.board, s.to_move
        out = []
        seen = set()  # dedupe (front_cell, direction) -- each phalanx head emits once per dir
        for (c, r), pl in list(board.items()):
            if pl != player:
                continue
            for dc, dr in AXES:
                for sgn in (1, -1):
                    sdc, sdr = sgn * dc, sgn * dr
                    # Only generate from the HEAD (leading end) of the phalanx in
                    # the chosen direction, so each phalanx/direction is unique.
                    if not _is_head(board, c, r, sdc, sdr, player):
                        continue
                    L = _phalanx_length(board, c, r, dc, dr, player)
                    key = ((c, r), sdc, sdr)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.extend(self._moves_for_head(board, c, r, sdc, sdr, L, player))
        return out

    def _moves_for_head(self, board, fc, fr, sdc, sdr, L, player):
        """Generate move strings for the phalanx whose head is (fc,fr), moving in
        direction (sdc,sdr). The phalanx has length L; the rear cell is
        (fc - (L-1)*sdc, fr - (L-1)*sdr)."""
        out = []
        rear_c = fc - (L - 1) * sdc
        rear_r = fr - (L - 1) * sdr
        # Walk forward from the head; collect empty squares and detect an enemy.
        empty_run = 0  # consecutive empty squares directly ahead of the head
        for k in range(1, L + 1):
            tc, tr = fc + sdc * k, fr + sdr * k
            if not _on(tc, tr):
                break
            occ = board.get((tc, tr))
            if occ is None:
                empty_run += 1
                # Non-capturing slide of `k` steps: whole phalanx shifts k.
                # Encode as head-from > head-to so the UI can click it.
                out.append(f"{rear_c},{rear_r}>{tc},{tr}")
            elif occ == player:
                # blocked by own piece -- cannot slide or capture further
                break
            else:
                # enemy at (tc,tr). To capture, the enemy FRONT must be exactly
                # this square (i.e. enemy phalanx faces us head-on here) and all
                # k-1 squares before it were empty (empty_run == k-1).
                if empty_run == k - 1:
                    # measure enemy phalanx length along this axis from its
                    # front square (tc,tr), extending away from the mover.
                    elen = _enemy_len_ahead(board, tc, tr, sdc, sdr, 1 - player)
                    if L > elen:
                        out.append(f"{rear_c},{rear_r}>{tc},{tr}")
                # cannot pass through enemy regardless
                break
        return out

    # ----- apply -----------------------------------------------------------
    def apply_move(self, s: EpamState, move: str, rng=None) -> EpamState:
        fs, ts = move.split(">")
        from_cell, to_cell = _cell(fs), _cell(ts)
        mover = s.to_move
        board = dict(s.board)

        rc, rr = from_cell  # rear cell of the phalanx
        tc, tr = to_cell    # destination of the HEAD

        # Reconstruct the move geometry. Direction from rear to head:
        # the phalanx lies along some axis; the head is the leading cell.
        # We know rear and the head-destination; the slide distance and axis are
        # derivable, but more robustly we recompute from the board.
        # Find the axis/direction: the head was at some cell; phalanx ran from
        # rear backward... Actually rear is the trailing cell, head leads. We
        # find direction (sdc,sdr) such that there is a friendly run starting at
        # rear heading toward to_cell.
        sdc, sdr, L, head = self._reconstruct(board, rc, rr, tc, tr, mover)

        # The phalanx cells: head, head-step, ... rear.
        phalanx = [(head[0] - sdc * i, head[1] - sdr * i) for i in range(L)]
        # Slide distance k: head moves from `head` to `to_cell`.
        k = (tc - head[0]) // sdc if sdc != 0 else (tr - head[1]) // sdr

        # Determine capture: is the destination occupied by an enemy?
        captured = []
        if board.get((tc, tr)) == 1 - mover:
            # remove the whole enemy phalanx lying ahead on this line (its front
            # square is (tc,tr), extending away from the mover).
            captured = _enemy_chain_ahead(board, tc, tr, sdc, sdr, 1 - mover)

        for cell in captured:
            del board[cell]
        # Move the phalanx: remove old cells, add shifted cells.
        for cell in phalanx:
            del board[cell]
        for (pc, pr) in phalanx:
            board[(pc + sdc * k, pr + sdr * k)] = mover

        ply = s.ply + 1
        winner, drawn = None, False

        # Crossing win: evaluate for the OPPONENT of the mover (they just got
        # their free reply). If they hold a strict majority on the mover's back
        # row, they win now.
        opp = 1 - mover
        opp_cross = _back_count(board, opp)   # opp pieces on mover's back row
        mover_cross = _back_count(board, mover)  # mover pieces on opp's back row
        if opp_cross > mover_cross and opp_cross > 0:
            winner = opp

        # Annihilation / no-piece loss is handled in returns/is_terminal via
        # the no-move check below; but a side with zero pieces also loses.
        if winner is None:
            if not any(p == opp for p in board.values()):
                winner = mover
            elif not any(p == mover for p in board.values()):
                winner = opp

        if winner is None and ply >= PLY_CAP:
            drawn = True

        return EpamState(board=board, to_move=opp, winner=winner, drawn=drawn,
                         ply=ply, last_move=(from_cell, to_cell))

    def _reconstruct(self, board, rc, rr, tc, tr, mover):
        """Given the rear cell (rc,rr) of a friendly phalanx and the head's
        destination (tc,tr), find direction (sdc,sdr), length L, and head cell."""
        for dc, dr in AXES:
            for sgn in (1, -1):
                sdc, sdr = sgn * dc, sgn * dr
                # destination must lie strictly ahead of rear along (sdc,sdr)
                ddc, ddr = tc - rc, tr - rr
                # check colinear & same direction
                steps = None
                if sdc != 0:
                    if ddc % sdc != 0:
                        continue
                    steps = ddc // sdc
                    if steps <= 0:
                        continue
                    if ddr != steps * sdr:
                        continue
                else:
                    if ddc != 0:
                        continue
                    if sdr == 0:
                        continue
                    if ddr % sdr != 0:
                        continue
                    steps = ddr // sdr
                    if steps <= 0:
                        continue
                # rear must be the trailing end of a friendly phalanx heading (sdc,sdr)
                if board.get((rc, rr)) != mover:
                    continue
                # not extendable backward
                if board.get((rc - sdc, rr - sdr)) == mover:
                    continue
                L = _phalanx_length(board, rc, rr, dc, dr, mover)
                head = (rc + sdc * (L - 1), rr + sdr * (L - 1))
                # head-to-dest distance must be within 1..L
                k = (tc - head[0]) // sdc if sdc != 0 else (tr - head[1]) // sdr
                if 1 <= k <= L:
                    return sdc, sdr, L, head
        raise ValueError(f"cannot reconstruct move rear={rc,rr} dest={tc,tr}")

    # ----- terminal --------------------------------------------------------
    def is_terminal(self, s: EpamState) -> bool:
        if s.winner is not None or s.drawn:
            return True
        return not self._raw_moves(s)

    def legal_moves(self, s: EpamState) -> list[str]:
        if s.winner is not None or s.drawn:
            return []
        return self._raw_moves(s)

    def returns(self, s: EpamState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        if s.drawn:
            return [0.0, 0.0]
        # terminal because the player to move has no move: they lose
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    # ----- serialize -------------------------------------------------------
    def serialize(self, s: EpamState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "winner": s.winner,
            "drawn": s.drawn,
            "ply": s.ply,
            "last_move": (
                [f"{s.last_move[0][0]},{s.last_move[0][1]}",
                 f"{s.last_move[1][0]},{s.last_move[1][1]}"]
                if s.last_move else None
            ),
        }

    def deserialize(self, d: dict) -> EpamState:
        lm = d.get("last_move")
        return EpamState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], winner=d.get("winner"),
            drawn=d.get("drawn", False), ply=d.get("ply", 0),
            last_move=(_cell(lm[0]), _cell(lm[1])) if lm else None,
        )

    def describe_move(self, s: EpamState, move: str) -> str:
        fs, ts = move.split(">")
        frm, to = _cell(fs), _cell(ts)
        cap = s.board.get(to) is not None
        return f"{fs}{'x' if cap else '-'}{ts}"

    # ----- render ----------------------------------------------------------
    def render(self, s: EpamState, perspective=None) -> dict:
        names = {0: "Red", 1: "Blue"}
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": ""}
                  for (c, r), p in s.board.items()]
        highlights = []
        if s.last_move:
            (fc, fr), (tc, tr) = s.last_move
            highlights.append({"cell": f"{tc},{tr}", "kind": "last-move"})
        if s.winner is not None:
            caption = f"{names[s.winner]} wins"
        elif s.drawn:
            caption = "Draw (ply cap)"
        else:
            c0 = _back_count(s.board, 0)
            c1 = _back_count(s.board, 1)
            cross = ""
            if c0 or c1:
                cross = f"  (crossings R:{c0} B:{c1})"
            caption = f"{names[s.to_move]} to move{cross}"
        # tint each player's back row so the crossing objective is visible
        tints = {}
        for c in range(W):
            tints[f"{c},{BACK_ROW[0]}"] = "#553333"
            tints[f"{c},{BACK_ROW[1]}"] = "#333355"
        return {
            "board": {"type": "square", "width": W, "height": H, "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }


def _enemy_len_ahead(board, tc, tr, sdc, sdr, enemy):
    """Length of the enemy phalanx that lies directly ahead, starting at its
    FRONT square (tc,tr) and extending AWAY from the mover (continuing in the
    mover's travel direction sdc,sdr)."""
    length = 1
    cc, rr = tc + sdc, tr + sdr
    while _on(cc, rr) and board.get((cc, rr)) == enemy:
        length += 1
        cc += sdc
        rr += sdr
    return length


def _enemy_chain_ahead(board, tc, tr, sdc, sdr, enemy):
    """Cells of the enemy phalanx whose front is (tc,tr), extending in the
    mover's travel direction."""
    cells = [(tc, tr)]
    cc, rr = tc + sdc, tr + sdr
    while _on(cc, rr) and board.get((cc, rr)) == enemy:
        cells.append((cc, rr))
        cc += sdc
        rr += sdr
    return cells
