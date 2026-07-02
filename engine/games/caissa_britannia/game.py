"""Caissa Britannia (Fergus Duniho, 2003), 10x10, built on the shared core.

British-themed large variant whose ROYAL piece is the Queen. Alongside Rooks,
Anglican Bishops and Pawns it adds three heraldic pieces (Lion for England,
Unicorn for Scotland, Dragon for Wales) and replaces the King with a
Prince Consort:

* **Queen "Q"** (royal) -- slides as a chess Queen but may not pass over any
  square it would be illegal for it to move to: every square it crosses must
  be free of enemy attack (with the enemy Queen counted as a plain Queen
  slider, so Queens may never face each other across an open line and may
  never pass over squares the other Queen reaches). Its own CHECKING power is
  a plain Queen slide (the movement restriction does not impair its attack).
* **Prince Consort "K"** (not royal) -- slides like a Queen without capturing,
  or captures by stepping one square in any direction (Betza mQK).
* **Lion "L"** -- T. R. Dawson's Leo: moves as a Queen without capturing;
  captures like the Chinese-Chess Cannon/Vao along Queen lines by leaping
  exactly one screen (of either colour) and taking the first piece beyond it.
* **Unicorn "U"** -- Bishop + Nightrider (repeated knight leaps in one
  direction over empty landing squares).
* **Dragon "D"** -- Alfilrider + Dabbabarider: any number of consecutive
  two-square leaps in one radial direction; every landing square except the
  last must be empty (the jumped-over odd squares are ignored). Colorbound to
  one quarter of the board.
* **Bishop "B"** -- Anglican: slides diagonally, or steps one square
  orthogonally WITHOUT capturing (so it can change square colour).
* **Rook "R"** / **Knight "N"** / **Pawn "P"** -- as in chess (no castling;
  the Knight appears only by promotion).

Pawns start on the third rank, keep the double step and en passant, and MUST
promote on the last rank -- to a Knight, or to any piece type the owner has
lost (a captured piece is "liberated"). Checkmate of the enemy Queen wins;
stalemate is a draw. There is no castling. White = player 0.

Source: https://www.chessvariants.com/large.dir/british.html
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, PromotionRules, StandardPawn, NoCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

RANK1 = ["D", "R", "U", "B", "Q", "K", "B", "U", "R", "D"]   # files a..j


class CaissaPromotion(PromotionRules):
    """Mandatory last-rank promotion to a Knight or to any *captured* piece:
    a type is available iff the owner currently has fewer of it on the board
    than at the start. (The royal Queen is included for fidelity to the
    published promotion list, but is unreachable in legal play.)"""

    INITIAL = {"Q": 1, "R": 2, "B": 2, "U": 2, "L": 2, "D": 2}

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        last = (to[1] == core.HEIGHT - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK)
        if not last:
            return [None]
        cnt = {}
        for (pl2, t) in state.board.values():
            if pl2 == pl:
                cnt[t] = cnt.get(t, 0) + 1
        return ["N"] + [T for T in ("Q", "R", "B", "U", "L", "D")
                        if cnt.get(T, 0) < self.INITIAL[T]]

    def safety_piece(self):
        return "N"    # always a legal promotion; never a second royal Queen


class CaissaBritannia(ChessLike):
    name = "Caissa Britannia"

    WIDTH = HEIGHT = 10
    PLY_CAP = 800
    # Move generation and attack detection are fully custom (screen captures,
    # riders, move/capture asymmetry, the royal-Queen path rule), so the
    # declarative table stays empty and _pseudo/attacked are overridden.
    PIECES: dict = {}
    # Any piece besides the (uncapturable) royal Queens is mating material:
    # a Queen + almost anything can mate a cornered Queen. Only bare Q vs Q
    # is a dead draw.
    HEAVY = ("P", "R", "N", "B", "L", "U", "D", "K")
    # Rough values (source ranks U/R/K as majors, L/D/B/N as strong minors).
    PIECE_VALUES = {"P": 1.0, "N": 3.0, "D": 3.0, "B": 3.5, "L": 3.5,
                    "R": 5.0, "K": 5.5, "U": 7.0, "Q": 0.0}
    PAWN = StandardPawn(white_start=2, black_start=7)
    PROMOTION = CaissaPromotion()
    CASTLING = NoCastling()

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for i, t in enumerate(RANK1):
            b[(i, 0)] = (WHITE, t)
            b[(i, 9)] = (BLACK, t)
        for c in (1, 8):
            b[(c, 1)] = (WHITE, "L")
            b[(c, 8)] = (BLACK, "L")
        for c in range(10):
            b[(c, 2)] = (WHITE, "P")
            b[(c, 7)] = (BLACK, "P")
        return b

    # ---- royal piece: the Queen ---------------------------------------------
    def _king(self, board, player):
        for (c, r), (pl, t) in board.items():
            if pl == player and t == "Q":
                return c, r
        return None

    # ---- attack detection ----------------------------------------------------
    # Is (c, r) attacked by side ``by``? The royal Queen ATTACKS as a plain
    # Queen slider ("this restriction on the Queen's movement does not impair
    # the Queen's ability to check"); the Bishop's wazir step and the Prince
    # Consort's / Lion's plain slides are non-capturing, so they do not attack.
    def attacked(self, board, c, r, by) -> bool:
        if self.PAWN.attacks(self, board, c, r, by):
            return True
        for dc, dr in KNIGHT:
            if board.get((c + dc, r + dr)) == (by, "N"):
                return True
        for dc, dr in ALL8:                       # Prince Consort captures as a King
            if board.get((c + dc, r + dr)) == (by, "K"):
                return True
        for dirs, types in ((ORTHO, ("R", "Q")), (DIAG, ("B", "Q", "U"))):
            for dc, dr in dirs:
                cc, rr = c + dc, r + dr
                while self.on(cc, rr):
                    occ = board.get((cc, rr))
                    if occ is not None:
                        if occ[0] == by and occ[1] in types:
                            return True
                        break
                    cc += dc
                    rr += dr
        for dc, dr in KNIGHT:                     # Unicorn's nightrider component
            cc, rr = c + dc, r + dr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ == (by, "U"):
                        return True
                    break
                cc += dc
                rr += dr
        for dc, dr in ALL8:                       # Dragon: two-square rider
            cc, rr = c + 2 * dc, r + 2 * dr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ == (by, "D"):
                        return True
                    break
                cc += 2 * dc
                rr += 2 * dr
        for dc, dr in ALL8:                       # Lion: one screen, then the target
            cc, rr = c + dc, r + dr
            while self.on(cc, rr) and (cc, rr) not in board:
                cc += dc
                rr += dr
            if not self.on(cc, rr):
                continue
            cc += dc
            rr += dr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ == (by, "L"):
                        return True
                    break
                cc += dc
                rr += dr
        return False

    # ---- move generation ------------------------------------------------------
    def _rider(self, board, c, r, player, step):
        """Repeated fixed leaps in one direction; every landing square except
        the last must be empty (Nightrider / Dragon movement)."""
        dc, dr = step
        cc, rr = c + dc, r + dr
        while self.on(cc, rr):
            occ = board.get((cc, rr))
            if occ is None:
                yield (c, r), (cc, rr)
            else:
                if occ[0] != player:
                    yield (c, r), (cc, rr)
                return
            cc += dc
            rr += dr

    def _queen_moves(self, board, c, r, player):
        """Royal-Queen slides: may not pass over any square that would itself
        be an illegal destination (i.e. where the Queen would stand attacked,
        origin square vacated)."""
        enemy = 1 - player
        b = dict(board)
        del b[(c, r)]
        for dc, dr in ALL8:
            cc, rr = c + dc, r + dr
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None and occ[0] == player:
                    break
                b[(cc, rr)] = (player, "Q")
                safe = not self.attacked(b, cc, rr, enemy)
                if occ is None:
                    del b[(cc, rr)]
                else:
                    b[(cc, rr)] = occ
                if safe:
                    yield (c, r), (cc, rr)
                if occ is not None or not safe:
                    break
                cc += dc
                rr += dr

    def _pseudo(self, state):
        board, player = state.board, state.to_move
        ep_target = state.ep[0] if state.ep else None
        for (c, r), (pl, t) in list(board.items()):
            if pl != player:
                continue
            if t == "P":
                yield from self.PAWN.pseudo(self, board, c, r, player, ep_target)
            elif t == "N":
                for dc, dr in KNIGHT:
                    tc, tr = c + dc, r + dr
                    if self.on(tc, tr) and (board.get((tc, tr)) or (None,))[0] != player:
                        yield (c, r), (tc, tr)
            elif t == "R":
                for d in ORTHO:
                    yield from self._slide(board, c, r, player, d)
            elif t == "B":
                for d in DIAG:
                    yield from self._slide(board, c, r, player, d)
                for dc, dr in ORTHO:              # wazir step, non-capturing
                    tc, tr = c + dc, r + dr
                    if self.on(tc, tr) and (tc, tr) not in board:
                        yield (c, r), (tc, tr)
            elif t == "K":                        # Prince Consort: mQK
                for dc, dr in ALL8:
                    tc, tr = c + dc, r + dr
                    if not self.on(tc, tr):
                        continue
                    occ = board.get((tc, tr))
                    if occ is not None:           # one-step capture only
                        if occ[0] != player:
                            yield (c, r), (tc, tr)
                        continue
                    while self.on(tc, tr) and (tc, tr) not in board:
                        yield (c, r), (tc, tr)    # slide over empties, no capture
                        tc += dc
                        tr += dr
            elif t == "U":
                for d in DIAG:
                    yield from self._slide(board, c, r, player, d)
                for o in KNIGHT:
                    yield from self._rider(board, c, r, player, o)
            elif t == "D":
                for dc, dr in ALL8:
                    yield from self._rider(board, c, r, player, (2 * dc, 2 * dr))
            elif t == "L":                        # Leo: mQ + screen capture
                for dc, dr in ALL8:
                    cc, rr = c + dc, r + dr
                    while self.on(cc, rr) and (cc, rr) not in board:
                        yield (c, r), (cc, rr)
                        cc += dc
                        rr += dr
                    if not self.on(cc, rr):
                        continue
                    cc += dc                      # leap the screen
                    rr += dr
                    while self.on(cc, rr) and (cc, rr) not in board:
                        cc += dc
                        rr += dr
                    if self.on(cc, rr) and board[(cc, rr)][0] != player:
                        yield (c, r), (cc, rr)
            elif t == "Q":
                yield from self._queen_moves(board, c, r, player)

    def _slide(self, board, c, r, player, d):
        dc, dr = d
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
