"""Chess960 (Fischer Random Chess) -- standard chess with a randomized back rank.

Built on :class:`agp.chesslike.ChessLike`. Everything except the starting position
and castling is orthodox chess: normal piece moves, the standard pawn (double step
+ en passant), last-rank promotion to Q/R/B/N, check / checkmate / stalemate, and
draws by the fifty-move rule, threefold repetition and insufficient material -- all
inherited from ChessLike. White = player 0.

Randomized setup
----------------
``initial_state`` builds one of the 960 legal Chess960 back ranks using the passed
``rng`` (or a ``position`` option, 0..959, to force a specific id; standard chess is
#518 = RNBQKBNR). The chosen back rank satisfies the three constraints: the two
bishops sit on opposite-colour squares, the king stands strictly between the two
rooks, and Black mirrors White on the same files. The arrangement is STORED in the
state (as the king/rook home files) so it round-trips and replays deterministically.

Castling (by final squares -- the Chess960 rule)
------------------------------------------------
Castling is defined by the king's and rook's FINAL squares (king to the c-file for
queenside / g-file for kingside; rook to the d-file / f-file respectively),
regardless of their starting files. Conditions: neither the king nor that rook has
moved; every square between the king's start and end and between the rook's start
and end is empty except for the castling king and rook themselves; and the king does
not start in, pass through, or land on an attacked square.

To stay unambiguous (a Chess960 king can start adjacent to its destination, so a
"king moves two files" test is unreliable), a castling move is encoded as the king
moving onto its OWN rook's square ("king captures rook" -- the FIDE Chess960
convention). In the UI: click the king, then click the rook you want to castle with.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, Castling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, cell,
)

STANDARD_960 = 518   # RNBQKBNR -- ordinary chess


# --------------------------------------------------------------------------- #
# Generating a Chess960 back rank
# --------------------------------------------------------------------------- #
def back_rank_from_id(idx: int) -> list:
    """The Scharnagl numbering: map a 0..959 id to a back-rank list of 8 letters.

    Bishops on opposite colours, king between the two rooks. This is the standard
    construction used by FIDE / Wikipedia; #518 == RNBQKBNR (ordinary chess).
    """
    if not (0 <= idx < 960):
        raise ValueError("Chess960 position id must be in 0..959")
    rank = [None] * 8
    n = idx
    # Light-square bishop: files 1,3,5,7 (the light squares of rank 1, 0-indexed odd).
    n, b1 = divmod(n, 4)
    rank[(1, 3, 5, 7)[b1]] = "B"
    # Dark-square bishop: files 0,2,4,6.
    n, b2 = divmod(n, 4)
    rank[(0, 2, 4, 6)[b2]] = "B"
    # Queen on the q-th remaining empty file.
    n, q = divmod(n, 6)
    empties = [i for i in range(8) if rank[i] is None]
    rank[empties[q]] = "Q"
    # The remaining three empty files take one of 10 knight arrangements; the two
    # leftover files are the rooks, and the king goes between them.
    knight_tables = [
        (0, 1), (0, 2), (0, 3), (0, 4),
        (1, 2), (1, 3), (1, 4),
        (2, 3), (2, 4),
        (3, 4),
    ]
    empties = [i for i in range(8) if rank[i] is None]   # exactly 5 files
    k1, k2 = knight_tables[n]
    rank[empties[k1]] = "N"
    rank[empties[k2]] = "N"
    rest = [i for i in range(8) if rank[i] is None]       # exactly 3 files, ascending
    rank[rest[0]] = "R"
    rank[rest[1]] = "K"
    rank[rest[2]] = "R"
    return rank


def validate_back_rank(rank: list) -> None:
    """Assert the three Chess960 constraints (used by the selftest)."""
    bishops = [i for i, t in enumerate(rank) if t == "B"]
    rooks = [i for i, t in enumerate(rank) if t == "R"]
    king = rank.index("K")
    assert len(bishops) == 2 and (bishops[0] % 2) != (bishops[1] % 2), \
        f"bishops not on opposite colours: {rank}"
    assert len(rooks) == 2 and rooks[0] < king < rooks[1], \
        f"king not between rooks: {rank}"
    assert sorted(rank) == ["B", "B", "K", "N", "N", "Q", "R", "R"], \
        f"wrong piece multiset: {rank}"


# --------------------------------------------------------------------------- #
# State: ordinary CState plus the (constant) king/rook home files.
# --------------------------------------------------------------------------- #
@dataclass
class C9State(CState):
    # (king_file, queenside_rook_file, kingside_rook_file); same for both colours.
    homes: tuple = (4, 0, 7)


# --------------------------------------------------------------------------- #
# Chess960 castling (final-square rule, arbitrary start files)
# --------------------------------------------------------------------------- #
class Chess960Castling(Castling):
    """Castling generation that reads the home files from the state.

    Rights are the orthodox ``"KQkq"`` chars (K/Q = White king/queen side, k/q =
    Black). A right exists iff that rook and the king are both unmoved, so while a
    right is present its rook is still on its home file. Rook-target files: kingside
    rook -> f-file (5), queenside rook -> d-file (3); king-target files: g-file (6)
    kingside, c-file (2) queenside. The castling MOVE is encoded as king -> own-rook
    square; :meth:`is_castle` recognises it.
    """

    SIDE_BY_FLAG = {"K": ("kingside", WHITE), "Q": ("queenside", WHITE),
                    "k": ("kingside", BLACK), "q": ("queenside", BLACK)}
    FLAGS_BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
    KING_TARGET = {"kingside": 6, "queenside": 2}   # g-file / c-file
    ROOK_TARGET = {"kingside": 5, "queenside": 3}   # f-file / d-file

    def initial_rights(self):
        return frozenset("KQkq")

    @staticmethod
    def _rank(player):
        return 0 if player == WHITE else 7

    @staticmethod
    def _rook_file(homes, side):
        # homes = (king_file, qrook_file, krook_file)
        return homes[2] if side == "kingside" else homes[1]

    def _between(self, a, b):
        lo, hi = (a, b) if a <= b else (b, a)
        return range(lo, hi + 1)

    def _castle_legal(self, core, state, player, side):
        homes = state.homes
        rank = self._rank(player)
        kfile = homes[0]
        rfile = self._rook_file(homes, side)
        kfrom = (kfile, rank)
        rfrom = (rfile, rank)
        if state.board.get(kfrom) != (player, "K") or state.board.get(rfrom) != (player, "R"):
            return None
        kto = (self.KING_TARGET[side], rank)
        rto = (self.ROOK_TARGET[side], rank)
        enemy = 1 - player
        # Every square the king and rook pass through / land on must be empty,
        # except the two castling pieces themselves.
        occupied_ok = {kfrom, rfrom}
        for f in self._between(kfile, kto[0]):
            sq = (f, rank)
            if sq not in occupied_ok and sq in state.board:
                return None
        for f in self._between(rfile, rto[0]):
            sq = (f, rank)
            if sq not in occupied_ok and sq in state.board:
                return None
        # King may not start in, pass through, or land on an attacked square.
        for f in self._between(kfile, kto[0]):
            if core.attacked(state.board, f, rank, enemy):
                return None
        return kfrom, rfrom, kto, rto

    def moves(self, core, state):
        player = state.to_move
        if core.in_check(state.board, player):
            return
        for flag in self.FLAGS_BY_COLOR[player]:
            if flag not in state.castling:
                continue
            side, _ = self.SIDE_BY_FLAG[flag]
            res = self._castle_legal(core, state, player, side)
            if res is not None:
                kfrom, rfrom, _, _ = res
                yield kfrom, rfrom            # king -> own rook square (the encoding)

    def is_castle(self, state, frm, to, player):
        """Return (kfrom, rfrom, kto, rto) if frm->to is a legal-shape castle here."""
        if state.board.get(frm) != (player, "K"):
            return None
        if state.board.get(to) != (player, "R"):
            return None
        homes = state.homes
        rank = self._rank(player)
        if to[1] != rank or frm[1] != rank:
            return None
        side = "kingside" if to[0] == homes[2] else "queenside" if to[0] == homes[1] else None
        if side is None:
            return None
        return (frm, to, (self.KING_TARGET[side], rank), (self.ROOK_TARGET[side], rank))

    def update_rights(self, rights, frm, to, board, homes):
        rights = set(rights)
        pl, t = board[frm]
        rank = self._rank(pl)
        kfile, qrook, krook = homes
        if t == "K" and frm == (kfile, rank):
            rights -= set(self.FLAGS_BY_COLOR[pl])
        # A rook leaving its home square loses the corresponding right.
        for who, hr in ((WHITE, 0), (BLACK, 7)):
            kf = self.FLAGS_BY_COLOR[who]
            if frm == (krook, hr):
                rights.discard(kf[0])
            if frm == (qrook, hr):
                rights.discard(kf[1])
            # A rook captured on its home square also kills the right.
            if to == (krook, hr):
                rights.discard(kf[0])
            if to == (qrook, hr):
                rights.discard(kf[1])
        return frozenset(rights)


class Chess960(ChessLike):
    uid = "chess960"
    name = "Chess960"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    CASTLING = Chess960Castling()

    @property
    def num_players(self) -> int:
        return 2

    def setup_board(self) -> dict:   # not used (initial_state builds it), but required
        return self._board_from_rank(back_rank_from_id(STANDARD_960))

    @staticmethod
    def _board_from_rank(rank):
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, rank[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, rank[c])
        return b

    @staticmethod
    def _homes_from_rank(rank):
        rooks = [i for i, t in enumerate(rank) if t == "R"]
        return (rank.index("K"), rooks[0], rooks[1])

    def initial_state(self, options=None, rng=None):
        options = options or {}
        pos = options.get("position", "random")
        if pos in (None, "random", ""):
            r = rng if rng is not None else random.Random()
            idx = r.randrange(960)
        else:
            idx = int(pos)
        rank = back_rank_from_id(idx)
        board = self._board_from_rank(rank)
        homes = self._homes_from_rank(rank)
        st = C9State(board=board, to_move=WHITE,
                     castling=self.CASTLING.initial_rights(), ep=None, homes=homes)
        st.reps = {self._poskey_state(st): 1}
        return st

    # ---- apply (override only the castling + rights handling) ---------------
    def apply_move(self, state, move, rng=None):
        promo = None
        m = move
        if "=" in m:
            m, promo = m.split("=")
        fs, ts = m.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]

        castle = self.CASTLING.is_castle(state, frm, to, pl) if t == "K" else None
        b = dict(state.board)
        if castle is not None:
            kfrom, rfrom, kto, rto = castle
            b.pop(kfrom)
            b.pop(rfrom)
            b[kto] = (pl, "K")
            b[rto] = (pl, "R")
            castling = self.CASTLING.update_rights(state.castling, frm, to,
                                                   state.board, state.homes)
            key = self._poskey(b, 1 - pl, castling, None)
            reps = dict(state.reps)
            reps[key] = reps.get(key, 0) + 1
            return C9State(board=b, to_move=1 - pl, castling=castling, ep=None,
                           halfmove=state.halfmove + 1, ply=state.ply + 1,
                           reps=reps, homes=state.homes)

        b.pop(frm)
        capture = to in state.board
        captured_sq = to if capture else None
        ep_new = None
        if t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                captured_sq = state.ep[1]
                b.pop(captured_sq, None)
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)
        if t == "P" and promo:
            t = promo
        b[to] = (pl, t)

        castling = self.CASTLING.update_rights(state.castling, frm, to,
                                               state.board, state.homes)
        reset = capture or state.board[frm][1] == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return C9State(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                       halfmove=0 if reset else state.halfmove + 1,
                       ply=state.ply + 1, reps=reps, homes=state.homes)

    # ---- (de)serialize: carry the home files --------------------------------
    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["homes"] = list(state.homes)
        return d

    def deserialize(self, d: dict):
        base = super().deserialize(d)
        homes = tuple(d.get("homes", (4, 0, 7)))
        return C9State(board=base.board, to_move=base.to_move,
                       castling=base.castling, ep=base.ep, halfmove=base.halfmove,
                       ply=base.ply, reps=base.reps, homes=homes)

    # ---- move log notation --------------------------------------------------
    def describe_move(self, state, move) -> str:
        raw = move.split("=")[0]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        if t == "K" and self.CASTLING.is_castle(state, frm, to, pl) is not None:
            return "O-O" if to[0] == state.homes[2] else "O-O-O"
        return super().describe_move(state, move)
