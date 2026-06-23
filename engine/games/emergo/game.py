"""Emergo (Christian Freeling & Ed van Zon, 1986) -- a stacking draughts game.

Played on the 41 dark squares of a 9x9 board. Both players begin with all
**twelve men off the board** and ENTER them. There are **no kings**: every piece
-- a lone man or a column you control -- moves and captures one step in **any of
the four diagonal directions**. You CAPTURE by jumping an adjacent enemy column
to the empty square beyond; the jumped column's **top** man is removed and tucked
**underneath** your moving column as a prisoner (your column grows by one). The
rest of the jumped column stays where it is, now controlled by whoever is newly on
top. Captures are **compulsory** and a capturing piece must take the **maximum**
number of men available (chains, may revisit squares / re-jump a column, no 180
degrees immediate reversal). You WIN by capturing all of the opponent's men, or by
leaving the opponent with no legal move.

This reuses the platform's Lasca stacking/column model (piece.stack tower glyph),
but is a genuinely DISTINCT game -- see rules.md ("How Emergo differs from
Lasca & Bashni"): the off-board ENTRY phase, the no-kings omnidirectional move,
maximum (not merely compulsory) capture, and the capture-all win.

Board model: cell ids are "c,r" on a 9x9 grid; a dark square has (c+r) even.
The diagonal Emergo board is represented here as those dark squares, with moves
running along the grid diagonals (exactly as Lasca/checkers). A simple move /
jump chain is a ">"-path of squares; entering a man is the drop move "m@c,r".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 9
WHITE, BLACK = 0, 1
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
MEN_PER_PLAYER = 12
CENTER = (SIZE // 2, SIZE // 2)             # (4,4): banned for White's first entry
NO_PROGRESS_DRAW = 60       # plies with neither a capture nor an entry -> draw
PLY_CAP = 600


def _on(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE and (c + r) % 2 == 0


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _top(col):
    return col[-1]


def _controller(col):
    return col[-1]


@dataclass
class EState:
    board: dict = field(default_factory=dict)        # (c,r) -> column tuple, bottom->top owners
    hands: list = field(default_factory=lambda: [MEN_PER_PLAYER, MEN_PER_PLAYER])
    to_move: int = WHITE
    since: int = 0                                    # plies since a capture or an entry
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class Emergo(Game):
    uid = "emergo"
    name = "Emergo"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        st = EState(board={}, hands=[MEN_PER_PLAYER, MEN_PER_PLAYER], to_move=WHITE)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- capture generation (maximum capture) ------------------------------
    def _capture_paths(self, board, sq, col, player):
        """Yield jump chains [sq, land1, land2, ...] from `sq`. `came_from` not
        needed as state: 180 reversal is forbidden via the no-immediate-reverse
        check using the previous direction, handled by the caller wrapper."""
        return self._cap_rec(board, sq, col, player, None)

    def _cap_rec(self, board, sq, col, player, last_dir):
        found = False
        for (dc, dr) in DIAG:
            if last_dir is not None and (dc, dr) == (-last_dir[0], -last_dir[1]):
                continue                              # no 180-degree immediate reversal
            over = (sq[0] + dc, sq[1] + dr)
            land = (sq[0] + 2 * dc, sq[1] + 2 * dr)
            if not _on(*land) or land in board or over not in board:
                continue
            ocol = board[over]
            if _controller(ocol) == player:
                continue                              # can't jump your own piece
            nb = dict(board)
            prisoner = _top(ocol)
            rest = ocol[:-1]
            if rest:
                nb[over] = rest
            else:
                del nb[over]
            ncol = (prisoner,) + col                  # captured top man tucked UNDER
            nb[land] = ncol
            found = True
            tails = list(self._cap_rec(nb, land, ncol, player, (dc, dr)))
            if tails:
                for t in tails:
                    yield [sq] + t
            else:
                yield [sq, land]
        if not found:
            return

    def _all_captures(self, board, player):
        out = []
        for sq, col in board.items():
            if _controller(col) != player:
                continue
            for path in self._capture_paths(board, sq, col, player):
                out.append(path)
        return out

    def _max_captures(self, board, player):
        caps = self._all_captures(board, player)
        if not caps:
            return []
        best = max(len(p) for p in caps)              # path length == jumps + 1
        return [p for p in caps if len(p) == best]

    # ---- simple (non-capturing) moves --------------------------------------
    def _simple_moves(self, board, player):
        out = []
        for sq, col in board.items():
            if _controller(col) != player:
                continue
            for (dc, dr) in DIAG:
                to = (sq[0] + dc, sq[1] + dr)
                if _on(*to) and to not in board:
                    out.append([sq, to])
        return out

    # ---- entering moves ----------------------------------------------------
    def _legal_entries(self, state):
        """Entry drops, honouring the no-force-a-capture and first-entry-center
        restrictions, and the 'enter remaining men as one column' end-of-entry
        rule."""
        player = state.to_move
        opp = 1 - player
        if state.hands[player] <= 0:
            return []
        empties = [(c, r) for r in range(SIZE) for c in range(SIZE)
                   if _on(c, r) and (c, r) not in state.board]
        first_entry = (state.hands[WHITE] == MEN_PER_PLAYER
                       and state.hands[BLACK] == MEN_PER_PLAYER and player == WHITE)
        out = []
        for cell in empties:
            if first_entry and cell == CENTER:
                continue                              # White may not open in the centre
            # Reject an entry that would force the opponent into a capture.
            # (Captures take precedence over entering, so legal_moves only reaches
            # here when the entering player has no capture of his own -- the
            # "unless already obliged to capture" clause never applies.)
            nb = dict(state.board)
            nb[cell] = (player,)
            if self._max_captures(nb, opp):
                continue                              # would force opponent to capture
            out.append(cell)
        return out

    # ---- public move list --------------------------------------------------
    def legal_moves(self, state):
        if state.winner is not None or self._draw(state):
            return []
        player = state.to_move
        # 1) Capture is obligatory and takes precedence over entering / moving.
        caps = self._max_captures(state.board, player)
        if caps:
            return [">".join(f"{c},{r}" for (c, r) in p) for p in caps]
        out = []
        # 2) Entering a man (if any remain in hand).
        if state.hands[player] > 0:
            if state.hands[1 - player] == 0:
                # Opponent has placed all twelve; this player must now enter ALL
                # remaining men, stacked as a single column, on a vacant square.
                # (No square may force an opponent capture; center rule no longer
                # applies -- it only constrains White's very first entry.)
                for (c, r) in self._stack_entry_cells(state):
                    out.append(f"M@{c},{r}")
            else:
                for (c, r) in self._legal_entries(state):
                    out.append(f"m@{c},{r}")
        # 3) Otherwise / additionally, a normal move (a man or controlled column
        #    steps one square diagonally). During the entry phase a player MAY
        #    move instead of entering.
        for p in self._simple_moves(state.board, player):
            out.append(">".join(f"{c},{r}" for (c, r) in p))
        return out

    def _stack_entry_cells(self, state):
        player = state.to_move
        opp = 1 - player
        empties = [(c, r) for r in range(SIZE) for c in range(SIZE)
                   if _on(c, r) and (c, r) not in state.board]
        out = []
        for cell in empties:
            nb = dict(state.board)
            nb[cell] = tuple([player] * state.hands[player])
            if self._max_captures(nb, opp):
                continue
            out.append(cell)
        if not out:
            # no non-forcing square -> allow any empty (avoid a dead end)
            out = empties
        return out

    # ---- apply -------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        board = dict(state.board)
        hands = list(state.hands)
        player = state.to_move
        captured = False
        entered = False

        if "@" in move:
            tag, cell_s = move.split("@")
            cell = _cell(cell_s)
            if tag == "M":                            # stacked final entry
                board[cell] = tuple([player] * hands[player])
                hands[player] = 0
            else:                                     # single man
                board[cell] = (player,)
                hands[player] -= 1
            entered = True
        else:
            pts = [_cell(s) for s in move.split(">")]
            col = board.pop(pts[0])
            for i in range(1, len(pts)):
                frm, to = pts[i - 1], pts[i]
                if abs(to[0] - frm[0]) == 2:          # a jump
                    over = ((frm[0] + to[0]) // 2, (frm[1] + to[1]) // 2)
                    ocol = board[over]
                    col = (_top(ocol),) + col         # tuck prisoner UNDER
                    rest = ocol[:-1]
                    if rest:
                        board[over] = rest
                    else:
                        del board[over]
                    captured = True
            board[pts[-1]] = col

        since = 0 if (captured or entered) else state.since + 1
        ns = EState(board=board, hands=hands, to_move=1 - player,
                    since=since, ply=state.ply + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1

        # Win-as-event: capture-all, or opponent has no legal move.
        opp = 1 - player
        opp_has_column = any(_controller(c) == opp for c in board.values())
        opp_has_men = opp_has_column or hands[opp] > 0
        if not opp_has_men:
            ns.winner = player                        # all opponent men captured
        elif not self._draw(ns) and not self.legal_moves(ns):
            ns.winner = player                        # opponent has no legal move
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.ply >= PLY_CAP
                     or state.since >= NO_PROGRESS_DRAW
                     or state.reps.get(self._key(state), 0) >= 3))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- keys / serialise --------------------------------------------------
    def _col_str(self, col):
        return "".join("wb"[o] for o in col)

    def _parse_col(self, s):
        return tuple(0 if ch == "w" else 1 for ch in s)

    def _key(self, state):
        b = "|".join(f"{c},{r}:{self._col_str(state.board[(c, r)])}"
                     for r in range(SIZE) for c in range(SIZE) if (c, r) in state.board)
        return f"{b}#{state.to_move}#{state.hands[0]},{state.hands[1]}"

    def serialize(self, state):
        return {
            "board": {f"{c},{r}": self._col_str(col) for (c, r), col in state.board.items()},
            "hands": list(state.hands),
            "to_move": state.to_move, "since": state.since, "ply": state.ply,
            "reps": dict(state.reps), "winner": state.winner,
        }

    def deserialize(self, d):
        return EState(
            board={_cell(k): self._parse_col(v) for k, v in d["board"].items()},
            hands=list(d.get("hands", [MEN_PER_PLAYER, MEN_PER_PLAYER])),
            to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if "@" in move:
            tag, cell_s = move.split("@")
            return ("stack" if tag == "M" else "enter") + " " + cell_s
        pts = move.split(">")
        jump = any(abs(_cell(pts[i])[0] - _cell(pts[i - 1])[0]) == 2
                   for i in range(1, len(pts)))
        return ("x" if jump else "-").join(pts)

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), col in state.board.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": _top(col),
                "stack": list(col),                   # bottom -> top owners
                "label": str(len(col)) if len(col) > 1 else "",
            })
        names = {WHITE: "White", BLACK: "Black"}
        reserve = {}
        for seat in (WHITE, BLACK):
            if state.hands[seat] > 0:
                reserve[seat] = {"m": state.hands[seat]}
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        else:
            must = bool(self._max_captures(state.board, state.to_move))
            phase = "" if state.hands[state.to_move] == 0 else " (entering)"
            cap = f"{names[state.to_move]} to move{phase}" + (" (must capture)" if must else "")
        spec = {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
        if reserve:
            spec["reserve"] = reserve
        return spec
