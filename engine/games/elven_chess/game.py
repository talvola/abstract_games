"""Elven Chess (H. G. Muller, 2014) -- 10x10 orthodox-Chess / Chu-Shogi hybrid.

Primary source: https://www.chessvariants.com/rules/elven-chess (Muller's own
published rules page, incl. his Interactive Diagram definition). Secondary:
his play-test applet http://hgm.nubati.net/variants/elven/ (differs in two
places -- documented in rules.md; the CVP page is followed).

Next to the FIDE army it adds four pieces that all have the King's move:

* **Goblin  (G)** -- Rook + King step  (the Shogi Dragon King, Betza RF);
* **Elf     (E)** -- Bishop + King step (the Shogi Dragon Horse, Betza BW);
* **Dwarf   (D)** -- non-royal Commoner (King move only, Betza K);
* **Warlock (W)** -- the Chu-Shogi **Lion** (Betza KNADmabKcaKcabK): it moves
  as a King but may (optionally) do so **twice per turn**, and may use its
  non-last step as a *hop* over an occupied square. Concretely it can:
  leap directly to any square of the surrounding 5x5 area; capture an adjacent
  piece and move on (capturing again, moving to an empty square, or returning
  to its start square = *igui*); or step to an adjacent empty square and back,
  effectively passing the turn.

Anti-Warlock-trading rules (the game's signature, from the CVP page):

1. **Royal-for-one-turn:** a Warlock may capture the enemy Warlock only if the
   square it *ends up on* would be safe for a King -- i.e. not attacked by any
   enemy piece, pinned pieces included. (Since nothing then attacks it, it
   provably cannot be recaptured on the very next move, so no persistent state
   is needed for this rule.)
2. **Iron-for-one-turn:** when a *non*-Warlock captures a Warlock, the other
   side's Warlock becomes **iron** for one turn: the opponent's immediate reply
   may not capture it at all (not even as the first leg of a Lion double move).
   This *is* persistent state -- ``WState.iron`` holds the protected square for
   exactly the one turn it applies to.

Pawns: orthodox step/double-step/en-passant from the 3rd/8th rank; **mandatory
promotion on entering the last three ranks** (in practice the 8th/3rd rank),
to Q, R, B or N only (never to the fairy pieces). Castling: orthodox
conditions, but the King slides **three** squares toward the Rook (usual on
10-wide boards). Checkmate wins; stalemate and the usual repetition/50-move/
bare-minors rules draw.

Move encoding (all platform-clickable cell paths):

* normal moves / distance-2 Warlock leaps: ``"fc,fr>tc,tr"``;
* a Warlock move to an **adjacent** square: ``"f>m>m"`` (click the destination
  twice -- required so single steps do not shadow the double-move
  continuations that share the same first click);
* Warlock double move: ``"f>m>t"`` with an enemy on ``m`` (``t`` may be ``f``:
  capture-and-return igui);
* Warlock turn pass: ``"f>m>f"`` with ``m`` an adjacent empty square.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agp.chesslike import (
    ChessLike, CState, StandardPawn, PromotionRules, StandardCastling, cell,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, _FILES,
)

# The 24 squares of the 5x5 box around a cell: the Warlock's direct-leap range
# (K + N + A + D in Betza terms). Used both for its pseudo-moves and -- via the
# shared attack map -- for check detection (a Lion checks from distance <= 2).
BOX2 = [(dc, dr) for dc in range(-2, 3) for dr in range(-2, 3) if (dc, dr) != (0, 0)]

RANK1 = {0: "R", 9: "R", 5: "K"}                                   # a1 j1 f1
RANK2 = ["D", "N", "B", "E", "W", "Q", "G", "B", "N", "D"]          # a2..j2


@dataclass
class WState(CState):
    """Chess state + the iron-Warlock square (protected for this one turn)."""
    iron: Optional[tuple] = None


class ZonePromotion(PromotionRules):
    """Mandatory promotion (to Q/N/R/B) on any pawn move that ends in the last
    three ranks. Because promotion is compulsory on *entering* the zone, a pawn
    can in practice only ever promote on the zone's first rank (the 8th/3rd)."""

    TARGETS = ("Q", "N", "R", "B")

    def options(self, core, state, frm, to):
        pl = state.board[frm][0]
        in_zone = to[1] >= core.HEIGHT - 3 if pl == WHITE else to[1] <= 2
        return list(self.TARGETS) if in_zone else [None]


class ElvenCastling(StandardCastling):
    """10-wide castling: King f1 (White) / e10 (Black) slides THREE squares
    toward either Rook (a/j files); orthodox virginity / clear-path /
    not-through-check conditions. 'K'/'k' = toward the j-file rook."""

    CASTLES = {
        "K": ((5, 0), (8, 0), (9, 0), (7, 0),
              [(6, 0), (7, 0), (8, 0)], [(5, 0), (6, 0), (7, 0), (8, 0)]),
        "Q": ((5, 0), (2, 0), (0, 0), (3, 0),
              [(1, 0), (2, 0), (3, 0), (4, 0)], [(5, 0), (4, 0), (3, 0), (2, 0)]),
        "k": ((4, 9), (7, 9), (9, 9), (6, 9),
              [(5, 9), (6, 9), (7, 9), (8, 9)], [(4, 9), (5, 9), (6, 9), (7, 9)]),
        "q": ((4, 9), (1, 9), (0, 9), (2, 9),
              [(1, 9), (2, 9), (3, 9)], [(4, 9), (3, 9), (2, 9), (1, 9)]),
    }
    ROOK_HOME = {(9, 0): "K", (0, 0): "Q", (9, 9): "k", (0, 9): "q"}
    KING_HOME = {(5, 0): WHITE, (4, 9): BLACK}

    def rook_move(self, frm, to, player):
        if abs(to[0] - frm[0]) != 3:
            return None
        flag = self.BY_COLOR[player][0] if to[0] > frm[0] else self.BY_COLOR[player][1]
        _, _, rfrom, rto, _, _ = self.CASTLES[flag]
        return rfrom, rto


def _alg(c):
    return f"{_FILES[c[0]]}{c[1] + 1}"


class ElvenChess(ChessLike):
    uid = "elven_chess"
    name = "Elven Chess"

    WIDTH = HEIGHT = 10
    PLY_CAP = 800
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []), "N": ([], KNIGHT),
        "K": ([], ALL8),
        "G": (ORTHO, DIAG),   # Goblin: Rook + King step (Dragon King)
        "E": (DIAG, ORTHO),   # Elf: Bishop + King step (Dragon Horse)
        "D": ([], ALL8),      # Dwarf: Commoner
        "W": ([], BOX2),      # Warlock direct leaps (double moves are custom)
    }
    HEAVY = ("P", "R", "Q", "G", "E", "W", "D")
    PIECE_VALUES = {**ChessLike.PIECE_VALUES,
                    "G": 7.0, "E": 6.5, "D": 3.0, "W": 14.0}
    PAWN = StandardPawn(white_start=2, black_start=7)
    PROMOTION = ZonePromotion()
    CASTLING = ElvenCastling()

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c, t in RANK1.items():
            b[(c, 0)] = (WHITE, t)
            b[(9 - c, 9)] = (BLACK, t)          # 180-degree rotational symmetry
        for c, t in enumerate(RANK2):
            b[(c, 1)] = (WHITE, t)
            b[(9 - c, 8)] = (BLACK, t)
        for c in range(10):
            b[(c, 2)] = (WHITE, "P")
            b[(c, 7)] = (BLACK, "P")
        return b

    def initial_state(self, options=None, rng=None):
        st = WState(board=self.setup_board(), to_move=WHITE,
                    castling=self.CASTLING.initial_rights(), ep=None, iron=None)
        st.reps = {self._poskey_state(st): 1}
        return st

    # ---- helpers ------------------------------------------------------------
    def _adj(self, c, r):
        for dc, dr in ALL8:
            t = (c + dc, r + dr)
            if self.on(*t):
                yield t

    def _find_w(self, board, player):
        for sq, (pl, t) in board.items():
            if pl == player and t == "W":
                return sq
        return None

    # ---- move generation ----------------------------------------------------
    def _gen(self, state) -> list:
        """All legal move strings: standard piece moves (with the iron filter
        and the royal WxW filter), Warlock double moves / igui / pass, castling."""
        board, player = state.board, state.to_move
        enemy = 1 - player
        iron = state.iron
        out = []

        for f, t in self._pseudo(state):
            if iron is not None and t == iron:      # the iron Warlock is uncapturable
                continue
            nb = self._apply_board(board, f, t, state.ep)
            if self.in_check(nb, player):
                continue
            typ = board[f][1]
            occ = board.get(t)
            base = f"{f[0]},{f[1]}>{t[0]},{t[1]}"
            if typ == "W":
                # Royal rule: WxW only if the landing square is king-safe.
                if occ is not None and occ[1] == "W" and self.attacked(nb, t[0], t[1], enemy):
                    continue
                if max(abs(t[0] - f[0]), abs(t[1] - f[1])) == 1:
                    # Adjacent step: encode as f>m>m so it does not shadow the
                    # double-move continuations sharing the same click prefix.
                    out.append(f"{base}>{t[0]},{t[1]}")
                else:
                    out.append(base)
            elif typ == "P":
                for ch in self.PROMOTION.options(self, state, f, t):
                    out.append(base if ch is None else base + "=" + ch)
            else:
                out.append(base)

        # Warlock double moves: first leg captures an adjacent enemy, second leg
        # is a further King step (double capture / move on / return = igui);
        # plus the out-and-back turn pass via an adjacent empty square.
        in_chk = self.in_check(board, player)
        for f, (pl, typ) in list(board.items()):
            if pl != player or typ != "W":
                continue
            fs = f"{f[0]},{f[1]}"
            for m in self._adj(*f):
                occ_m = board.get(m)
                if occ_m is None:
                    if not in_chk:                  # a pass never resolves check
                        out.append(f"{fs}>{m[0]},{m[1]}>{fs}")
                    continue
                if occ_m[0] == player or (iron is not None and m == iron):
                    continue
                for t in self._adj(*m):
                    if t == f:
                        occ_t = None                # returning to the vacated origin
                    else:
                        occ_t = board.get(t)
                        if occ_t is not None and occ_t[0] == player:
                            continue
                        if iron is not None and t == iron:
                            continue
                    nb = dict(board)
                    del nb[f]
                    nb.pop(m, None)
                    nb.pop(t, None)
                    nb[t] = (player, "W")
                    if self.in_check(nb, player):
                        continue
                    w_cap = occ_m[1] == "W" or (occ_t is not None and occ_t[1] == "W")
                    if w_cap and self.attacked(nb, t[0], t[1], enemy):
                        continue                    # royal rule on the final square
                    out.append(f"{fs}>{m[0]},{m[1]}>{t[0]},{t[1]}")

        for kf, kt in self.CASTLING.moves(self, state):
            out.append(f"{kf[0]},{kf[1]}>{kt[0]},{kt[1]}")
        return out

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        return self._gen(state)

    def is_terminal(self, state) -> bool:
        return self._draw(state) or not self._gen(state)

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        if move.count(">") == 2:
            return self._apply_warlock(state, move)
        raw = move.split("=")[0]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        mover = state.board[frm]
        captured = state.board.get(to)
        ns = super().apply_move(state, move, rng)   # plain CState
        iron = None
        if captured is not None and captured[1] == "W" and mover[1] != "W":
            iron = self._find_w(ns.board, mover[0])
        return self._finish(state, ns, iron)

    def _apply_warlock(self, state, move):
        fs, ms, ts = move.split(">")
        f, m, t = cell(fs), cell(ms), cell(ts)
        pl = state.board[f][0]
        b = dict(state.board)
        del b[f]
        occ_m = b.pop(m, None) if m != t else None   # f>m>m captures at t below
        occ_t = b.pop(t, None)
        b[t] = (pl, "W")
        capture = occ_m is not None or occ_t is not None
        rights = set(state.castling)
        for sq, occ in ((m, occ_m), (t, occ_t)):     # a rook grabbed on its home square
            if occ is not None and sq in self.CASTLING.ROOK_HOME:
                rights.discard(self.CASTLING.ROOK_HOME[sq])
        # The mover is a Warlock, so rule 2 (iron) never triggers here.
        result = WState(board=b, to_move=1 - pl, castling=frozenset(rights), ep=None,
                        halfmove=0 if capture else state.halfmove + 1,
                        ply=state.ply + 1, reps={}, iron=None)
        reps = dict(state.reps)
        key = self._poskey_state(result)
        reps[key] = reps.get(key, 0) + 1
        result.reps = reps
        return result

    def _finish(self, prev, ns, iron):
        result = WState(board=ns.board, to_move=ns.to_move, castling=ns.castling,
                        ep=ns.ep, halfmove=ns.halfmove, ply=ns.ply, reps={},
                        iron=iron)
        reps = dict(prev.reps)
        key = self._poskey_state(result)
        reps[key] = reps.get(key, 0) + 1
        result.reps = reps
        return result

    # ---- (de)serialize ------------------------------------------------------
    def _poskey_state(self, state) -> str:
        return super()._poskey_state(state) + f"#i{state.iron}"

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["iron"] = f"{state.iron[0]},{state.iron[1]}" if state.iron else None
        return d

    def deserialize(self, d):
        base = super().deserialize(d)
        iron = cell(d["iron"]) if d.get("iron") else None
        return WState(board=base.board, to_move=base.to_move, castling=base.castling,
                      ep=base.ep, halfmove=base.halfmove, ply=base.ply,
                      reps=base.reps, hands=base.hands, promoted=base.promoted,
                      iron=iron)

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if move.count(">") == 2:
            f, m, t = (cell(p) for p in move.split(">"))
            if m == t:
                sep = "x" if m in state.board else "-"
                return f"W{_alg(f)}{sep}{_alg(m)}"
            if state.board.get(m) is None:
                return f"W{_alg(f)} pass"
            # t == f is the igui return to the (vacated) origin -- not a capture.
            end = f"x{_alg(t)}" if t != f and t in state.board else f"-{_alg(t)}"
            return f"W{_alg(f)}x{_alg(m)}{end}"
        return super().describe_move(state, move)

    def render(self, state, perspective=None) -> dict:
        spec = super().render(state, perspective)
        if state.iron is not None and not self.is_terminal(state):
            spec["caption"] += f" — Warlock {_alg(state.iron)} is iron (uncapturable)"
        return spec
