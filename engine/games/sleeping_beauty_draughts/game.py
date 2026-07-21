"""Sleeping Beauty Draughts (Dornröschendame) — Ralf Gering, 1986.

A Checkers (English draughts) variant on the 32 dark squares of an 8x8 board,
12 men per side, White moving first.  Its defining twist is the ONE-LADY rule
and the "sleeping beauty": a player may never hold two ladies (kings) at once.

Rules as implemented (source: Abstract Games magazine, Issue 14, Summer 2003,
"Sleeping Beauty Draughts" by Ralf Gering — the authoritative ruleset; see
rules.md for line-by-line quotes):

MEN
  * Move one square diagonally FORWARD to an empty square.
  * Capture an adjacent enemy MAN by a short leap FORWARD; capture an adjacent
    enemy LADY by a short leap BACKWARD.  A man may chain several leaps.
  * Reaching the opponent's back rank promotes: to a LADY if the player has no
    lady, otherwise to a frozen SLEEPING BEAUTY.  Promotion ALWAYS ends the move
    (a capture chain stops the instant a man reaches the back rank).

LADIES  (move one square any diagonal, like the English-draughts king)
  * Capture two ways, which may NOT be combined in one move:
      - by REPLACEMENT (Ferz-style): step onto an adjacent enemy square, taking
        exactly one piece.  Replacement is NOT compulsory.
      - by JUMPING (king-style short leap, any direction, chainable).  Jumping
        IS compulsory.
  * Jumping takes precedence over replacement, EXCEPT the Royal Privilege: a lady
    able to capture the opponent's LADY may choose replacement instead.  Majority
    still binds among jumps (you must take the greatest number).

SLEEPING BEAUTY  (a man promoted while the player already had a lady)
  * May not move, may not capture, and may NOT be captured (nor jumped over).
  * A beauty only ever sits on the promotion rank (rank 8 for White, rank 1 for
    Black), so its owner is fixed by that rank.

WAKING  (+ jump of joy)
  * When a player has lost his lady, he MUST wake a sleeping beauty (if he has
    one): she becomes his lady.  This does not count as a move — he then moves
    her.  Interpretation: in this engine a wake-turn's legal moves are exactly the
    moves of a woken beauty (you must wake and move her); if several beauties
    exist you choose which by which one you move.
  * A just-woken lady may make a JUMP OF JOY: move two squares diagonally in a
    straight line over a crossed square that is (1) vacant and (2) not guarded by
    the opponent.  No capture during a jump of joy; only available on the wake
    turn, and only if no capture is forced.

ANTI-LOOP  (ladies-only sequences)
  * In a continuous run of only-lady simple moves, once the full board position
    has repeated once, no move may recreate a position already seen in the run.
    This makes lady endgames finite (the game "cannot end in a draw").

END / SCORE
  * You lose when you have no legal move (all pieces captured or blocked).  The
    winner's points = the TOTAL number of pieces left on the board (men, ladies
    and beauties of both colours count equally); the loser scores zero.  A hard
    ply cap yields an honest DRAW as a termination backstop (never reached in
    normal play).

Coordinates: algebraic a1=(0,0)…h8=(7,7); White (player 0) plays up the board,
Black (player 1) down.  Playable dark squares are (c+r) even.  Piece kinds:
"m" man, "l" lady, "s" sleeping beauty.  Moves are `>`-separated cell paths; a
1-square step onto an enemy square is a replacement capture; a 2-square step is a
leap (jump capture, or — only on a wake turn over an empty square — a jump of joy).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 8
PLY_CAP = 600
DIAGS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


@dataclass
class SBState:
    board: dict = field(default_factory=dict)   # (c, r) -> (player, "m"|"l"|"s")
    to_move: int = 0
    ply: int = 0
    hist: tuple = ()      # position keys of the current ladies-only run
    rep: bool = False     # a full-board position has repeated in this run


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _back_rank(pl):
    return N - 1 if pl == 0 else 0


def _man_fwd(pl):
    return [(1, 1), (-1, 1)] if pl == 0 else [(1, -1), (-1, -1)]


def _man_back(pl):
    return [(1, -1), (-1, -1)] if pl == 0 else [(1, 1), (-1, 1)]


def _start_board():
    b = {}
    for r in (0, 1, 2):
        for c in range(N):
            if (c + r) % 2 == 0:
                b[(c, r)] = (0, "m")
    for r in (5, 6, 7):
        for c in range(N):
            if (c + r) % 2 == 0:
                b[(c, r)] = (1, "m")
    return b


def _num_ladies(board, pl):
    return sum(1 for v in board.values() if v[0] == pl and v[1] == "l")


def _key(board, to_move):
    items = ";".join(sorted(f"{c},{r},{pl},{k}" for (c, r), (pl, k) in board.items()))
    return f"{to_move}|{items}"


# --- capture generators (Turkish strike: captured pieces stay on the board as
#     obstacles until the whole sequence resolves; none may be jumped twice) ----

def _man_captures(board, pos, pl, captured, origin):
    """All maximal MAN capture sequences from `pos`.  Returns [(path, count)].
    Captures enemy MEN forward, enemy LADIES backward; promotion (reaching the
    back rank) ENDS the move, so such a leaf does not extend."""
    c, r = pos
    fwd = _man_fwd(pl)
    back = _man_back(pl)
    out = []
    for dc, dr in DIAGS:
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        if not _on(*land):
            continue
        occ = board.get(over)
        if occ is None or over in captured or occ[0] == pl or occ[1] == "s":
            continue
        if occ[1] == "m" and (dc, dr) not in fwd:
            continue
        if occ[1] == "l" and (dc, dr) not in back:
            continue
        if board.get(land) is not None and land != origin:
            continue
        ncap = captured | {over}
        if land[1] == _back_rank(pl):
            out.append(([pos, land], len(ncap)))          # promotion ends move
        else:
            cont = _man_captures(board, land, pl, ncap, origin)
            if cont:
                out += [([pos] + p, n) for p, n in cont]
            else:
                out.append(([pos, land], len(ncap)))
    return out


def _lady_jumps(board, pos, pl, captured, origin):
    """All maximal LADY jump sequences (short leap, any diagonal, chainable)."""
    c, r = pos
    out = []
    for dc, dr in DIAGS:
        over = (c + dc, r + dr)
        land = (c + 2 * dc, r + 2 * dr)
        if not _on(*land):
            continue
        occ = board.get(over)
        if occ is None or over in captured or occ[0] == pl or occ[1] == "s":
            continue
        if board.get(land) is not None and land != origin:
            continue
        ncap = captured | {over}
        cont = _lady_jumps(board, land, pl, ncap, origin)
        if cont:
            out += [([pos] + p, n) for p, n in cont]
        else:
            out.append(([pos, land], len(ncap)))
    return out


def _lady_replacements(board, pos, pl):
    """Ferz-style replacement captures from `pos`: (path, captured_kind)."""
    c, r = pos
    out = []
    for dc, dr in DIAGS:
        t = (c + dc, r + dr)
        if not _on(*t):
            continue
        occ = board.get(t)
        if occ is not None and occ[0] != pl and occ[1] != "s":
            out.append(([pos, t], occ[1]))
    return out


def _guarded(board, sq, pl):
    """Would an enemy piece be able to capture a `pl` LADY placed on `sq`?  Used
    for the jump-of-joy 'crossed square not threatened' condition."""
    enemy = 1 - pl
    sc, sr = sq
    for (pc, pr), (o, k) in board.items():
        if o != enemy:
            continue
        if k == "s":
            continue
        dc, dr = sc - pc, sr - pr
        if abs(dc) != 1 or abs(dr) != 1:
            continue
        if k == "l":
            return True                                    # adjacent lady: replaces/jumps
        # enemy man captures a lady by a BACKWARD leap over sq
        if (dc, dr) in _man_back(enemy):
            beyond = (sc + dc, sr + dr)
            if _on(*beyond) and board.get(beyond) is None:
                return True
    return False


def _must_wake(board, pl):
    return _num_ladies(board, pl) == 0 and any(
        v[0] == pl and v[1] == "s" for v in board.values())


class SleepingBeautyDraughts(Game):
    uid = "sleeping_beauty_draughts"
    name = "Sleeping Beauty Draughts"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SBState:
        b = _start_board()
        return SBState(board=b, hist=(_key(b, 0),))

    def current_player(self, s: SBState) -> int:
        return s.to_move

    # -- move generation ----------------------------------------------------

    def _wake_moves(self, s: SBState):
        """Legal moves when the mover must wake a beauty: for each of his
        beauties, the moves of the woken lady (captures / simple / jump of joy)."""
        pl = s.to_move
        beauties = [p for p, v in s.board.items() if v[0] == pl and v[1] == "s"]
        jumps, royal, simples, others = [], [], [], []
        for b in beauties:
            tb = dict(s.board)
            tb[b] = (pl, "l")
            for path, n in _lady_jumps(tb, b, pl, frozenset(), b):
                jumps.append((path, n))
            for path, kind in _lady_replacements(tb, b, pl):
                (royal if kind == "l" else others).append(path)
            bc, br = b
            for dc, dr in DIAGS:
                t = (bc + dc, br + dr)
                if _on(*t) and tb.get(t) is None:
                    simples.append([b, t])                  # 1-square lady step
                over = (bc + dc, br + dr)
                land = (bc + 2 * dc, br + 2 * dr)           # jump of joy
                if (_on(*land) and tb.get(land) is None and tb.get(over) is None
                        and not _guarded(tb, over, pl)):
                    others.append([b, land])
        if jumps:
            mx = max(n for _, n in jumps)
            return [p for p, n in jumps if n == mx] + royal
        return simples + others + royal

    def _all_moves(self, s: SBState):
        pl = s.to_move
        if _must_wake(s.board, pl):
            return self._wake_moves(s)
        mine = [(p, v[1]) for p, v in s.board.items() if v[0] == pl]
        jumps, royal, repl_men, simples = [], [], [], []
        for pos, kind in mine:
            if kind == "s":
                continue
            if kind == "m":
                for path, n in _man_captures(s.board, pos, pl, frozenset(), pos):
                    jumps.append((path, n))
                c, r = pos
                for dc, dr in _man_fwd(pl):
                    t = (c + dc, r + dr)
                    if _on(*t) and t not in s.board:
                        simples.append([pos, t])
            else:  # lady
                for path, n in _lady_jumps(s.board, pos, pl, frozenset(), pos):
                    jumps.append((path, n))
                for path, ck in _lady_replacements(s.board, pos, pl):
                    (royal if ck == "l" else repl_men).append(path)
                c, r = pos
                for dc, dr in DIAGS:
                    t = (c + dc, r + dr)
                    if _on(*t) and t not in s.board:
                        simples.append([pos, t])
        if jumps:
            mx = max(n for _, n in jumps)
            return [p for p, n in jumps if n == mx] + royal
        # no jumps: simple moves + optional replacement captures
        if s.rep:
            seen = set(s.hist)
            simples = [p for p in simples if not self._is_repeat(s, p, seen)]
        return simples + royal + repl_men

    def _is_repeat(self, s: SBState, path, seen):
        """True if a lady simple move `path` recreates a position seen in the run."""
        a, b = path[0], path[1]
        if s.board[a][1] != "l":
            return False
        nb = dict(s.board)
        nb[b] = nb.pop(a)
        return _key(nb, 1 - s.to_move) in seen

    def legal_moves(self, s: SBState):
        if s.ply >= PLY_CAP:
            return []
        return [">".join(f"{c},{r}" for c, r in path) for path in self._all_moves(s)]

    # -- apply --------------------------------------------------------------

    def _captured(self, board, cells):
        caps = []
        for a, b in zip(cells, cells[1:]):
            dc = b[0] - a[0]
            dr = b[1] - a[1]
            if abs(dc) == 2:
                caps.append((a[0] + dc // 2, a[1] + dr // 2))     # leap: midpoint
            elif abs(dc) == 1 and board.get(b) is not None:
                caps.append(b)                                     # replacement
        return caps

    def apply_move(self, s: SBState, move: str, rng=None) -> SBState:
        cells = [_cell(x) for x in move.split(">")]
        pl = s.to_move
        board = dict(s.board)
        woke = _must_wake(s.board, pl)
        origin = cells[0]
        mover_pl, kind = board.pop(origin)
        if woke:
            kind = "l"                                             # beauty wakes into a lady
        caps = self._captured(s.board, cells)
        for sq in caps:
            board.pop(sq, None)
        final = cells[-1]
        promoted = False
        if kind == "m" and final[1] == _back_rank(pl):
            promoted = True
            kind = "s" if _num_ladies(board, pl) >= 1 else "l"
        board[final] = (pl, kind)

        # classify the move for the ladies-only anti-loop run
        dc = abs(final[0] - origin[0]) if len(cells) == 2 else 99
        lady_simple = (not woke and not caps and not promoted
                       and s.board[origin][1] == "l" and dc == 1)
        newkey = _key(board, 1 - pl)
        if lady_simple:
            hist = s.hist + (newkey,)
            rep = s.rep or (newkey in set(s.hist))
        else:
            hist = (newkey,)
            rep = False
        return SBState(board=board, to_move=1 - pl, ply=s.ply + 1,
                       hist=hist, rep=rep)

    # -- terminal / score ---------------------------------------------------

    def is_terminal(self, s: SBState) -> bool:
        return len(self.legal_moves(s)) == 0

    def score(self, s: SBState) -> int:
        """Winner's points: total pieces on the board."""
        return len(s.board)

    def returns(self, s: SBState):
        if s.ply >= PLY_CAP:
            return [0.0, 0.0]                                       # honest draw backstop
        if len(self.legal_moves(s)) != 0:
            return [0.0, 0.0]
        # the player to move has no move -> he loses
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]

    # -- serialize / render -------------------------------------------------

    def serialize(self, s: SBState) -> dict:
        return {
            "board": {f"{c},{r}": [pl, k] for (c, r), (pl, k) in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "hist": list(s.hist),
            "rep": s.rep,
        }

    def deserialize(self, d: dict) -> SBState:
        return SBState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], ply=d.get("ply", 0),
            hist=tuple(d.get("hist", ())), rep=d.get("rep", False),
        )

    def describe_move(self, s: SBState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        caps = self._captured(s.board, cells)
        alg = lambda c: f"{'abcdefgh'[c[0]]}{c[1] + 1}"  # noqa: E731
        wake = "*" if _must_wake(s.board, s.to_move) else ""
        sep = ":" if caps else "-"
        return wake + sep.join(alg(c) for c in cells)

    def render(self, s: SBState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
        glyph = {"m": "", "l": "K", "s": "✵"}          # man=disc, lady=K, beauty=star
        pieces = []
        for (c, r), (pl, k) in s.board.items():
            p = {"cell": f"{c},{r}", "owner": pl}
            if glyph[k]:
                p["label"] = glyph[k]
            pieces.append(p)
        if self.is_terminal(s):
            ret = self.returns(s)
            if ret == [0.0, 0.0]:
                caption = "Draw"
            else:
                w = 0 if ret[0] > 0 else 1
                caption = f"{names[w]} wins by {self.score(s)} points"
        else:
            extra = " — wake a sleeping beauty" if _must_wake(s.board, s.to_move) else ""
            caption = f"{names[s.to_move]} to move{extra}"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
