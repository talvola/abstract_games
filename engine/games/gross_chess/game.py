"""Gross Chess (Fergus Duniho, 2009) -- 12x12, built on the shared ChessLike core.

Source of truth: https://www.chessvariants.com/large.dir/gross.html

Standard chess army plus, per side: 2 Marshalls M (rook+knight), 2 Archbishops A
(bishop+knight), 2 Champions S (wazir+dabbaba+alfil, from Omega Chess), 2 Wizards
W (ferz+camel, from Omega Chess), 2 Cannons C (rook-mover, hop-capture, from
Xiangqi) and 2 Vaos V (bishop-mover, hop-capture), and 12 pawns.

Differences from FIDE handled here:

* Cannon/Vao hop-capture can't be expressed in the (slides, leaps) table, so
  ``_pseudo`` and ``attacked`` are overridden to add the hopper mechanics.
* Pawns may make an initial move of two OR THREE squares; en passant applies on
  EVERY square passed over (Omega-Chess style), so ``state.ep`` holds
  ``((target, ...), captured_square)`` -- a tuple of targets -- and the methods
  that touch ep (``apply_move``, ``_apply_board``, ``serialize``/``deserialize``,
  ``describe_move``) are overridden to match.
* Flexible (Grotesque-Chess) castling: the king slides two or more squares toward
  a rook and the rook leaps to the square just behind it (they end adjacent).
  King g2/g11, rooks b/k on the same rank -- see ``GrossCastling``.
* Grand-Chess-style reserve promotion on the last three ranks, with rank tiers
  and an enlarged reserve (extra 2Q/4R/4N/4B) -- see ``GrossPromotion``.

White = player 0, moving toward higher rows. Files a..l = cols 0..11,
ranks 1..12 = rows 0..11.
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, PawnRules, PromotionRules, Castling, cell,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, _FILES,
)

CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]
FERZ = list(DIAG)
WAZIR = list(ORTHO)
DABBABA = [(2, 0), (-2, 0), (0, 2), (0, -2)]
ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]

# Hop-capturers: move like a rider along these directions, capture by jumping
# exactly one screen (any colour) and landing on the first piece beyond it.
HOPPERS = {"C": ORTHO, "V": DIAG}


class GrossPawn(PawnRules):
    """Orthodox pawn, but the initial move may be one, two or three squares, and
    en passant is available on every square the pawn passed over (the capturer
    steps diagonally forward onto a passed square; the passer is removed from
    its landing square). ``ep_targets`` is a tuple of passed squares or None."""

    def pseudo(self, core, board, c, r, player, ep_targets):
        fwd = self.fwd(player)
        if core.on(c, r + fwd) and (c, r + fwd) not in board:
            yield (c, r), (c, r + fwd)
            if r == self.start(player):
                if core.on(c, r + 2 * fwd) and (c, r + 2 * fwd) not in board:
                    yield (c, r), (c, r + 2 * fwd)
                    if core.on(c, r + 3 * fwd) and (c, r + 3 * fwd) not in board:
                        yield (c, r), (c, r + 3 * fwd)
        for dc in (-1, 1):
            t = (c + dc, r + fwd)
            if not core.on(*t):
                continue
            occ = board.get(t)
            if (occ is not None and occ[0] != player) or (ep_targets and t in ep_targets):
                yield (c, r), t

    def attacks(self, core, board, c, r, by) -> bool:
        pr = r - self.fwd(by)
        return any(board.get((c + dc, pr)) == (by, "P") for dc in (-1, 1))

    def ep_after(self, frm, to):
        """After a 2- or 3-square initial step: ((passed squares...), landing)."""
        d = abs(to[1] - frm[1])
        if d >= 2:
            step = 1 if to[1] > frm[1] else -1
            targets = tuple((frm[0], frm[1] + step * i) for i in range(1, d))
            return (targets, to)
        return None


class GrossPromotion(PromotionRules):
    """Promotion on the last three ranks, only to a piece held in reserve.
    The reserve = this player's captured pieces plus extras (2 Queens, 4 Rooks,
    4 Knights, 4 Bishops), which the source models exactly as: a player may
    never have more pieces of a type in play than POOL[type] (starting count +
    extras). Rank tiers: 10th rank -> minor colorbound/short-range pieces only
    (B N V W); 11th -> those plus S C R; 12th (last, compulsory) -> anything
    available including A M Q."""

    POOL = {"Q": 3, "M": 2, "A": 2, "R": 6, "C": 2, "S": 2,
            "B": 6, "N": 6, "V": 2, "W": 2}
    TIER_3RD_LAST = ("B", "N", "V", "W")
    TIER_2ND_LAST = ("R", "C", "S", "B", "N", "V", "W")
    TIER_LAST = ("Q", "M", "A", "R", "C", "S", "B", "N", "V", "W")

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        H = core.HEIGHT
        rank = to[1] if pl == WHITE else H - 1 - to[1]   # 0-based from own side
        if rank < H - 3:
            return [None]
        cnt = {}
        for (pl2, t) in state.board.values():
            if pl2 == pl:
                cnt[t] = cnt.get(t, 0) + 1
        tier = (self.TIER_3RD_LAST if rank == H - 3 else
                self.TIER_2ND_LAST if rank == H - 2 else self.TIER_LAST)
        avail = [T for T in tier if cnt.get(T, 0) < self.POOL[T]]
        if rank == H - 1:
            return avail          # compulsory (never empty in practice)
        return [None] + avail


class GrossCastling(Castling):
    """Grotesque-Chess flexible castling: the king moves two or more squares
    along its rank toward a rook, and the rook leaps over the king to the
    passed square nearest it, so they end adjacent. Conditions: neither piece
    has moved, ALL squares strictly between king and rook are empty, and the
    king is not in check on any square from its start through its destination.

    King home g2/g11 (col 6, rows 1/10); rooks b/k files (cols 1 and 10)."""

    KING_COL = 6
    ROOK_COLS = {"K": 10, "Q": 1}          # side (uppercased flag) -> rook col
    HOME_ROW = {WHITE: 1, BLACK: 10}
    BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}

    def initial_rights(self):
        return frozenset("KQkq")

    def moves(self, core, state):
        player = state.to_move
        enemy = 1 - player
        row = self.HOME_ROW[player]
        kfrom = (self.KING_COL, row)
        if state.board.get(kfrom) != (player, "K"):
            return
        if core.in_check(state.board, player):
            return
        for flag in self.BY_COLOR[player]:
            if flag not in state.castling:
                continue
            rcol = self.ROOK_COLS[flag.upper()]
            if state.board.get((rcol, row)) != (player, "R"):
                continue
            d = 1 if rcol > self.KING_COL else -1
            if any((c, row) in state.board for c in range(self.KING_COL + d, rcol, d)):
                continue
            for dist in range(2, abs(rcol - self.KING_COL)):
                kto = (self.KING_COL + d * dist, row)
                path = [(self.KING_COL + d * i, row) for i in range(1, dist + 1)]
                if any(core.attacked(state.board, c, r, enemy) for (c, r) in path):
                    continue
                yield kfrom, kto

    def rook_move(self, frm, to, player):
        row = self.HOME_ROW.get(player)
        if row is None or frm != (self.KING_COL, row) or to[1] != row:
            return None
        if abs(to[0] - self.KING_COL) < 2:
            return None
        d = 1 if to[0] > frm[0] else -1
        rcol = self.ROOK_COLS["K" if d > 0 else "Q"]
        return (rcol, row), (to[0] - d, row)

    def update_rights(self, rights, frm, to, board):
        rights = set(rights)
        pl, t = board[frm]
        if t == "K" and frm == (self.KING_COL, self.HOME_ROW[pl]):
            rights -= set(self.BY_COLOR[pl])
        for sq in (frm, to):
            for player, flags in self.BY_COLOR.items():
                row = self.HOME_ROW[player]
                if sq == (self.ROOK_COLS["Q"], row):
                    rights.discard(flags[1])
                if sq == (self.ROOK_COLS["K"], row):
                    rights.discard(flags[0])
        return frozenset(rights)


# Back-rank (rank 1) and second-rank piece files, cols 0..11 (None = empty).
RANK1 = ["M", "A", "V", "W", "C", None, None, "C", "W", "V", "A", "M"]
RANK2 = [None, "R", "S", "N", "B", "Q", "K", "B", "N", "S", "R", None]


class GrossChess(ChessLike):
    name = "Gross Chess"

    WIDTH = HEIGHT = 12
    PLY_CAP = 1000
    PIECES = {
        "R": (ORTHO, []),
        "B": (DIAG, []),
        "Q": (ALL8, []),
        "N": ([], KNIGHT),
        "K": ([], ALL8),
        "M": (ORTHO, KNIGHT),            # Marshall  = rook + knight
        "A": (DIAG, KNIGHT),             # Archbishop = bishop + knight
        "S": ([], WAZIR + DABBABA + ALFIL),   # Champion (Omega Chess)
        "W": ([], FERZ + CAMEL),              # Wizard   (Omega Chess)
        "C": ([], []),                   # Cannon -- handled in _pseudo/attacked
        "V": ([], []),                   # Vao    -- handled in _pseudo/attacked
    }
    HEAVY = ("P", "R", "Q", "M", "A", "S", "C")
    # Bot-eval material weights, ordered per the source's piece-value discussion:
    # minors "Cannon > Bishop > Knight > (Vao = Wizard)"; majors Q > M > A > R > S.
    PIECE_VALUES = {"P": 1.0, "W": 3.0, "V": 3.0, "N": 3.25, "B": 3.5, "C": 4.0,
                    "S": 4.5, "R": 5.5, "A": 7.5, "M": 8.5, "Q": 9.5, "K": 0.0}
    PAWN = GrossPawn(white_start=2, black_start=9)
    PROMOTION = GrossPromotion()
    CASTLING = GrossCastling()

    def setup_board(self) -> dict:
        b = {}
        for c in range(12):
            if RANK1[c]:
                b[(c, 0)] = (WHITE, RANK1[c])
                b[(c, 11)] = (BLACK, RANK1[c])
            if RANK2[c]:
                b[(c, 1)] = (WHITE, RANK2[c])
                b[(c, 10)] = (BLACK, RANK2[c])
            b[(c, 2)] = (WHITE, "P")
            b[(c, 9)] = (BLACK, "P")
        return b

    # ---- hoppers (Cannon / Vao) ---------------------------------------------
    def _pseudo(self, state):
        board, player = state.board, state.to_move
        ep_targets = state.ep[0] if state.ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "P":
                yield from self.PAWN.pseudo(self, board, c, r, player, ep_targets)
                continue
            if t in HOPPERS:
                for dc, dr in HOPPERS[t]:
                    cc, rr = c + dc, r + dr
                    while self.on(cc, rr) and (cc, rr) not in board:
                        yield (c, r), (cc, rr)          # rider move, no capture
                        cc += dc
                        rr += dr
                    if not self.on(cc, rr):
                        continue
                    cc += dc                            # hop over the screen
                    rr += dr
                    while self.on(cc, rr):
                        occ = board.get((cc, rr))
                        if occ is not None:
                            if occ[0] != player:
                                yield (c, r), (cc, rr)  # hop capture
                            break
                        cc += dc
                        rr += dr
                continue
            slides, leaps = self.PIECES[t]
            for dc, dr in leaps:
                tc, tr = c + dc, r + dr
                if self.on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                    yield (c, r), (tc, tr)
            for dc, dr in slides:
                cc, rr = c + dc, r + dr
                while self.on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is None:
                        yield (c, r), (cc, rr)
                    else:
                        if occ[0] != player:
                            yield (c, r), (cc, rr)
                        break
                    cc += dc
                    rr += dr

    def attacked(self, board, c, r, by) -> bool:
        if super().attacked(board, c, r, by):
            return True
        # A hopper attacks (c, r) if it sits beyond exactly one screen.
        for t, dirs in HOPPERS.items():
            for dc, dr in dirs:
                cc, rr = c + dc, r + dr
                while self.on(cc, rr) and (cc, rr) not in board:
                    cc += dc
                    rr += dr
                if not self.on(cc, rr):
                    continue
                cc += dc                                # past the screen
                rr += dr
                while self.on(cc, rr) and (cc, rr) not in board:
                    cc += dc
                    rr += dr
                if self.on(cc, rr) and board[(cc, rr)] == (by, t):
                    return True
        return False

    # ---- multi-target en passant --------------------------------------------
    def _apply_board(self, board, frm, to, ep):
        b = dict(board)
        pl, t = b.pop(frm)
        if t == "P" and ep is not None and to in ep[0] and to not in board:
            b.pop(ep[1], None)
        if t == "P" and (to[1] == self.HEIGHT - 1 and pl == WHITE
                         or to[1] == 0 and pl == BLACK):
            t = self.PROMOTION.safety_piece()
        b[to] = (pl, t)
        return b

    def apply_move(self, state, move, rng=None):
        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        capture = to in state.board
        ep_new = None
        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
        elif t == "P":
            if state.ep is not None and to in state.ep[0] and to not in state.board:
                b.pop(state.ep[1], None)
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)
        if t == "P" and promo:
            t = promo
        b[to] = (pl, t)
        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or state.board[frm][1] == "P"
        key = self._poskey(b, 1 - pl, castling, ep_new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=ep_new,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps)

    # ---- insufficient material ----------------------------------------------
    def _insufficient(self, board) -> bool:
        """Conservative: draw only bare kings or a lone minor (B/N/W/V/C --
        none can mate alone). Everything else plays on (50-move / repetition /
        ply-cap still guarantee termination); the source's pair-mating table
        (e.g. B+W mate only on opposite colours) is not short-circuited."""
        rest = [t for (_, t) in board.values() if t != "K"]
        if not rest:
            return True
        return len(rest) == 1 and rest[0] in ("B", "N", "W", "V", "C")

    # ---- (de)serialize (ep holds a tuple of targets) -------------------------
    def serialize(self, state) -> dict:
        ep = state.ep
        return {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "castling": "".join(sorted(state.castling)),
            "ep": (";".join(f"{c},{r}" for c, r in ep[0])
                   + "|" + f"{ep[1][0]},{ep[1][1]}") if ep else None,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
        }

    def deserialize(self, d: dict):
        ep = None
        if d.get("ep"):
            tpart, cpart = d["ep"].split("|")
            ep = (tuple(cell(s) for s in tpart.split(";")), cell(cpart))
        return CState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=ep,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
        )

    # ---- presentation --------------------------------------------------------
    def describe_move(self, state, move) -> str:
        raw, promo = (move.split("=") + [None])[:2]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        if t == "K" and self.CASTLING.rook_move(frm, to, pl) is not None:
            return "O-O" if to[0] > frm[0] else "O-O-O"
        capture = to in state.board or (
            t == "P" and state.ep is not None and to in state.ep[0])
        alg = lambda c: f"{_FILES[c[0]]}{c[1] + 1}"  # noqa: E731
        text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        return text + (f"={promo}" if promo else "")
