"""Shared core for the classical hexagonal chesses.

The hex-chess family (Gliński 1936, McCooey, Shafran 1939, Brusky 1966,
de Vasa 1953, McCooey's Mini Hexchess) turned out to be ~65% identical code,
and the duplicated part is exactly the reusable layer. This module is that
layer; a variant supplies only what genuinely differs.

WHY THIS IS SOUND
-----------------
The key finding (proved while building Brusky's game, then verified across all
six packages) is that **the orthogonal, diagonal and knight offset tables are
BYTE-IDENTICAL in axial space for every member of the family**, including the
two board orientations. Gliński/McCooey/Shafran are drawn with vertical files
and Brusky/de Vasa with horizontal ranks, but that is a RENDERING difference
(`board.orientation`, see SPEC.md) — in (q, r) coordinates the lattice is the
same lattice. What actually varies between variants is which axial vector is
"forward" for a pawn, and the pawn rules built on top of that.

So the rook / bishop / queen / knight / king move generation, attack detection,
check and mate, the draw rules, serialisation, rendering and the MCTS heuristic
are all shared here, and a variant implements a small set of hooks.

THE SEAM (what a variant must provide)
--------------------------------------
Required class attributes:
    CELLS       frozenset of (q, r) -- the board's cell set
    FILES       notation letters (used by the variant's own cell_name)
    NAME_OF     {WHITE: "White", BLACK: "Black"} display names
    PLY_CAP     termination backstop; MUST be derived from the variant's own
                bound and be dead code (see `Game.rules` / CLAUDE.md). If random
                play can reach it, it is a bug, not a backstop.

Required methods:
    cell_name(cell)                  -> the variant's own notation, e.g. "f1"
    pawn_moves(state, cell, out)     -> append this pawn's pseudo-legal moves
    pawn_attacks(player, cell)       -> cells this pawn ATTACKS (for check
                                        detection; separate from pawn_moves
                                        because a pawn's captures and its
                                        advances differ, and because Brusky's
                                        capture set depends on the cell)
    is_promo(player, cell)           -> does a pawn of `player` promote here?

Optional hooks (sensible defaults provided):
    PROMO_CHOICES                    default ("Q", "R", "B", "N"); Mini
                                     Hexchess overrides to ("R", "B", "N")
    STALEMATE_SCORED                 default False (stalemate is a draw).
                                     Gliński sets True: its stalemate is a
                                     SCORED 3/4-1/4 result, not a draw.
    castle_moves(state, out)         default none
    update_castling(rights, frm, to, board) -> new rights; default unchanged
    ep_after(state, frm, to, piece)  -> new ep value or None; default None
    ep_to_json / ep_from_json        the ON-DISK shape of `ep`. **Do not change
                                     an existing variant's encoding**: the
                                     server stores serialized state in the DB
                                     (`Match.state`), so a shape change breaks
                                     in-progress async matches.

THE CANONICAL MOVE TUPLE
------------------------
`(frm, to, promo, ep_victim, castle)` where `ep_victim` is the cell of the pawn
to REMOVE (None unless this is an en-passant capture) and `castle` is None or
(rook_from, rook_to). Before this module the six games used three different
tuple shapes; unifying on the victim cell (rather than a bare `is_ep` flag)
covers all of them, including Shafran's multi-cell en passant, where a 3-step
first move leaves TWO capturable cells behind one pawn.

THE CANONICAL `ep` STATE
------------------------
`(victim_cell, (target_cell, ...))` -- the pawn that may be captured, and the
cells from which it may be taken. Gliński/Brusky/de Vasa have exactly one
target; Shafran has one or two.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

from agp.game import Game

WHITE, BLACK = 0, 1

# Axial (q, r) offsets, cube s = -q-r. Identical for EVERY member of the
# family -- see the module docstring.
ORTHO = [(0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]      # cell edges
DIAG = [(1, -2), (2, -1), (1, 1), (-1, 2), (-2, 1), (-1, -1)]     # cell vertices
KNIGHT = [(1, -3), (2, -3), (3, -2), (3, -1), (2, 1), (1, 2),
          (-1, 3), (-2, 3), (-3, 2), (-3, 1), (-2, -1), (-1, -2)]

# Material values for the MCTS rollout cutoff heuristic. The royal piece scores
# 0 (it is always present); the extra bishop makes the hex armies slightly
# minor-heavy but the ordering is what matters.
PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}


@dataclass
class HState:
    """Shared state. Field ORDER matters only to positional construction, which
    this module never uses -- variants and the core always pass by keyword."""
    board: dict = field(default_factory=dict)   # (q,r) -> (owner, letter)
    to_move: int = WHITE
    ep: Optional[tuple] = None                  # (victim_cell, (target, ...))
    castling: frozenset = frozenset()           # variant-defined rights tokens
    halfmove: int = 0        # plies since last pawn move / capture (50-move)
    ply: int = 0
    reps: dict = field(default_factory=dict)    # position key -> count
    last: Optional[tuple] = None                # (from, to), for highlights


def cell_str(c) -> str:
    return f"{c[0]},{c[1]}"


def parse_cell(s: str):
    q, r = s.split(",")
    return int(q), int(r)


class HexChessLike(Game):
    """Base class for the classical hexagonal chesses."""

    # ---- the seam: variants override these -------------------------------
    CELLS: frozenset = frozenset()
    FILES: str = ""
    NAME_OF = {WHITE: "White", BLACK: "Black"}
    PLY_CAP: int = 25000
    PROMO_CHOICES = ("Q", "R", "B", "N")
    STALEMATE_SCORED = False       # Gliński: stalemate scores 3/4 - 1/4
    STATE = HState

    def cell_name(self, cell) -> str:            # pragma: no cover - abstract
        raise NotImplementedError

    def pawn_moves(self, s, cell, out) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def pawn_attackers(self, player: int, cell):  # pragma: no cover - abstract
        """Cells from which a pawn of `player` would ATTACK `cell`.

        The REVERSE of the capture directions, because check detection asks
        "is this square attacked?" and must not scan the board. Brusky's
        capture set depends on the source cell (its vertical diagonal only
        applies from the home rank), so this is a hook, not a table.
        """
        raise NotImplementedError

    def is_promo(self, player: int, cell) -> bool:  # pragma: no cover
        raise NotImplementedError

    def setup_board(self) -> dict:               # pragma: no cover - abstract
        raise NotImplementedError

    def initial_castling(self) -> frozenset:
        return frozenset()

    def stalemate_caption(self, s) -> str:
        """Caption for a no-move, not-in-check position. Four of the six
        variants use this wording verbatim; Gliński (scored stalemate) and
        McCooey override it."""
        return f"Draw (stalemate — {self.NAME_OF[s.to_move]} has no move)"

    def castle_moves(self, s, out) -> None:
        """Append castling moves. Default: the variant has no castling."""

    def update_castling(self, rights: frozenset, frm, to, board,
                        new_board=None) -> frozenset:
        """Castling rights after this move. `board` is the PRE-move board and
        `new_board` the POST-move one.

        PREFER `new_board`. Two independent ports of this core expressed the
        rule on the pre-move board ("is the king/rook still home?") and both
        got it subtly wrong; one shipped a divergence that passed both the
        random differential AND the full selftest, and was only caught by an
        exhaustive sweep: a ROOK MOVING ONTO a rook's home cell whose right is
        live but whose rook has gone would RE-GRANT that right. Deriving the
        answer from the post-move occupant makes that class of bug impossible.
        """
        return rights

    def ep_after(self, s, frm, to, piece: str):
        """The `ep` value created by this move, or None. Default: no e.p."""
        return None

    # On-disk shape of `ep`. The default is [target, victim], which is what
    # Gliński/McCooey/Brusky/de Vasa already write. Shafran overrides.
    def ep_to_json(self, ep):
        return None if ep is None else [cell_str(ep[1][0]), cell_str(ep[0])]

    def ep_from_json(self, v):
        if not v:
            return None
        return (parse_cell(v[1]), (parse_cell(v[0]),))

    def castling_to_json(self, rights):
        return sorted(rights)

    def castling_from_json(self, v):
        return frozenset(v or ())

    # ---- board helpers ----------------------------------------------------
    def on(self, cell) -> bool:
        return cell in self.CELLS

    @property
    def num_players(self) -> int:
        return 2

    def current_player(self, s) -> int:
        return s.to_move

    def initial_state(self, options=None, rng=None):
        s = self.STATE(board=self.setup_board(), to_move=WHITE,
                       castling=self.initial_castling())
        # SEED the opening position into `reps`. Without this the start
        # position is only counted from its first RECURRENCE, so a threefold
        # repetition of it needs four occurrences instead of three.
        s.reps = {self.poskey(s.board, s.to_move, s.ep, s.castling): 1}
        return s

    # ---- move generation --------------------------------------------------
    def _pseudo(self, s) -> list:
        """Pseudo-legal moves as (frm, to, promo, ep_victim, castle).

        Sliders, leapers and the king are identical across the whole family;
        only pawns (and castling) are delegated to the variant.
        """
        out = []
        me = s.to_move
        board = s.board
        for cell, (owner, t) in board.items():
            if owner != me:
                continue
            if t == "P":
                self.pawn_moves(s, cell, out)
                continue
            q, r = cell
            if t in ("N", "K"):
                for dq, dr in (KNIGHT if t == "N" else ORTHO + DIAG):
                    tgt = (q + dq, r + dr)
                    if tgt in self.CELLS:
                        occ = board.get(tgt)
                        if occ is None or occ[0] != me:
                            out.append((cell, tgt, None, None, None))
            else:
                dirs = ORTHO if t == "R" else DIAG if t == "B" else ORTHO + DIAG
                for dq, dr in dirs:
                    cq, cr = q + dq, r + dr
                    while (cq, cr) in self.CELLS:
                        occ = board.get((cq, cr))
                        if occ is None:
                            out.append((cell, (cq, cr), None, None, None))
                        else:
                            if occ[0] != me:
                                out.append((cell, (cq, cr), None, None, None))
                            break
                        cq += dq
                        cr += dr
        self.castle_moves(s, out)
        return out

    def attacked(self, board: dict, cell, by: int) -> bool:
        """Is `cell` attacked by any piece of player `by`?

        NOTE this is a SEPARATE code path from move generation -- testing
        movegen does NOT test this (a QA agent found un-laming a piece here
        survived a full selftest). Variants that change how a pawn captures
        must reflect it in `pawn_attacks`, which this consults.
        """
        q, r = cell
        # REVERSE lookup, not a scan: ask which cells a pawn could attack this
        # one FROM. `attacked` runs once per pseudo-move in `_legal`, so an
        # O(board) scan here would dominate move generation.
        for src in self.pawn_attackers(by, cell):
            p = board.get(src)
            if p is not None and p[0] == by and p[1] == "P":
                return True
        for dq, dr in KNIGHT:
            p = board.get((q + dq, r + dr))
            if p is not None and p[0] == by and p[1] == "N":
                return True
        for dq, dr in ORTHO + DIAG:
            p = board.get((q + dq, r + dr))
            if p is not None and p[0] == by and p[1] == "K":
                return True
        for dirs, letters in ((ORTHO, ("R", "Q")), (DIAG, ("B", "Q"))):
            for dq, dr in dirs:
                cq, cr = q + dq, r + dr
                while (cq, cr) in self.CELLS:
                    p = board.get((cq, cr))
                    if p is not None:
                        if p[0] == by and p[1] in letters:
                            return True
                        break
                    cq += dq
                    cr += dr
        return False

    def king_cell(self, board: dict, player: int):
        for c, (o, t) in board.items():
            if o == player and t == "K":
                return c
        return None

    def in_check(self, board: dict, player: int) -> bool:
        k = self.king_cell(board, player)
        return k is not None and self.attacked(board, k, 1 - player)

    def apply_to_board(self, board: dict, frm, to, promo, ep_victim, castle,
                       mover: int) -> dict:
        b = dict(board)
        piece = b.pop(frm)
        if ep_victim is not None:
            b.pop(ep_victim, None)
        b[to] = (mover, promo) if promo else piece
        if castle is not None:
            rf, rt = castle
            b[rt] = b.pop(rf)
        return b

    def _legal(self, s) -> list:
        """Pseudo-legal moves filtered by "does not leave my king in check".

        Memoised on the state, because `_draw_reason` consults it (only once a
        counter has fired) and `legal_moves`/`is_terminal`/`returns` may each
        ask for it in the same tick.
        """
        cached = getattr(s, "_legal_cache", None)
        if cached is not None:
            return cached
        me = s.to_move
        out = []
        for frm, to, promo, ep_victim, castle in self._pseudo(s):
            nb = self.apply_to_board(s.board, frm, to, promo, ep_victim,
                                     castle, me)
            if not self.in_check(nb, me):
                out.append((frm, to, promo, ep_victim, castle))
        object.__setattr__(s, "_legal_cache", out)
        return out

    @staticmethod
    def _mstr(frm, to, promo) -> str:
        return f"{cell_str(frm)}>{cell_str(to)}" + (f"={promo}" if promo else "")

    # ---- draws / terminal -------------------------------------------------
    def _draw_reason(self, s) -> Optional[str]:
        """Why this position is a draw by a COUNTER, or None.

        A DECISIVE RESULT OUTRANKS THE COUNTERS. Chess ends the instant the
        king is mated (FIDE 5.1.1), so a mate delivered on the 100th reversible
        ply is a win, not a 50-move draw. This exact defect shipped in eight
        independent places in this codebase before the shared core existed --
        centralising it here is a large part of why this module is worth having.

        Gating on "the side to move has NO legal move" rather than on checkmate
        specifically also covers Gliński, whose stalemate is a SCORED 3/4-1/4
        result that must likewise survive a fired counter. For variants where
        stalemate is an ordinary draw the two formulations are equivalent.
        """
        reason = None
        if s.halfmove >= 100:
            reason = "50-move rule"
        elif s.reps and max(s.reps.values()) >= 3:
            reason = "threefold repetition"
        elif s.ply >= self.PLY_CAP:
            reason = "move limit"
        if reason is None:
            return None
        return None if not self._legal(s) else reason

    def legal_moves(self, s) -> list:
        if self._draw_reason(s) is not None:
            return []
        return [self._mstr(f, t, p) for f, t, p, _, _ in self._legal(s)]

    def is_terminal(self, s) -> bool:
        if self._draw_reason(s) is not None:
            return True
        return not self._legal(s)

    def returns(self, s) -> list:
        if self._draw_reason(s) is not None:
            return [0.0, 0.0]
        if self._legal(s):
            return [0.0, 0.0]
        loser = s.to_move
        if self.in_check(s.board, loser):
            return [-1.0, 1.0] if loser == WHITE else [1.0, -1.0]
        if self.STALEMATE_SCORED:
            # 3/4 - 1/4 in chess points maps to +0.5 / -0.5 on this engine's
            # +1/0/-1 payoff scale (p points -> 2p-1), so
            # win > stalemate-win > draw > stalemated > loss orders correctly.
            return [-0.5, 0.5] if loser == WHITE else [0.5, -0.5]
        return [0.0, 0.0]

    # ---- applying a move --------------------------------------------------
    def _find(self, s, move: str):
        for m in self._legal(s):
            if self._mstr(m[0], m[1], m[2]) == move:
                return m
        raise ValueError(f"illegal move {move!r}")

    def poskey(self, board: dict, to_move: int, ep, castling) -> str:
        items = sorted((q, r, o, t) for (q, r), (o, t) in board.items())
        ep_s = cell_str(ep[0]) + "|" + ",".join(cell_str(c) for c in ep[1]) if ep else "-"
        return (f"{to_move}|{ep_s}|{'.'.join(sorted(map(str, castling)))}|"
                + ";".join(f"{q},{r},{o},{t}" for q, r, o, t in items))

    def apply_move(self, s, move: str, rng=None):
        frm, to, promo, ep_victim, castle = self._find(s, move)
        mover = s.to_move
        piece = s.board[frm][1]
        captured = to in s.board or ep_victim is not None
        board = self.apply_to_board(s.board, frm, to, promo, ep_victim, castle,
                                    mover)
        irreversible = captured or piece == "P"
        rights = self.update_castling(s.castling, frm, to, s.board, board)
        ep = self.ep_after(s, frm, to, piece)
        halfmove = 0 if irreversible else s.halfmove + 1
        reps = {} if irreversible or rights != s.castling else dict(s.reps)
        key = self.poskey(board, 1 - mover, ep, rights)
        reps[key] = reps.get(key, 0) + 1
        return self.STATE(board=board, to_move=1 - mover, ep=ep,
                          castling=rights, halfmove=halfmove, ply=s.ply + 1,
                          reps=reps, last=(frm, to))

    # ---- serialisation ----------------------------------------------------
    def serialize(self, s) -> dict:
        return {
            "board": {cell_str(k): [v[0], v[1]] for k, v in s.board.items()},
            "to_move": s.to_move,
            "ep": self.ep_to_json(s.ep),
            "castling": self.castling_to_json(s.castling),
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
            "last": [cell_str(s.last[0]), cell_str(s.last[1])] if s.last else None,
        }

    def deserialize(self, d: dict):
        last = d.get("last")
        return self.STATE(
            board={parse_cell(k): (v[0], v[1]) for k, v in d["board"].items()},
            to_move=d["to_move"],
            ep=self.ep_from_json(d.get("ep")),
            castling=self.castling_from_json(d.get("castling")),
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps") or {}),
            last=(parse_cell(last[0]), parse_cell(last[1])) if last else None,
        )

    # ---- presentation -----------------------------------------------------
    PIECE_NAMES = {"K": "K", "Q": "Q", "R": "R", "B": "B", "N": "N", "P": ""}

    # Move-log notation is USER-VISIBLE and differs across the family, so it is
    # hooked rather than unified: Brusky annotates check, the others do not, and
    # Shafran/de Vasa have castling notation. Defaults reproduce the majority.
    CHECK_MARKS = False        # append "+"/"#"; Brusky sets True

    def castle_notation(self, s, frm, to, castle) -> Optional[str]:
        """Variant's castling notation for this move, or None. Default: none."""
        return None

    def describe_move(self, s, move: str) -> str:
        frm, to, promo, ep_victim, castle = self._find(s, move)
        if castle is not None:
            note = self.castle_notation(s, frm, to, castle)
            if note is not None:
                return note
        piece = s.board[frm][1]
        cap = "x" if (to in s.board or ep_victim is not None) else "-"
        txt = (self.PIECE_NAMES.get(piece, piece) + self.cell_name(frm) + cap
               + self.cell_name(to))
        if promo:
            txt += "=" + promo
        if ep_victim is not None:
            txt += " e.p."
        if self.CHECK_MARKS:
            nxt = self.apply_move(s, move)
            if self.in_check(nxt.board, nxt.to_move):
                txt += "#" if not self._legal(nxt) else "+"
        return txt

    def render(self, s, perspective=None) -> dict:
        pieces = [{"cell": cell_str(c), "owner": o, "label": t}
                  for c, (o, t) in sorted(s.board.items())]
        highlights = ([{"cell": cell_str(s.last[0]), "kind": "last-move"},
                       {"cell": cell_str(s.last[1]), "kind": "last-move"}]
                      if s.last else [])
        reason = self._draw_reason(s)
        if reason is not None:
            caption = f"Draw ({reason})"
        elif not self._legal(s):
            if self.in_check(s.board, s.to_move):
                caption = f"{self.NAME_OF[1 - s.to_move]} wins (checkmate)"
            else:
                caption = self.stalemate_caption(s)
        else:
            check = " (check)" if self.in_check(s.board, s.to_move) else ""
            caption = f"{self.NAME_OF[s.to_move]} to move{check}"
        return {
            "board": self.board_spec(s),
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "pieceset": "chess",
        }

    def board_spec(self, s) -> dict:            # pragma: no cover - abstract
        """The RenderSpec `board` block. Variants differ in shape/orientation
        and in their three-colour tinting, so this is theirs to supply."""
        raise NotImplementedError

    def heuristic(self, s) -> list:
        """Tanh material balance, as a LIST of per-player payoffs.

        It MUST be a list -- a bare float raises `TypeError: 'float' object is
        not subscriptable` in MCTS back-propagation, and only when the rollout
        cutoff is reached (so a short game hides the bug). See SPEC.md.
        """
        import math
        bal = 0.0
        for _, (o, t) in s.board.items():
            v = PIECE_VALUES.get(t, 3.0)
            bal += v if o == WHITE else -v
        w = math.tanh(bal / 10.0)
        return [w, -w]
