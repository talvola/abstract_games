"""Hostage Chess (John Leslie, 1997) -- chess where captured men become hostages.

Every captured man goes to the CAPTOR's prison (it never changes colour).
Instead of a normal move a player may:

* perform a HOSTAGE EXCHANGE: release a hostage from their own prison (it goes
  to the opponent's airfield, droppable by the opponent later) to rescue one of
  their own men of equal-or-lesser value from the opponent's prison; the rescued
  man must be parachuted onto an empty square at once, ending the turn; or
* DROP a man from their own airfield onto an empty square.

Piece values for the exchange: Q > R > B = N > P. Pawns may not be dropped on
the 1st or 8th rank; a pawn dropped on its 2nd rank regains the double step; a
rook dropped on a rook starting square can castle (if the king never moved).
A pawn may move to the last rank only if the opponent's prison holds one of the
player's own Q/R/B/N: the pawn goes into that prison and the chosen piece takes
its square (so a 7th-rank pawn with no such piece available cannot advance and
gives no check -- and capturing a Q/R/B/N that would enable it can be an illegal
self-check). Promoted pieces keep their identity when captured.

Sources: chessvariants.com/difftaking.dir/hostage.html (Leslie's own rules page)
and Wikipedia "Hostage chess" (Pritchard, Variant Chess 32 / Popular Chess
Variants ch. 13). White = player 0.

Move encoding (all parseable by the generic web UI):
* board moves  "fc,fr>tc,tr" with "=T" promotion suffix (T from the opponent's
  prison); castling is the usual two-square king move;
* airfield drops "L@c,r" (reserve-tray click);
* a hostage exchange is TWO plies by the same player: the action move
  "exchange:H-L" (release hostage H, rescue own man L; renders as a button)
  followed by the forced parachute drop "L@c,r" (reserve-tray click).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, NoCastling, DropRules,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, cell, _FILES,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

# Exchange values (Leslie: pawn least; knight and bishop equal; then rook; queen).
VAL = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9}

# Castling bookkeeping. The rights set holds corner flags "KQkq" plus
# king-never-moved tokens "E"/"e" -- needed because a rook DROPPED on a home
# corner regenerates that corner's flag, but only while the king has never moved.
KING_TOKEN = {WHITE: "E", BLACK: "e"}
BY_COLOR = {WHITE: ("K", "Q"), BLACK: ("k", "q")}
ROOK_HOME = {(7, 0): "K", (0, 0): "Q", (7, 7): "k", (0, 7): "q"}
FLAG_COLOR = {"K": WHITE, "Q": WHITE, "k": BLACK, "q": BLACK}
CASTLES = {
    "K": ((4, 0), (6, 0), (7, 0), (5, 0), [(5, 0), (6, 0)], [(4, 0), (5, 0), (6, 0)]),
    "Q": ((4, 0), (2, 0), (0, 0), (3, 0), [(1, 0), (2, 0), (3, 0)], [(4, 0), (3, 0), (2, 0)]),
    "k": ((4, 7), (6, 7), (7, 7), (5, 7), [(5, 7), (6, 7)], [(4, 7), (5, 7), (6, 7)]),
    "q": ((4, 7), (2, 7), (0, 7), (3, 7), [(1, 7), (2, 7), (3, 7)], [(4, 7), (3, 7), (2, 7)]),
}


@dataclass
class HState(CState):
    # prisons[p] = men of player 1-p captured (and now held) by player p.
    prisons: dict = field(default_factory=dict)
    # After an "exchange:H-L" action: the rescued letter L that MUST be dropped
    # by the same player before the turn passes. None otherwise.
    pending: Optional[str] = None


class HostageDrops(DropRules):
    """Reserve support is on (hands = the airfields); drop generation itself is
    custom in the game (exchanges, pending-drop phase)."""

    enabled = True

    def initial_hands(self, core) -> dict:
        return {WHITE: {}, BLACK: {}}

    def can_drop_on(self, core, state, letter, to, player) -> bool:
        if letter == "P":
            return 0 < to[1] < core.HEIGHT - 1   # no pawn drops on ranks 1/8
        return True


class HostageChess(ChessLike):
    name = "Hostage Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 800            # an exchange turn costs 2 plies
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
    }
    HEAVY = ("P", "R", "Q")
    PAWN = StandardPawn(white_start=1, black_start=6)
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))   # unused: custom promo logic
    CASTLING = NoCastling()                                # unused: custom castling
    DROPS = HostageDrops()

    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    def initial_state(self, options=None, rng=None):
        st = HState(board=self.setup_board(), to_move=WHITE,
                    castling=frozenset("KQkqEe"), ep=None,
                    hands={WHITE: {}, BLACK: {}},
                    prisons={WHITE: {}, BLACK: {}})
        st.reps = {self._poskey_state(st): 1}
        return st

    # ---- prison-aware attacks ----------------------------------------------
    # A pawn attacks (= could capture onto) a square on its LAST rank only if
    # its owner could promote there, i.e. the opponent's prison holds one of the
    # owner's Q/R/B/N. Everything else is as in orthodox chess.
    def _attacked_h(self, board, c, r, by, prisons) -> bool:
        for (dx, dy), types in self._leap_map.items():
            occ = board.get((c + dx, r + dy))
            if occ is not None and occ[0] == by and occ[1] in types:
                return True
        for (dx, dy), types in self._slide_map.items():
            cc, rr = c + dx, r + dy
            while self.on(cc, rr):
                occ = board.get((cc, rr))
                if occ is not None:
                    if occ[0] == by and occ[1] in types:
                        return True
                    break
                cc += dx
                rr += dy
        last = (r == self.HEIGHT - 1) if by == WHITE else (r == 0)
        if last and not self._promo_types_p(prisons, by):
            return False
        fwd = 1 if by == WHITE else -1
        return any(board.get((c + dc, r - fwd)) == (by, "P") for dc in (-1, 1))

    def _in_check_h(self, board, player, prisons) -> bool:
        k = self._king(board, player)
        return k is not None and self._attacked_h(board, k[0], k[1], 1 - player, prisons)

    @staticmethod
    def _promo_types_p(prisons, player):
        """Piece types ``player`` may promote to: own Q/R/B/N held in the
        OPPONENT's prison (prisons[1-player] holds player's captured men)."""
        pr = prisons.get(1 - player, {})
        return [L for L in ("Q", "R", "B", "N") if pr.get(L, 0) > 0]

    def _last_rank(self, player) -> int:
        return self.HEIGHT - 1 if player == WHITE else 0

    # ---- move generation ----------------------------------------------------
    def _sim(self, state, frm, to, promo):
        """(board, prisons) after a board move, for king-safety testing."""
        b = dict(state.board)
        pl, t = b.pop(frm)
        capture_sq = to if to in state.board else None
        if t == "P" and capture_sq is None and state.ep is not None and to == state.ep[0]:
            capture_sq = state.ep[1]
        prisons = state.prisons
        if capture_sq is not None or promo:
            prisons = {p: dict(h) for p, h in state.prisons.items()}
        if capture_sq is not None:
            cap = state.board[capture_sq]
            prisons[pl][cap[1]] = prisons[pl].get(cap[1], 0) + 1
            if capture_sq != to:
                b.pop(capture_sq, None)
        if promo:
            prisons[1 - pl][promo] -= 1
            prisons[1 - pl]["P"] = prisons[1 - pl].get("P", 0) + 1
            t = promo
        b[to] = (pl, t)
        return b, prisons

    def _board_moves(self, state) -> list:
        out = []
        pl = state.to_move
        last = self._last_rank(pl)
        promos = None
        for frm, to in self._pseudo(state):
            t = state.board[frm][1]
            if t == "P" and to[1] == last:
                if promos is None:
                    promos = self._promo_types_p(state.prisons, pl)
                choices = promos
                if not choices:
                    continue      # no piece available in the opponent's prison
            else:
                choices = [None]
            # Own-king safety is identical across promotion choices (the piece
            # type on `to` and prisons[1-pl] never affect attacks on pl's king).
            b, pr = self._sim(state, frm, to, choices[0])
            if self._in_check_h(b, pl, pr):
                continue
            base = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
            for ch in choices:
                out.append(base if ch is None else base + "=" + ch)
        return out

    def _castle_moves(self, state):
        pl = state.to_move
        rights = state.castling
        if KING_TOKEN[pl] not in rights:
            return
        if self._in_check_h(state.board, pl, state.prisons):
            return
        for flag in BY_COLOR[pl]:
            if flag not in rights:
                continue
            kfrom, kto, rfrom, rto, empties, path = CASTLES[flag]
            if state.board.get(kfrom) != (pl, "K") or state.board.get(rfrom) != (pl, "R"):
                continue
            if any(sq in state.board for sq in empties):
                continue
            if any(self._attacked_h(state.board, c, r, 1 - pl, state.prisons)
                   for (c, r) in path):
                continue
            yield f"{kfrom[0]},{kfrom[1]}>{kto[0]},{kto[1]}"

    def _drop_squares(self, state, letter):
        for r in range(self.HEIGHT):
            if letter == "P" and (r == 0 or r == self.HEIGHT - 1):
                continue
            for c in range(self.WIDTH):
                if (c, r) not in state.board:
                    yield (c, r)

    def _drops_of(self, state, letter, prisons, in_chk) -> list:
        """Legal "L@c,r" drops. A drop can never expose the dropper's own king,
        so only when already in check must each placement be safety-tested."""
        pl = state.to_move
        out = []
        for (c, r) in self._drop_squares(state, letter):
            if in_chk:
                b = dict(state.board)
                b[(c, r)] = (pl, letter)
                if self._in_check_h(b, pl, prisons):
                    continue
            out.append(f"{letter}@{c},{r}")
        return out

    def _exchange_moves(self, state) -> list:
        """"exchange:H-L": release hostage H (value >= L) from my prison to the
        opponent's airfield and rescue my man L from the opponent's prison.
        Offered only if at least one completing drop of L would be legal (the
        release itself may resolve a promotion-pawn check, so feasibility is
        tested with the post-exchange prisons)."""
        pl = state.to_move
        out = []
        for L, nl in sorted(state.prisons.get(1 - pl, {}).items()):
            if nl <= 0:
                continue
            for H, nh in sorted(state.prisons.get(pl, {}).items()):
                if nh <= 0 or VAL[H] < VAL[L]:
                    continue
                pr2 = {p: dict(h) for p, h in state.prisons.items()}
                pr2[pl][H] -= 1
                pr2[1 - pl][L] -= 1
                if not self._in_check_h(state.board, pl, pr2):
                    feasible = any(True for _ in self._drop_squares(state, L))
                else:
                    feasible = False
                    for (c, r) in self._drop_squares(state, L):
                        b = dict(state.board)
                        b[(c, r)] = (pl, L)
                        if not self._in_check_h(b, pl, pr2):
                            feasible = True
                            break
                if feasible:
                    out.append(f"exchange:{H}-{L}")
        return out

    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        pl = state.to_move
        if state.pending:
            in_chk = self._in_check_h(state.board, pl, state.prisons)
            return self._drops_of(state, state.pending, state.prisons, in_chk)
        out = self._board_moves(state)
        out.extend(self._castle_moves(state))
        in_chk = self._in_check_h(state.board, pl, state.prisons)
        for L, n in sorted(state.hands.get(pl, {}).items()):
            if n > 0:
                out.extend(self._drops_of(state, L, state.prisons, in_chk))
        out.extend(self._exchange_moves(state))
        return out

    # ---- apply --------------------------------------------------------------
    def _update_rights(self, rights, frm, to, board) -> frozenset:
        rights = set(rights)
        pl, t = board[frm]
        if t == "K":
            rights -= {KING_TOKEN[pl], *BY_COLOR[pl]}
        if frm in ROOK_HOME:
            rights.discard(ROOK_HOME[frm])
        if to in ROOK_HOME:                  # a rook captured on its home square
            rights.discard(ROOK_HOME[to])
        return frozenset(rights)

    def _finish(self, ns):
        key = self._poskey_state(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        return ns

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        if move.startswith("exchange:"):
            H, L = move.split(":", 1)[1].split("-")
            prisons = {p: dict(h) for p, h in state.prisons.items()}
            prisons[pl][H] -= 1
            if prisons[pl][H] <= 0:
                del prisons[pl][H]
            prisons[1 - pl][L] -= 1
            if prisons[1 - pl][L] <= 0:
                del prisons[1 - pl][L]
            hands = {p: dict(h) for p, h in state.hands.items()}
            hands[1 - pl][H] = hands[1 - pl].get(H, 0) + 1
            return self._finish(HState(
                board=dict(state.board), to_move=pl, castling=state.castling,
                ep=None, halfmove=state.halfmove, ply=state.ply + 1,
                reps=dict(state.reps), hands=hands, prisons=prisons, pending=L))

        if "@" in move:
            letter, cs = move.split("@")
            to = cell(cs)
            b = dict(state.board)
            b[to] = (pl, letter)
            hands = {p: dict(h) for p, h in state.hands.items()}
            if state.pending is not None:      # the parachute completing an exchange
                pending_ok = letter == state.pending
                assert pending_ok, f"must drop the rescued {state.pending}"
            else:                              # a plain airfield drop
                hands[pl][letter] = hands[pl].get(letter, 0) - 1
                if hands[pl][letter] <= 0:
                    del hands[pl][letter]
            rights = state.castling
            if letter == "R" and to in ROOK_HOME:
                flag = ROOK_HOME[to]
                # A rook dropped on a home corner can castle -- but only while
                # the king has never moved.
                if FLAG_COLOR[flag] == pl and KING_TOKEN[pl] in rights:
                    rights = frozenset(set(rights) | {flag})
            return self._finish(HState(
                board=b, to_move=1 - pl, castling=rights, ep=None,
                halfmove=state.halfmove + 1, ply=state.ply + 1,
                reps=dict(state.reps), hands=hands,
                prisons={p: dict(h) for p, h in state.prisons.items()}, pending=None))

        promo = None
        if "=" in move:
            move, promo = move.split("=")
        fs, ts = move.split(">")
        frm, to = cell(fs), cell(ts)
        pl_, t = state.board[frm]
        b = dict(state.board)
        b.pop(frm)
        prisons = {p: dict(h) for p, h in state.prisons.items()}
        capture_sq = to if to in state.board else None
        ep_new = None
        if t == "K" and abs(to[0] - frm[0]) == 2:      # castling
            flag = BY_COLOR[pl][0] if to[0] > frm[0] else BY_COLOR[pl][1]
            _, _, rfrom, rto, _, _ = CASTLES[flag]
            b[rto] = b.pop(rfrom)
        elif t == "P":
            if capture_sq is None and state.ep is not None and to == state.ep[0]:
                capture_sq = state.ep[1]
            elif capture_sq is None:
                ep_new = self.PAWN.ep_after(frm, to)
        if capture_sq is not None:
            cap = state.board[capture_sq]
            prisons[pl][cap[1]] = prisons[pl].get(cap[1], 0) + 1
            if capture_sq != to:
                b.pop(capture_sq, None)
        if promo:
            prisons[1 - pl][promo] -= 1
            if prisons[1 - pl][promo] <= 0:
                del prisons[1 - pl][promo]
            prisons[1 - pl]["P"] = prisons[1 - pl].get("P", 0) + 1
            t = promo
        b[to] = (pl, t)
        rights = self._update_rights(state.castling, frm, to, state.board)
        reset = capture_sq is not None or state.board[frm][1] == "P"
        return self._finish(HState(
            board=b, to_move=1 - pl, castling=rights, ep=ep_new,
            halfmove=0 if reset else state.halfmove + 1, ply=state.ply + 1,
            reps=dict(state.reps), hands={p: dict(h) for p, h in state.hands.items()},
            prisons=prisons, pending=None))

    # ---- terminal -----------------------------------------------------------
    def is_terminal(self, state) -> bool:
        return self._draw(state) or not self.legal_moves(state)

    def returns(self, state) -> list:
        if self._draw(state) or not self._in_check_h(state.board, state.to_move,
                                                     state.prisons):
            return [0.0, 0.0]
        return [-1.0, 1.0] if state.to_move == WHITE else [1.0, -1.0]

    def heuristic(self, state) -> list:
        """Material eval; imprisoned men count half for their OWNER (they may be
        rescued), airfield men full. Returns [white, black] payoffs."""
        vals = self.PIECE_VALUES
        bal = 0.0
        for (p, t) in state.board.values():
            bal += vals.get(t, 3.0) * (1.0 if p == WHITE else -1.0)
        for p, hand in state.hands.items():
            s = 1.0 if p == WHITE else -1.0
            bal += s * sum(vals.get(t, 3.0) * n for t, n in hand.items())
        for p, pris in state.prisons.items():
            s = 1.0 if (1 - p) == WHITE else -1.0     # held men belong to 1-p
            bal += 0.5 * s * sum(vals.get(t, 3.0) * n for t, n in pris.items())
        if state.pending:
            s = 1.0 if state.to_move == WHITE else -1.0
            bal += s * vals.get(state.pending, 3.0)
        score = math.tanh(bal / 8.0)
        return [score, -score]

    # ---- keys / (de)serialize ----------------------------------------------
    def _poskey_state(self, state) -> str:
        key = self._poskey(state.board, state.to_move, state.castling, state.ep,
                           state.hands)
        key += "#P" + ";".join(
            f"{p}=" + ",".join(f"{L}{n}" for L, n in sorted(h.items()) if n > 0)
            for p, h in sorted(state.prisons.items()))
        if state.pending:
            key += "#!" + state.pending
        return key

    def serialize(self, state) -> dict:
        d = super().serialize(state)
        d["prisons"] = {str(p): {L: n for L, n in sorted(h.items()) if n > 0}
                        for p, h in sorted(state.prisons.items())}
        if state.pending:
            d["pending"] = state.pending
        return d

    def deserialize(self, d: dict):
        s = super().deserialize(d)
        return HState(
            board=s.board, to_move=s.to_move, castling=s.castling, ep=s.ep,
            halfmove=s.halfmove, ply=s.ply, reps=s.reps, hands=s.hands,
            promoted=s.promoted,
            prisons={int(p): {L: int(n) for L, n in h.items()}
                     for p, h in d.get("prisons", {}).items()},
            pending=d.get("pending"))

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        if move.startswith("exchange:"):
            H, L = move.split(":", 1)[1].split("-")
            return f"({H}-{L})"                       # Leslie's notation prefix
        if "@" in move:
            letter, cs = move.split("@")
            c = cell(cs)
            sq = f"{_FILES[c[0]]}{c[1] + 1}"
            return ("*" if letter == "P" else letter + "*") + sq
        raw, promo = (move.split("=") + [None])[:2]
        fs, ts = raw.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        if t == "K" and abs(to[0] - frm[0]) == 2:
            return "O-O" if to[0] > frm[0] else "O-O-O"
        capture = to in state.board or (t == "P" and state.ep is not None
                                        and to == state.ep[0])
        alg = lambda c: f"{_FILES[c[0]]}{c[1] + 1}"  # noqa: E731
        return f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}" + (
            f"={promo}" if promo else "")

    def render(self, state, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": pl, "label": t}
                  for (c, r), (pl, t) in state.board.items()]
        names = {WHITE: "White", BLACK: "Black"}

        def inv(h):
            return "".join(f"{L}" + ("" if n == 1 else str(n))
                           for L, n in sorted(h.items()) if n > 0) or "-"

        info = (f"prisons W:{inv(state.prisons.get(WHITE, {}))}"
                f" B:{inv(state.prisons.get(BLACK, {}))}"
                f" | airfields W:{inv(state.hands.get(WHITE, {}))}"
                f" B:{inv(state.hands.get(BLACK, {}))}")
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = ("Draw" if ret == [0.0, 0.0]
                       else f"{names[0 if ret[0] > 0 else 1]} wins (checkmate)")
        else:
            chk = " (check)" if self._in_check_h(state.board, state.to_move,
                                                 state.prisons) else ""
            who = names[state.to_move]
            if state.pending:
                caption = f"{who} must drop the rescued {state.pending}{chk} — {info}"
            else:
                caption = f"{who} to move{chk} — {info}"
        reserve = {}
        for p in (WHITE, BLACK):
            if state.pending and p == state.to_move:
                # Mid-exchange the only legal action is parachuting the rescued
                # man, so the tray shows just that chip.
                reserve[str(p)] = {state.pending: 1}
            else:
                reserve[str(p)] = {L: n for L, n in
                                   sorted(state.hands.get(p, {}).items()) if n > 0}
        # Friendly labels for the "exchange:H-L" action buttons (H handed back to
        # the opponent's airfield, L rescued and parachuted). Only meaningful when
        # not mid-exchange, when such moves are actually offered.
        action_names = {}
        if not state.pending and not self.is_terminal(state):
            for m in self._exchange_moves(state):
                H, L = m.split(":", 1)[1].split("-")
                action_names[m] = f"Hand back {H}, rescue {L}"
        return {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
            "pieceset": "chess",
            "reserve": reserve,
            "actionNames": action_names,
        }
