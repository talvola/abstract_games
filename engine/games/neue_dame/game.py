"""Neue Dame ("New Draughts") -- Heinrich Adolf Schmidt, Hildesheim 1904.

One of the very first *stacking* games (only Bashni 1875, Towers of Hanoi 1883
and the Diplomaten-Spiel 1895 are older; Lasca is seven years younger).  Played
on the 32 dark squares of an 8x8 board, 12 men a side on the first three rows.

Captured pieces are not removed: the **top** piece of the jumped column is tucked
under the **bottom** of the capturing column, forming a tower ("Turm").  A column
is owned by whoever's piece is on top and moves as that piece.

What makes Neue Dame its own game (and not Bashni/Lasca) is the **Dame** (Lady)
and the way her captures are constrained:

  * a man steps and captures **forward only**, by the short leap (Anglo-American
    draughts);
  * a Dame is a **flying king** (International draughts) -- but
      - **a Dame's capture takes precedence over a man's**,
      - **the nearest capturable piece must be taken first**, and
      - **the Dame must stop on the square immediately behind the LAST piece
        taken** (intermediate landings inside a chain are free);
  * the game ends when one player owns every column (or cannot move), and the
    winner scores **one point per Dame on the board** (1/2 if none exists).

Rules source: Ralf Gering, "Neue Dame: A forgotten stacking game", *Abstract
Games* 18 (Winter/Spring 2020), pp. 30-31, plus the four composed problems and
their solutions printed on p. 1 of the same issue -- see rules.md and selftest.py.

Squares are "c,r" on the 8x8 grid (a1 = "0,0"); a move is a ">"-separated path of
squares (a simple step, or the landing squares of a jump chain).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

SIZE = 8
GREEN, BLACK = 0, 1                 # Green starts at the bottom and plays up
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
NAMES = {GREEN: "Green", BLACK: "Black"}

# --- termination ------------------------------------------------------------
# Neue Dame recycles material (a captured piece stays on the board, buried), so
# play can in principle cycle.  Two counters bound it; see rules.md.
NO_PROGRESS_DRAW = 100      # plies with no capture and no promotion -> draw
PLY_CAP = 1200              # hard backstop (never reached in measured play)


def on_board(c, r):
    """A playing square: on the 8x8 grid and dark (a1 dark, h1 light)."""
    return 0 <= c < SIZE and 0 <= r < SIZE and (c + r) % 2 == 0


def fwd(player):
    return 1 if player == GREEN else -1


def last_rank(player):
    return SIZE - 1 if player == GREEN else 0


def cid(sq):
    return f"{sq[0]},{sq[1]}"


def parse_cid(s):
    c, r = s.split(",")
    return int(c), int(r)


def alg(sq):
    """(0,0) -> 'a1'  (the magazine uses chess notation)."""
    return "abcdefgh"[sq[0]] + str(sq[1] + 1)


def from_alg(s):
    return "abcdefgh".index(s[0]), int(s[1]) - 1


# A piece is (owner, is_dame); a column is a tuple of pieces, BOTTOM -> TOP.
def top(col):
    return col[-1]


def owner(col):
    return col[-1][0]


def is_dame(col):
    return col[-1][1]


@dataclass
class NState:
    board: dict = field(default_factory=dict)     # (c,r) -> column tuple
    to_move: int = GREEN
    since: int = 0                                # plies since capture/promotion
    ply: int = 0
    reps: dict = field(default_factory=dict)
    winner: object = None


class NeueDame(Game):
    name = "Neue Dame"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        board = {}
        for r in range(SIZE):
            for c in range(SIZE):
                if not on_board(c, r):
                    continue
                if r <= 2:
                    board[(c, r)] = ((GREEN, False),)
                elif r >= 5:
                    board[(c, r)] = ((BLACK, False),)
        st = NState(board=board, to_move=GREEN)
        st.reps = {self._key(st): 1}
        return st

    def current_player(self, state):
        return state.to_move

    # ---- capture generation ------------------------------------------------
    def _candidates(self, board, sq, col, player, jumped):
        """Legal single jumps from `sq`: [(over, dir, [landing squares]), ...].

        A man leaps an *adjacent* enemy column forward.  A Dame flies: in each
        direction the first occupied square is the only one she can take, and
        by the rule "the nearest piece must be captured first" only the closest
        such piece(s) may be taken.  A square already jumped in this move may
        not be jumped again (and still blocks the diagonal).
        """
        out = []
        if not is_dame(col):
            f = fwd(player)
            for dc in (1, -1):
                d = (dc, f)
                over = (sq[0] + d[0], sq[1] + d[1])
                land = (sq[0] + 2 * d[0], sq[1] + 2 * d[1])
                if (on_board(*land) and land not in board and over in board
                        and over not in jumped and owner(board[over]) != player):
                    out.append((over, d, [land]))
            return out
        best = None
        for d in DIAG:
            c, r = sq[0] + d[0], sq[1] + d[1]
            dist = 1
            while on_board(c, r) and (c, r) not in board:
                c += d[0]
                r += d[1]
                dist += 1
            if not on_board(c, r):
                continue                       # nothing to jump in this direction
            over = (c, r)
            if owner(board[over]) == player or over in jumped:
                continue                       # blocked
            lands = []
            c, r = over[0] + d[0], over[1] + d[1]
            while on_board(c, r) and (c, r) not in board:
                lands.append((c, r))
                c += d[0]
                r += d[1]
            if not lands:
                continue
            if best is None or dist < best:
                best = dist
                out = [(over, d, lands)]
            elif dist == best:
                out.append((over, d, lands))
        return out

    def _capture(self, board, sq, col, over, land):
        """Take the top of the jumped column; tuck it under the mover's bottom."""
        nb = dict(board)
        del nb[sq]
        ocol = nb[over]
        rest = ocol[:-1]
        if rest:
            nb[over] = rest
        else:
            del nb[over]
        ncol = (top(ocol),) + col
        nb[land] = ncol
        return nb, ncol

    def _chains(self, board, sq, col, player, jumped):
        """Complete capture sequences from `sq`: lists of landing squares.

        "Captures must be continued as long as possible", so a sequence may only
        stop where no further capture exists.  A Dame must finish on the square
        immediately behind the last piece she took; the landings *inside* a chain
        are free (Puzzle 4 move 6, Puzzle 3 move 5).  A man that reaches the far
        row while capturing is crowned and the move ends there (Anglo-American
        crowning; Puzzle 1 move 3).
        """
        cands = self._candidates(board, sq, col, player, jumped)
        if not cands:
            return []
        out = []
        promo_row = last_rank(player)
        for (over, d, lands) in cands:
            behind = (over[0] + d[0], over[1] + d[1])
            for land in lands:
                nb, ncol = self._capture(board, sq, col, over, land)
                if not top(ncol)[1] and land[1] == promo_row:
                    out.append([land])                     # crowned: move ends
                    continue
                tails = self._chains(nb, land, ncol, player, jumped | {over})
                if tails:
                    for t in tails:
                        out.append([land] + t)
                elif land == behind:
                    out.append([land])
        return out

    def _all_captures(self, board, player):
        """All capture moves, with the Dame-takes-precedence rule applied."""
        dame, man = [], []
        for sq, col in board.items():
            if owner(col) != player:
                continue
            bucket = dame if is_dame(col) else man
            for path in self._chains(board, sq, col, player, frozenset()):
                bucket.append([sq] + path)
        return dame if dame else man

    # ---- simple (non-capturing) moves --------------------------------------
    def _simple_moves(self, board, player):
        out = []
        for sq, col in board.items():
            if owner(col) != player:
                continue
            if is_dame(col):                    # flying Dame: any distance
                for d in DIAG:
                    c, r = sq[0] + d[0], sq[1] + d[1]
                    while on_board(c, r) and (c, r) not in board:
                        out.append([sq, (c, r)])
                        c += d[0]
                        r += d[1]
            else:                               # man: one step forward
                f = fwd(player)
                for dc in (1, -1):
                    to = (sq[0] + dc, sq[1] + f)
                    if on_board(*to) and to not in board:
                        out.append([sq, to])
        return out

    def _moves(self, board, player):
        caps = self._all_captures(board, player)
        return caps if caps else self._simple_moves(board, player)

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        return [">".join(cid(sq) for sq in p)
                for p in self._moves(state.board, state.to_move)]

    # ---- apply --------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        pts = [parse_cid(s) for s in move.split(">")]
        board = dict(state.board)
        player = state.to_move
        col = board.pop(pts[0])
        captured = False
        for i in range(1, len(pts)):
            frm, to = pts[i - 1], pts[i]
            d = (1 if to[0] > frm[0] else -1, 1 if to[1] > frm[1] else -1)
            over = None
            c, r = frm[0] + d[0], frm[1] + d[1]
            while (c, r) != to:
                if (c, r) in board:
                    over = (c, r)
                    break
                c += d[0]
                r += d[1]
            if over is not None:                       # this leg is a jump
                ocol = board[over]
                col = (top(ocol),) + col
                rest = ocol[:-1]
                if rest:
                    board[over] = rest
                else:
                    del board[over]
                captured = True
        landing = pts[-1]
        promoted = False
        t_owner, t_dame = top(col)
        if not t_dame and t_owner == player and landing[1] == last_rank(player):
            col = col[:-1] + ((player, True),)
            promoted = True
        board[landing] = col

        since = 0 if (captured or promoted) else state.since + 1
        ns = NState(board=board, to_move=1 - player, since=since,
                    ply=state.ply + 1, reps=dict(state.reps))
        key = self._key(ns)
        ns.reps[key] = ns.reps.get(key, 0) + 1
        # A decisive result OUTRANKS the draw counters: the win is settled first
        # and never re-examined, so a blockade/wipe-out on the 100th quiet ply
        # (or at the ply cap, or in a thrice-repeated position) still scores.
        if not self._moves(ns.board, ns.to_move):
            ns.winner = player
        return ns

    # ---- terminal ------------------------------------------------------------
    def _draw(self, state):
        return (state.winner is None
                and (state.since >= NO_PROGRESS_DRAW
                     or state.reps.get(self._key(state), 0) >= 3
                     or state.ply >= PLY_CAP))

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    def dames(self, state):
        """Ladies on the board -- buried ones count; this is the winner's score."""
        return sum(1 for col in state.board.values() for (_o, k) in col if k)

    def score(self, state):
        """The winner's point score: one per Dame, or 1/2 if none was promoted."""
        if state.winner is None:
            return 0.0
        n = self.dames(state)
        return float(n) if n else 0.5

    # ---- MCTS eval -----------------------------------------------------------
    def heuristic(self, state):
        """Payoffs (a LIST, one per seat) from how close each side's pieces are
        to the top of their column -- a buried piece is nearly worthless, a top
        piece is a live column."""
        val = [0.0, 0.0]
        for col in state.board.values():
            for depth, (o, k) in enumerate(reversed(col)):
                val[o] += (0.55 ** depth) * (1.6 if k else 1.0)
        tot = val[0] + val[1]
        if tot <= 0:
            return [0.0, 0.0]
        e = max(-1.0, min(1.0, 1.8 * (val[0] - val[1]) / tot))
        return [e, -e]

    # ---- keys / serialise -----------------------------------------------------
    def _col_str(self, col):
        return "".join(("GB"[o] if k else "gb"[o]) for (o, k) in col)

    def _parse_col(self, s):
        return tuple((0 if ch in "gG" else 1, ch.isupper()) for ch in s)

    def _key(self, state):
        b = "|".join(f"{c},{r}:{self._col_str(state.board[(c, r)])}"
                     for r in range(SIZE) for c in range(SIZE) if (c, r) in state.board)
        return f"{b}#{state.to_move}"

    def serialize(self, state):
        return {
            "board": {cid(sq): self._col_str(col) for sq, col in state.board.items()},
            "to_move": state.to_move, "since": state.since, "ply": state.ply,
            "reps": dict(state.reps), "winner": state.winner,
        }

    def deserialize(self, d):
        return NState(
            board={parse_cid(k): self._parse_col(v) for k, v in d["board"].items()},
            to_move=d["to_move"], since=d.get("since", 0), ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})), winner=d.get("winner"))

    # ---- presentation ---------------------------------------------------------
    def describe_move(self, state, move):
        """The magazine's own notation: 'a1-b2', 'c3xa1*D', 'c3xe1xh4xd8'.

        A leg is a jump iff a column stands strictly between its two squares --
        a Dame's quiet slide also spans several squares, so distance alone is
        NOT the test.
        """
        pts = [parse_cid(s) for s in move.split(">")]
        frm, to = pts[0], pts[1]
        d = (1 if to[0] > frm[0] else -1, 1 if to[1] > frm[1] else -1)
        jump = False
        c, r = frm[0] + d[0], frm[1] + d[1]
        while (c, r) != to:
            if (c, r) in state.board:
                jump = True
                break
            c += d[0]
            r += d[1]
        s = ("x" if jump else "-").join(alg(p) for p in pts)
        player = state.to_move
        col = state.board.get(pts[0])
        if col is not None and not is_dame(col) and pts[-1][1] == last_rank(player):
            s += "*D"
        return s

    def render(self, state, perspective=None):
        pieces = []
        for sq, col in state.board.items():
            pieces.append({
                "cell": cid(sq),
                "owner": owner(col),
                "stack": [o for (o, _k) in col],        # bottom -> top
                "label": "D" if is_dame(col) else "",
            })
        if state.winner is not None:
            pts = self.score(state)
            pts = int(pts) if pts == int(pts) else pts
            cap = f"{NAMES[state.winner]} wins ({pts} point{'' if pts == 1 else 's'})"
        elif self._draw(state):
            cap = "Draw (0-0)"
        else:
            must = self._all_captures(state.board, state.to_move)
            cap = f"{NAMES[state.to_move]} to move" + (" (must capture)" if must else "")
        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
