"""Tamerlane Chess (Timur's Great Chess / Shatranj Kamil, Persia c. 1400).

An 11x10 board plus two CITADEL squares (112 cells total), modelled like Omega
Chess as an embedding: main cells are (c, r) with 1 <= c <= 11 (files a..k) and
1 <= r <= 10; the citadels are (12, 2) (White's, protruding right of rank 2)
and (0, 9) (Black's, protruding left of rank 9). White = player 0 on ranks
1-3, advancing toward rank 10.

Pieces (all verified against chessvariants.com/historic.dir/tamerlane.html and
Wikipedia "Great chess" / Cazaux & Knowlton, *A World of Chess*):

* King ``K`` -- one step any direction. Once per game, when checked, it may
  EXCHANGE places with any friendly non-royal piece (move suffix ``=SWAP``).
* General (ferz) ``F`` -- one step diagonally.
* Vizier (wazir) ``V`` -- one step orthogonally.
* Giraffe (zurafa) ``G`` -- one step diagonally then a minimum of THREE squares
  straight, continuing outward along either orthogonal component; every passed
  square (including the diagonal one) must be empty. Not a jumper.
* Picket (talia) ``T`` -- bishop that must move at least two squares.
* Knight ``N``, Rook ``R`` -- as in modern chess.
* Elephant (alfil) ``E`` -- (2,2) jump. Camel ``C`` -- (3,1) leap.
* War engine (dabbaba) ``W`` -- (2,0) jump.
* Eleven PAWN TYPES, one per piece kind (lowercase letter of the piece they
  promote to: ``r n t g f v e c w`` plus ``k`` = pawn of kings and
  ``p``/``q``/``z`` = the pawn of pawns' three stages). Pawns step/capture like
  modern pawns but have NO double step and NO en passant. Promotion on the
  last rank is mandatory and always to the pawn's own piece type; the pawn of
  kings promotes to a Prince ``S`` (an extra royal), and the pawn of pawns
  follows the famous three-stage rule (see rules.md and _pop_placements).

Royal pieces are ``K`` (shah) > ``S`` (prince) > ``A`` (adventitious king).
While a player owns two or more royals there is NO check: royals may be left
or moved en prise and captured like ordinary pieces. Only when a single royal
remains do check/checkmate rules bind. Checkmate AND stalemate both lose for
the player to move. A player's acting king (his highest-ranking royal) may
enter the OPPONENT's empty citadel: the game is immediately drawn. Only a
(non-sole-royal) adventitious king may enter its OWN citadel, where it is
immune and blocks the opponent's draw; if it becomes the sole royal while
inside, its owner must immediately relocate it to any empty square.

No castling, no baring rule (Gollon). Threefold repetition, a 100-halfmove
no-progress rule and a hard ply cap are modern draw additions that guarantee
termination (documented in rules.md).
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, cell, ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK,
)

ALFIL = [(2, 2), (2, -2), (-2, 2), (-2, -2)]
DABBABA = [(2, 0), (-2, 0), (0, 2), (0, -2)]
CAMEL = [(1, 3), (3, 1), (-1, 3), (-3, 1), (1, -3), (3, -1), (-1, -3), (-3, -1)]

# Owner's citadel: the appendage on the owner's side of the board. The ENEMY
# acting king entering it draws; the owner's adventitious king may shelter there.
CITADEL = {WHITE: (12, 2), BLACK: (0, 9)}
CITADEL_CELLS = frozenset(CITADEL.values())

LAST = {WHITE: 10, BLACK: 1}          # promotion rank
FWD = {WHITE: 1, BLACK: -1}
POK_START = {WHITE: (6, 3), BLACK: (6, 8)}   # pawn-of-kings home = f3 / f8

ROYALS = ("K", "S", "A")              # shah > prince > adventitious king
PAWN_PROMO = {"r": "R", "n": "N", "t": "T", "g": "G", "f": "F",
              "v": "V", "e": "E", "c": "C", "w": "W", "k": "S"}
PAWN_LETTERS = frozenset("rntgfvecwkpqz")

LEAPS = {
    "N": KNIGHT, "E": ALFIL, "W": DABBABA, "C": CAMEL,
    "F": DIAG, "V": ORTHO, "K": ALL8, "S": ALL8, "A": ALL8,
}

LABELS = {"K": "K", "F": "F", "V": "V", "G": "G", "T": "T", "N": "N",
          "R": "R", "E": "E", "C": "C", "W": "W", "S": "Pr", "A": "AK",
          "r": "pR", "n": "pN", "t": "pT", "g": "pG", "f": "pF", "v": "pV",
          "e": "pE", "c": "pC", "w": "pW", "k": "pK",
          "p": "pP", "q": "p2", "z": "p3"}

NAMES = {"K": "King", "F": "General", "V": "Vizier", "G": "Giraffe",
         "T": "Picket", "N": "Knight", "R": "Rook", "E": "Elephant",
         "C": "Camel", "W": "War engine", "S": "Prince", "A": "Adv. king"}

_FILES = "abcdefghijk"                # c = 1..11

MAIN_CELLS = tuple((c, r) for r in range(1, 11) for c in range(1, 12))
_MAIN = frozenset(MAIN_CELLS)


def on_main(c, r) -> bool:
    return (c, r) in _MAIN


def _alg(sq) -> str:
    if sq == CITADEL[WHITE]:
        return "cw"
    if sq == CITADEL[BLACK]:
        return "cb"
    return f"{_FILES[sq[0] - 1]}{sq[1]}"


class TamerlaneChess(ChessLike):
    name = "Tamerlane Chess"

    WIDTH = 13                        # embedding (c 0..12) -- only 112 cells exist
    HEIGHT = 11                       # embedding (r 0..10)
    PLY_CAP = 1000
    PIECESET = None                   # uniform letter labels (custom pawn labels)
    PIECES = {T: ([], off) for T, off in LEAPS.items()}
    PIECES["R"] = (ORTHO, [])
    # G (giraffe) and T (picket) have bespoke generators below.
    PIECES["G"] = ([], [])
    PIECES["T"] = ([], [])
    PAWN = None
    PROMOTION = None

    PIECE_VALUES = {
        "K": 0.0, "S": 3.0, "A": 3.0, "R": 5.0, "G": 3.5, "N": 3.0,
        "T": 2.5, "C": 2.0, "E": 1.5, "W": 1.5, "F": 1.5, "V": 1.5,
        "r": 1.0, "n": 1.0, "t": 1.0, "g": 1.0, "f": 1.0, "v": 1.0,
        "e": 1.0, "c": 1.0, "w": 1.0, "k": 1.0, "p": 1.0, "q": 1.5, "z": 2.5,
    }

    # ---- setup ---------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        # White (CVP diagram, files a..k = c 1..11): rank 1 has elephants,
        # camels and war engines with gaps; rank 2 the heavy row; rank 3 pawns.
        for c, t in ((1, "E"), (3, "C"), (5, "W"), (7, "W"), (9, "C"), (11, "E")):
            b[(c, 1)] = (WHITE, t)
        for c, t in enumerate("RNTGFKVGTNR", start=1):
            b[(c, 2)] = (WHITE, t)
        for c, t in enumerate("pwcefkvgtnr", start=1):
            b[(c, 3)] = (WHITE, t)
        # Black mirrors by 180-degree rotation (c,r) -> (12-c, 11-r); kings face
        # each other on the f-file, each player's vizier on his own right.
        for c, t in ((1, "E"), (3, "C"), (5, "W"), (7, "W"), (9, "C"), (11, "E")):
            b[(c, 10)] = (BLACK, t)
        for c, t in enumerate("RNTGVKFGTNR", start=1):
            b[(c, 9)] = (BLACK, t)
        for c, t in enumerate("rntgvkfecwp", start=1):
            b[(c, 8)] = (BLACK, t)
        return b

    def initial_state(self, options=None, rng=None):
        st = CState(board=self.setup_board(), to_move=WHITE,
                    castling=frozenset("Ss"))     # per-player king-swap right
        st.reps = {self._poskey_state(st): 1}
        return st

    # ---- helpers -------------------------------------------------------------
    def _royals(self, board, player):
        """The player's royal pieces, ordered shah > prince > adv. king."""
        found = [(sq, t) for sq, (pl, t) in board.items()
                 if pl == player and t in ROYALS]
        found.sort(key=lambda x: ROYALS.index(x[1]))
        return found

    def _immune(self, board, sq) -> bool:
        """A pawn of pawns frozen on its last rank cannot be captured or
        displaced; an adventitious king in its own citadel likewise (the latter
        is emergent -- no enemy piece may enter that citadel anyway)."""
        occ = board.get(sq)
        return (occ is not None and occ[1] == "q" and sq[1] == LAST[occ[0]])

    def _attack_squares(self, board, c, r):
        """Squares ATTACKED by the piece at (c, r) (capture squares; a slider
        ray includes its first blocker). Citadel cells are never attacked."""
        pl, t = board[(c, r)]
        if t in PAWN_LETTERS:
            if t == "q" and r == LAST[pl]:
                return                                # frozen: attacks nothing
            f = FWD[pl]
            for dc in (-1, 1):
                if on_main(c + dc, r + f):
                    yield (c + dc, r + f)
            return
        if t == "R":
            for dc, dr in ORTHO:
                cc, rr = c + dc, r + dr
                while on_main(cc, rr):
                    yield (cc, rr)
                    if (cc, rr) in board:
                        break
                    cc += dc
                    rr += dr
            return
        if t == "T":                                  # picket: bishop, min 2
            for dc, dr in DIAG:
                if not on_main(c + dc, r + dr) or (c + dc, r + dr) in board:
                    continue                          # must pass the first square
                cc, rr = c + 2 * dc, r + 2 * dr
                while on_main(cc, rr):
                    yield (cc, rr)
                    if (cc, rr) in board:
                        break
                    cc += dc
                    rr += dr
            return
        if t == "G":                                  # giraffe: 1 diag + >=3 straight
            for dc, dr in DIAG:
                d1 = (c + dc, r + dr)
                if not on_main(*d1) or d1 in board:
                    continue
                for sc, sr in ((dc, 0), (0, dr)):     # both outward continuations
                    cc, rr = d1
                    blocked = False
                    for i in range(1, 12):
                        cc, rr = cc + sc, rr + sr
                        if not on_main(cc, rr) or blocked:
                            break
                        if i < 3:
                            if (cc, rr) in board:
                                break                 # passed square must be empty
                        else:
                            yield (cc, rr)
                            if (cc, rr) in board:
                                blocked = True
            return
        for dc, dr in LEAPS[t]:
            if on_main(c + dc, r + dr):
                yield (c + dc, r + dr)

    # Reverse-attack table for the leaper pieces (every leap set is symmetric,
    # so "X at sq+off attacks sq" iff off is in X's set).
    _REV_LEAP = {}
    for _t, _offs in LEAPS.items():
        for _o in _offs:
            _REV_LEAP.setdefault(_o, set()).add(_t)
    _REV_LEAP = {k: frozenset(v) for k, v in _REV_LEAP.items()}
    del _t, _offs, _o

    def attacked_sq(self, board, sq, by) -> bool:
        """Targeted reverse test: is the (main-board) square attacked by ``by``?"""
        c, r = sq
        for (dc, dr), letters in self._REV_LEAP.items():
            occ = board.get((c + dc, r + dr))
            if occ is not None and occ[0] == by and occ[1] in letters:
                return True
        pr = r - FWD[by]                              # pawns (a frozen PoP's attack
        for dc in (-1, 1):                            # rank is off-board, so it
            occ = board.get((c + dc, pr))             # never appears here)
            if occ is not None and occ[0] == by and occ[1] in PAWN_LETTERS:
                return True
        for dc, dr in ORTHO:                          # rook rays
            cc, rr = c + dc, r + dr
            while on_main(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] == by and occ[1] == "R":
                        return True
                    break
                cc += dc
                rr += dr
        for dc, dr in DIAG:                           # picket rays (min length 2)
            cc, rr, dist = c + dc, r + dr, 1
            while on_main(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if dist >= 2 and occ[0] == by and occ[1] == "T":
                        return True
                    break
                cc, rr, dist = cc + dc, rr + dr, dist + 1
        # Giraffe: reverse of (1 diag + m>=3 straight). Walk each ortho dir w
        # from sq; after m empty squares (m>=3) the last one is the giraffe's
        # diagonal landing square d1; the giraffe sits one diagonal step beyond,
        # at d1 + w + p for either perpendicular unit p.
        for w in ORTHO:
            cc, rr, m = c, r, 0
            while True:
                cc, rr, m = cc + w[0], rr + w[1], m + 1
                if not on_main(cc, rr) or (cc, rr) in board:
                    break
                if m >= 3:
                    for p in ((-w[1], w[0]), (w[1], -w[0])):
                        occ = board.get((cc + w[0] + p[0], rr + w[1] + p[1]))
                        if occ is not None and occ[0] == by and occ[1] == "G":
                            return True
        return False

    def in_check(self, board, player) -> bool:
        """Check exists only while the player owns EXACTLY ONE royal piece."""
        royals = self._royals(board, player)
        return len(royals) == 1 and self.attacked_sq(board, royals[0][0], 1 - player)

    # ---- pseudo move generation ----------------------------------------------
    def _piece_targets(self, board, c, r):
        """Movement targets (main board) for the piece at (c, r). Citadel
        entries and pawn-of-pawns placements are added elsewhere."""
        pl, t = board[(c, r)]
        if t in PAWN_LETTERS:
            if t == "q" and r == LAST[pl]:
                return                                # frozen: placements only
            f = FWD[pl]
            nt = (c, r + f)
            if on_main(*nt) and nt not in board:
                if not (t == "q" and nt[1] == LAST[pl] and POK_START[pl] in board):
                    yield nt                          # (2nd PoP promotion needs f3/f8 empty)
            for dc in (-1, 1):
                dt = (c + dc, r + f)
                occ = board.get(dt)
                if (on_main(*dt) and occ is not None and occ[0] != pl
                        and not self._immune(board, dt)):
                    if not (t == "q" and dt[1] == LAST[pl] and POK_START[pl] in board):
                        yield dt
            return
        for sq in self._attack_squares(board, c, r):
            occ = board.get(sq)
            if occ is None or (occ[0] != pl and not self._immune(board, sq)):
                yield sq

    def _citadel_entries(self, board, player):
        """(frm, to) royal steps into a citadel. The acting king (highest
        royal) may enter the opponent's EMPTY citadel (-> draw); an adventitious
        king that is NOT the sole royal may enter its own empty citadel."""
        royals = self._royals(board, player)
        if not royals:
            return
        top_sq, _top_t = royals[0]
        enemy_cit = CITADEL[1 - player]
        if enemy_cit not in board and max(abs(top_sq[0] - enemy_cit[0]),
                                          abs(top_sq[1] - enemy_cit[1])) == 1:
            yield top_sq, enemy_cit
        own_cit = CITADEL[player]
        if own_cit not in board and len(royals) >= 2:
            for sq, t in royals:
                if t == "A" and max(abs(sq[0] - own_cit[0]),
                                    abs(sq[1] - own_cit[1])) == 1:
                    yield sq, own_cit

    def _pop_placements(self, state, frm):
        """Placement targets for a frozen pawn of pawns at ``frm``: any main
        square (not the owner's last rank, not holding a royal or an immune
        piece) where the placed pawn forks two enemy pieces or attacks one
        trapped enemy piece. Trapped (static 1-ply test, see rules.md): no
        enemy piece attacks the placement square, and the attacked piece has
        no pseudo-legal move to a square the placed pawn does not attack."""
        board = state.board
        pl = board[frm][0]
        enemy = 1 - pl
        f = FWD[pl]
        out = []
        for t in MAIN_CELLS:
            if t == frm or t[1] == LAST[pl]:
                continue
            occ = board.get(t)
            if occ is not None and (occ[1] in ROYALS or self._immune(board, t)):
                continue
            atk = [(t[0] + dc, t[1] + f) for dc in (-1, 1)
                   if on_main(t[0] + dc, t[1] + f)]
            b2 = dict(board)
            del b2[frm]
            b2.pop(t, None)
            b2[t] = (pl, "q")
            victims = [a for a in atk
                       if (v := b2.get(a)) is not None and v[0] == enemy
                       and not self._immune(b2, a)]
            if len(victims) >= 2:
                out.append(t)
                continue
            if len(victims) == 1 and b2[victims[0]][1] not in ROYALS:
                if self.attacked_sq(b2, t, enemy):
                    continue                          # the pawn can be captured
                vx = victims[0]
                if not any(sq not in atk
                           for sq in self._piece_targets(b2, vx[0], vx[1])):
                    out.append(t)                     # no escape square
        return out

    def _swap_moves(self, state):
        """Once-per-game royal exchange: when the (sole) royal is checked, it
        may swap squares with any friendly non-royal, non-frozen piece, if the
        swap resolves the check. A pawn may not be swapped onto its last rank."""
        pl = state.to_move
        flag = "S" if pl == WHITE else "s"
        if flag not in state.castling:
            return []
        board = state.board
        royals = self._royals(board, pl)
        if len(royals) != 1 or not self.attacked_sq(board, royals[0][0], 1 - pl):
            return []
        ksq, kt = royals[0]
        out = []
        for sq, (p2, t) in board.items():
            if p2 != pl or t in ROYALS or sq in CITADEL_CELLS:
                continue
            if self._immune(board, sq):
                continue
            if t in PAWN_LETTERS and ksq[1] == LAST[pl]:
                continue                              # no pawn onto its last rank
            b2 = dict(board)
            b2[ksq], b2[sq] = (pl, t), (pl, kt)
            if not self.attacked_sq(b2, sq, 1 - pl):
                out.append(f"{ksq[0]},{ksq[1]}>{sq[0]},{sq[1]}=SWAP")
        return out

    # ---- board transition (shared by legality filter and apply) --------------
    def _move_board(self, board, frm, to):
        """Board after moving frm->to (handles captures, all promotions and the
        pawn-of-pawns teleport). Returns (board, captured_or_None)."""
        pl, t = board[frm]
        b = dict(board)
        del b[frm]
        captured = b.pop(to, None)
        if t in PAWN_LETTERS:
            if t == "q" and frm[1] == LAST[pl]:
                b[to] = (pl, "q")                     # placement off the last rank
            elif to[1] == LAST[pl]:
                if t == "p":
                    b[to] = (pl, "q")                 # 1st arrival: freeze, immune
                elif t == "q":
                    b[POK_START[pl]] = (pl, "z")      # 2nd arrival: teleport to f3/f8
                elif t == "z":
                    b[to] = (pl, "A")                 # 3rd arrival: adventitious king
                else:
                    b[to] = (pl, PAWN_PROMO[t])       # own piece (pawn of kings -> S)
            else:
                b[to] = (pl, t)
        else:
            b[to] = (pl, t)
        return b, captured

    # ---- legal moves ----------------------------------------------------------
    def _legal_pairs(self, state):
        """All legal (frm, to) pairs (excluding =SWAP moves)."""
        board, pl = state.board, state.to_move
        royals = self._royals(board, pl)
        if not royals:
            return []
        # Bodlaender's rule: a sole-royal adventitious king sitting in its own
        # citadel must immediately be placed on any empty main square.
        if len(royals) == 1 and royals[0][1] == "A" and royals[0][0] == CITADEL[pl]:
            frm = royals[0][0]
            out = []
            for sq in MAIN_CELLS:
                if sq in board:
                    continue
                b2 = dict(board)
                del b2[frm]
                b2[sq] = (pl, "A")
                if not self.attacked_sq(b2, sq, 1 - pl):
                    out.append((frm, sq))
            return out
        pairs = []
        for (c, r), (p2, t) in list(board.items()):
            if p2 != pl:
                continue
            if t == "q" and r == LAST[pl]:
                pairs.extend(((c, r), to) for to in self._pop_placements(state, (c, r)))
            else:
                pairs.extend(((c, r), to) for to in self._piece_targets(board, c, r))
        pairs.extend(self._citadel_entries(board, pl))
        if len(royals) >= 2:
            return pairs                              # no check with spare royals
        out = []
        for frm, to in pairs:
            if to in CITADEL_CELLS:
                out.append((frm, to))                 # game ends on entry
                continue
            b2, _cap = self._move_board(state.board, frm, to)
            if not self.in_check(b2, pl):
                out.append((frm, to))
        return out

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        out = [f"{f[0]},{f[1]}>{t[0]},{t[1]}" for f, t in self._legal_pairs(state)]
        out.extend(self._swap_moves(state))
        return out

    # ---- apply -----------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        castling = state.castling
        if move.endswith("=SWAP"):
            fs, ts = move[:-5].split(">")
            ksq, sq = cell(fs), cell(ts)
            b = dict(state.board)
            b[ksq], b[sq] = b[sq], b[ksq]
            castling = castling - {"S" if pl == WHITE else "s"}
            reset = False
        else:
            frm, to = (cell(x) for x in move.split(">"))
            b, captured = self._move_board(state.board, frm, to)
            reset = captured is not None or state.board[frm][1] in PAWN_LETTERS
        key = self._poskey(b, 1 - pl, castling, None)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        return CState(board=b, to_move=1 - pl, castling=castling, ep=None,
                      halfmove=0 if reset else state.halfmove + 1,
                      ply=state.ply + 1, reps=reps)

    # ---- terminal --------------------------------------------------------------
    def _citadel_draw(self, board) -> bool:
        w = board.get(CITADEL[WHITE])                 # White's citadel: a BLACK
        if w is not None and w[0] == BLACK:           # royal here drew the game
            return True
        bl = board.get(CITADEL[BLACK])
        return bl is not None and bl[0] == WHITE

    def _draw(self, state) -> bool:
        if self._citadel_draw(state.board):
            return True
        if len(state.board) == 2:
            return True   # bare royal vs bare royal: dead (a LONE extra royal
        #     is NOT dead -- K+Prince can still win by forced stalemate)
        return (state.halfmove >= 100 or state.ply >= self.PLY_CAP
                or state.reps.get(self._poskey_state(state), 0) >= 3)

    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        if not self._royals(state.board, WHITE) or not self._royals(state.board, BLACK):
            return True                               # guard; unreachable in legal play
        return not self.legal_moves(state)

    def returns(self, state) -> list:
        if self._citadel_draw(state.board):
            return [0.0, 0.0]
        for pl in (WHITE, BLACK):
            if not self._royals(state.board, pl):
                return [-1.0, 1.0] if pl == WHITE else [1.0, -1.0]
        if self._draw(state):
            return [0.0, 0.0]
        # No legal moves: checkmate AND stalemate both lose in Tamerlane chess.
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    # ---- presentation ------------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if move.endswith("=SWAP"):
            fs, ts = move[:-5].split(">")
            return f"K{_alg(cell(fs))}<->{_alg(cell(ts))} (royal exchange)"
        frm, to = (cell(x) for x in move.split(">"))
        pl, t = state.board.get(frm, (None, "?"))
        lbl = LABELS.get(t, t)
        if t == "q" and frm[1] == LAST.get(pl, -1):
            return f"{lbl}{_alg(frm)}@{_alg(to)} (placement)"
        capture = to in state.board
        text = f"{lbl}{_alg(frm)}{'x' if capture else '-'}{_alg(to)}"
        if to in CITADEL_CELLS:
            text += " (citadel)"
        return text

    def render(self, state, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": pl, "label": LABELS.get(t, t)}
                  for (c, r), (pl, t) in state.board.items()]
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            if ret == [0.0, 0.0]:
                caption = ("Draw — king reached the citadel"
                           if self._citadel_draw(state.board) else "Draw")
            else:
                winner = 0 if ret[0] > 0 else 1
                how = ("checkmate" if self.in_check(state.board, 1 - winner)
                       else "stalemate")
                caption = f"{names[winner]} wins ({how})"
        elif self.in_check(state.board, state.to_move):
            caption = f"{names[state.to_move]} to move (check)"
        else:
            caption = f"{names[state.to_move]} to move"
        cells, tints = [], {}
        for (c, r) in MAIN_CELLS + tuple(CITADEL.values()):
            y = self.HEIGHT - 1 - r                   # White (r=1) at the bottom
            cells.append({"id": f"{c},{r}",
                          "points": [[c, y], [c + 1, y], [c + 1, y + 1], [c, y + 1]]})
            if (c, r) in CITADEL_CELLS:
                tints[f"{c},{r}"] = "#3a2e45"         # citadels (accent)
            elif (c + r) % 2 == 1:
                tints[f"{c},{r}"] = "#332e27"
            else:
                tints[f"{c},{r}"] = "#2a2620"
        return {
            "board": {"type": "polygons", "cells": cells, "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
