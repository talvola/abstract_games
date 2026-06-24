"""Seirawan Chess (S-Chess / S-HARP), by Yasser Seirawan and Bruce Harper (2007).

Standard 8x8 FIDE chess plus two extra pieces held off the board in each player's
reserve ("in hand"):

  * **Hawk (H)**  = Bishop + Knight (the "princess"/"archbishop" compound).
  * **Elephant (E)** = Rook + Knight (the "chancellor"/"marshall" compound).

The signature mechanic is **gating**: the FIRST time a player moves one of their
ORIGINAL back-rank pieces (or castles), they MAY simultaneously place a Hawk or an
Elephant from their reserve onto the square that piece just vacated.

  * Gating is OPTIONAL on each such move; each gate piece can enter only once.
  * Once an original back-rank piece leaves its home square WITHOUT gating, that
    square's gating right is GONE (the only chance was that first move).
  * When castling, BOTH the king's and the rook's home squares are vacated; you
    may gate ONE piece onto EITHER vacated square (not both).
  * A gating placement may NOT be used to block a check (you may not be in check
    when you gate; the gated piece may, however, give check or even checkmate).
  * Pawns may promote to a Hawk or an Elephant, but ONLY if that piece is still in
    the player's reserve; doing so removes it from the reserve (so it can no longer
    be gated). Promotion to Q/R/B/N is always available.

Move encoding (drives the EXISTING generic UI's "=choice" picker, no UI change):
  A gating move is an ordinary back-rank move/castle with a "=" suffix naming the
  gate. For a back-rank piece moving frm->to:
      "fc,fr>tc,tr"          -- move, no gate (always offered)
      "fc,fr>tc,tr=H"        -- ... and gate a Hawk onto the vacated FROM square
      "fc,fr>tc,tr=E"        -- ... and gate an Elephant onto the vacated FROM square
  For castling (king's two-square move), the king's vacated square uses =H/=E and
  the rook's vacated square uses =Hr/=Er. Because these share the same cell path,
  the generic Board.jsx pops up its choice picker (the same widget pawn promotion
  uses); spec.choiceNames/choiceTitle label the options. Pawn promotion keeps its
  ordinary "=Q/=R/=B/=N/=H/=E" suffix.

White = player 0 (advances toward higher rows).
"""

from __future__ import annotations

from agp.chesslike import (
    ChessLike, CState, StandardPawn, LastRankPromotion, StandardCastling,
    ORTHO, DIAG, ALL8, KNIGHT, WHITE, BLACK, cell,
)

BACK_RANK = ["R", "N", "B", "Q", "K", "B", "N", "R"]

# Home back-rank squares per colour (where gating may occur on the first move).
WHITE_HOME = frozenset((c, 0) for c in range(8))
BLACK_HOME = frozenset((c, 7) for c in range(8))


class Seirawan(ChessLike):
    uid = "seirawan"
    name = "Seirawan Chess"

    WIDTH = HEIGHT = 8
    PLY_CAP = 600
    PIECES = {
        "R": (ORTHO, []), "B": (DIAG, []), "Q": (ALL8, []),
        "N": ([], KNIGHT), "K": ([], ALL8),
        "H": (DIAG, KNIGHT),     # Hawk  = Bishop + Knight
        "E": (ORTHO, KNIGHT),    # Elephant = Rook + Knight
    }
    HEAVY = ("P", "R", "Q", "H", "E")
    PAWN = StandardPawn(white_start=1, black_start=6)
    CASTLING = StandardCastling()
    # The actual promotion menu depends on the reserve and is built in
    # _promotion_moves below; PROMOTION here is consulted ONLY by the shared
    # king-safety code (its safety_piece(), a Queen stand-in).
    PROMOTION = LastRankPromotion(("Q", "R", "B", "N"))
    PROMO_BASE = ("Q", "R", "B", "N")    # always-available promotion targets

    # ---- setup --------------------------------------------------------------
    def setup_board(self) -> dict:
        b = {}
        for c in range(8):
            b[(c, 0)] = (WHITE, BACK_RANK[c])
            b[(c, 1)] = (WHITE, "P")
            b[(c, 6)] = (BLACK, "P")
            b[(c, 7)] = (BLACK, BACK_RANK[c])
        return b

    def _home(self, player) -> frozenset:
        return WHITE_HOME if player == WHITE else BLACK_HOME

    # ---- state with gating rights ------------------------------------------
    # We piggy-back two extra pieces of state on CState:
    #   state.hands  -> {player: {"H": n, "E": n}}     (reserve, reused machinery)
    #   state.gates  -> frozenset of home squares that may STILL gate (set by us)
    # gates is a plain attribute set on the CState instance.

    def initial_state(self, options=None, rng=None):
        board = self.setup_board()
        rights = self.CASTLING.initial_rights()
        hands = {WHITE: {"H": 1, "E": 1}, BLACK: {"H": 1, "E": 1}}
        st = CState(board=board, to_move=WHITE, castling=rights, ep=None, hands=hands)
        st.gates = WHITE_HOME | BLACK_HOME
        st.reps = {self._poskey_state(st): 1}
        return st

    def _gates(self, state) -> frozenset:
        return getattr(state, "gates", frozenset())

    def _has_reserve(self, state, player) -> bool:
        h = state.hands.get(player, {})
        return h.get("H", 0) > 0 or h.get("E", 0) > 0

    def _reserve_letters(self, state, player) -> list:
        h = state.hands.get(player, {})
        return [L for L in ("H", "E") if h.get(L, 0) > 0]

    # ---- gating helpers -----------------------------------------------------
    def _gate_squares(self, state, frm, to, player):
        """Return [(choice_suffix, vacated_square), ...] for the gate placements
        available on the move frm->to (a back-rank piece's FIRST move / castle).
        Empty if no gating is possible for this move."""
        if not self._has_reserve(state, player):
            return []
        gates = self._gates(state)
        # in-check gating is forbidden (cannot use gating to block check)
        if self.in_check(state.board, player):
            return []
        pl, t = state.board[frm]
        opts = []
        # Castling: king moves two squares; both king & rook home squares vacate.
        if t == "K":
            rook = self.CASTLING.rook_move(frm, to, player)
        else:
            rook = None
        if rook is not None:
            if frm in gates:
                opts.append(("", frm))          # king square -> =H/=E
            if rook[0] in gates:
                opts.append(("r", rook[0]))     # rook square -> =Hr/=Er
        else:
            if frm in gates:
                opts.append(("", frm))
        return opts

    # ---- move generation ----------------------------------------------------
    def legal_moves(self, state) -> list:
        if self._draw(state):
            return []
        player = state.to_move
        out = []
        for frm, to in self._legal(state):
            base = f"{frm[0]},{frm[1]}>{to[0]},{to[1]}"
            t = state.board.get(frm, (None, "?"))[1]
            if t == "P":
                out.extend(self._promotion_moves(state, frm, to, base))
            else:
                out.append(base)
                for suffix, sq in self._gate_squares(state, frm, to, player):
                    for L in self._reserve_letters(state, player):
                        out.append(f"{base}={L}{suffix}")
        return out

    def _promotion_moves(self, state, frm, to, base):
        pl = state.board[frm][0]
        last = (to[1] == self.HEIGHT - 1 and pl == WHITE) or (to[1] == 0 and pl == BLACK)
        if not last:
            return [base]
        targets = list(self.PROMO_BASE)
        # Hawk / Elephant promotion ONLY if still in reserve.
        for L in self._reserve_letters(state, pl):
            targets.append(L)
        return [base + "=" + T for T in targets]

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        gate = None        # (letter, vacated_square) or None
        promo = None
        body = move
        if "=" in body:
            body, suffix = body.split("=")
            # A gate suffix is H | E | Hr | Er on a back-rank piece move; a
            # promotion suffix is a bare piece letter (Q/R/B/N/H/E) on a PAWN move.
            fs0 = body.split(">")[0]
            mover = state.board.get(cell(fs0), (None, "?"))[1]
            if mover == "P":
                promo = suffix          # pawn promotion (may be H or E from reserve)
            else:
                gate = self._parse_gate(state, body, suffix)
        fs, ts = body.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board[frm]

        b = dict(state.board)
        b.pop(frm)
        hands = {p: dict(h) for p, h in state.hands.items()}
        gates = set(self._gates(state))

        capture = to in state.board
        captured = state.board.get(to)
        captured_sq = to if capture else None
        ep_new = None

        rook = self.CASTLING.rook_move(frm, to, pl) if t == "K" else None
        if rook is not None:
            b[rook[1]] = b.pop(rook[0])
            gates.discard(frm)
            gates.discard(rook[0])
        elif t == "P":
            if state.ep is not None and to == state.ep[0] and to not in state.board:
                captured_sq = state.ep[1]
                captured = state.board.get(captured_sq)
                b.pop(captured_sq, None)
                capture = True
            else:
                ep_new = self.PAWN.ep_after(frm, to)
        else:
            # any non-castling, non-pawn move off (or onto) a home square clears
            # that square's gating right (the piece has now left without gating
            # unless we gate this very move, handled below).
            gates.discard(frm)

        # Promotion (Q/R/B/N always; H/E only if it was in reserve -> consume it).
        promoting = t == "P" and bool(promo)
        if promoting:
            if promo in ("H", "E"):
                hands.setdefault(pl, {})
                hands[pl][promo] = hands[pl].get(promo, 0) - 1
                if hands[pl][promo] <= 0:
                    del hands[pl][promo]
            t = promo
        b[to] = (pl, t)

        # A captured piece on a home square also kills that square's gating right.
        if captured_sq is not None:
            gates.discard(captured_sq)
        # A piece moving ONTO a home square never grants gating; landing there is
        # irrelevant. (gates only ever shrinks.)

        # Perform the gate placement (onto the vacated square), consuming reserve.
        if gate is not None:
            letter, vsq = gate
            b[vsq] = (pl, letter)
            hands.setdefault(pl, {})
            hands[pl][letter] = hands[pl].get(letter, 0) - 1
            if hands[pl][letter] <= 0:
                del hands[pl][letter]
            # the gated-onto square is consumed; (castling's other home square's
            # right is already discarded above).
            gates.discard(vsq)

        castling = self.CASTLING.update_rights(state.castling, frm, to, state.board)
        reset = capture or state.board[frm][1] == "P"
        new = CState(
            board=b, to_move=1 - pl, castling=castling, ep=ep_new,
            halfmove=0 if reset else state.halfmove + 1,
            ply=state.ply + 1, hands=hands,
        )
        new.gates = frozenset(gates)
        key = self._poskey_state(new)
        reps = dict(state.reps)
        reps[key] = reps.get(key, 0) + 1
        new.reps = reps
        return new

    def _parse_gate(self, state, body, suffix):
        player = state.to_move
        fs, ts = body.split(">")
        frm, to = cell(fs), cell(ts)
        letter = suffix[0]
        is_rook = suffix.endswith("r")
        if state.board[frm][1] == "K" and self.CASTLING.rook_move(frm, to, player) is not None:
            if is_rook:
                vsq = self.CASTLING.rook_move(frm, to, player)[0]
            else:
                vsq = frm
        else:
            vsq = frm
        return (letter, vsq)

    # ---- king safety: a gated move must also leave the king safe ------------
    # The base _legal already verifies the plain move's king safety. A gate only
    # ADDS a friendly piece on a vacated square, which can never expose the king,
    # so the gated variants are legal exactly when the plain move is -- no extra
    # check needed. (Gating-while-in-check is already excluded in _gate_squares.)

    # ---- (de)serialize: round-trip hands + gating rights --------------------
    def _poskey_state(self, state) -> str:
        base = self._poskey(state.board, state.to_move, state.castling, state.ep,
                            state.hands)
        return base + "#G" + ",".join(f"{c}.{r}" for (c, r) in sorted(self._gates(state)))

    def serialize(self, state) -> dict:
        ep = state.ep
        d = {
            "board": {f"{c},{r}": [pl, t] for (c, r), (pl, t) in state.board.items()},
            "to_move": state.to_move,
            "castling": "".join(sorted(state.castling)),
            "ep": f"{ep[0][0]},{ep[0][1]},{ep[1][0]},{ep[1][1]}" if ep else None,
            "halfmove": state.halfmove,
            "ply": state.ply,
            "reps": dict(state.reps),
            "hands": {str(p): {L: n for L, n in sorted(h.items()) if n > 0}
                      for p, h in sorted(state.hands.items())},
            "gates": [f"{c},{r}" for (c, r) in sorted(self._gates(state))],
        }
        return d

    def deserialize(self, d: dict):
        ep = None
        if d.get("ep"):
            a, b, c, e = (int(x) for x in d["ep"].split(","))
            ep = ((a, b), (c, e))
        hands = {int(p): {L: int(n) for L, n in h.items()}
                 for p, h in d.get("hands", {}).items()}
        st = CState(
            board={cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"],
            castling=frozenset(d.get("castling", "")),
            ep=ep,
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
            hands=hands,
        )
        st.gates = frozenset(cell(s) for s in d.get("gates", []))
        return st

    # ---- terminal / draws use the gate-aware legal_moves --------------------
    def is_terminal(self, state) -> bool:
        if self._draw(state):
            return True
        return not self.legal_moves(state)

    # ---- presentation -------------------------------------------------------
    def describe_move(self, state, move) -> str:
        body = move
        suffix = None
        if "=" in body:
            body, suffix = body.split("=")
        fs, ts = body.split(">")
        frm, to = cell(fs), cell(ts)
        pl, t = state.board.get(frm, (None, "?"))
        files = "abcdefgh"
        alg = lambda c: f"{files[c[0]]}{c[1] + 1}"  # noqa: E731
        castle = t == "K" and self.CASTLING.rook_move(frm, to, pl) is not None
        if castle:
            text = "O-O" if to[0] > frm[0] else "O-O-O"
        else:
            capture = to in state.board or (
                t == "P" and state.ep is not None and to == state.ep[0])
            text = f"{t}{alg(frm)}{'x' if capture else '-'}{alg(to)}"
        if suffix is None:
            return text
        if t == "P":
            return text + "=" + suffix          # promotion
        # gate suffix
        letter = suffix[0]
        if castle:
            vsq = (self.CASTLING.rook_move(frm, to, pl)[0]
                   if suffix.endswith("r") else frm)
        else:
            vsq = frm
        return f"{text}/{letter}{alg(vsq)}"      # e.g. "Nb1-c3/Ha1"

    def render(self, state, perspective=None) -> dict:
        pieces = [
            {"cell": f"{c},{r}", "owner": pl, "label": t}
            for (c, r), (pl, t) in state.board.items()
        ]
        names = {WHITE: "White", BLACK: "Black"}
        if self.is_terminal(state):
            ret = self.returns(state)
            caption = ("Draw" if ret == [0.0, 0.0]
                       else f"{names[0 if ret[0] > 0 else 1]} wins (checkmate)")
        elif self.in_check(state.board, state.to_move):
            caption = f"{names[state.to_move]} to move (check)"
        else:
            caption = f"{names[state.to_move]} to move"
        spec = {
            "board": {"type": "square", "width": self.WIDTH, "height": self.HEIGHT},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
            "reserve": {
                str(p): {L: n for L, n in sorted(h.items()) if n > 0}
                for p, h in sorted(state.hands.items())
            },
            "choiceNames": {
                "H": "Gate Hawk", "E": "Gate Elephant",
                "Hr": "Gate Hawk (rook square)", "Er": "Gate Elephant (rook square)",
                "Q": "Queen", "R": "Rook", "B": "Bishop", "N": "Knight",
            },
            "choiceTitle": "Choose move / gating",
        }
        return spec
