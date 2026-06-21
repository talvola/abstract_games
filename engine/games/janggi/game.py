"""Janggi (Korean Chess) — 9-file x 10-rank board, the Korean sibling of Xiangqi.

Two sides: Cho (player 0, uppercase, home rows 0-4, moves first) and Han
(player 1, lowercase, rows 5-9).  Pieces sit on the points of a 9x10 grid
(rendered as cells).  Each side has a 3x3 **palace** with **diagonal lines**
drawn between the palace centre and its four corners; those diagonals are real
movement paths for some pieces.

Pieces (rendered with letters):

* General  G/g — one step orthogonally OR one step along a palace-diagonal line,
                 confined to the 3x3 palace.
* Guard    A/a — exactly like the General (palace, orthogonal + palace-diagonal),
                 two per side.
* Horse    H/h — one orthogonal then one outward diagonal; LAME: blocked by a
                 piece on the orthogonal leg.
* Elephant E/e — one orthogonal then TWO outward diagonals (a 1+2 leap); blocked
                 if any square along the path is occupied.  NOT river-confined.
* Chariot  R/r — slides orthogonally any distance (a rook); ALSO slides along the
                 palace-diagonal lines while inside a palace.
* Cannon   C/c — moves AND captures by jumping exactly ONE intervening 'screen'
                 piece (orthogonally any distance, or along a palace diagonal).
                 A cannon may NOT use another cannon as its screen, may NOT jump
                 over a cannon, and may NOT capture a cannon.
* Soldier  S/s — one step forward or sideways (never backward); no promotion.
                 Inside the ENEMY palace it may also step along the palace
                 diagonals (toward the enemy general).

Bikjang (facing generals): implemented as the Xiangqi-style *flying general*
rule — a move that leaves your own general facing the enemy general on an open
file (no pieces between) is **illegal**.  (See rules.md for the choice.)

A player with no legal move LOSES (checkmate or stalemate).  Termination is
guaranteed by a no-capture draw counter, threefold repetition, and a hard ply
cap.  Moves are clickable cell paths "fc,fr>tc,tr".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

W, H = 9, 10
CHO, HAN = 0, 1
NAMES = {CHO: "Cho", HAN: "Han"}
ORTHO = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIAG = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
PALACE_COLS = (3, 4, 5)
CHO_PALACE_ROWS = (0, 1, 2)
HAN_PALACE_ROWS = (7, 8, 9)
NO_CAPTURE_DRAW = 120
PLY_CAP = 600


# ---- palace diagonal geometry -------------------------------------------------
# A palace is a 3x3 block.  Diagonal lines connect the centre to the 4 corners,
# i.e. the centre and the corners are diagonally linked (one step), but the edge
# midpoints are NOT on any diagonal.  Build, per palace, the set of points and an
# adjacency of diagonal one-steps.

def _palace_points(rows):
    return {(c, r) for c in PALACE_COLS for r in rows}


def _palace_diag_steps(rows):
    """Map point -> list of diagonally-adjacent palace points (one step)."""
    cmid = 4
    rmid = rows[1]
    centre = (cmid, rmid)
    corners = [(PALACE_COLS[0], rows[0]), (PALACE_COLS[2], rows[0]),
               (PALACE_COLS[0], rows[2]), (PALACE_COLS[2], rows[2])]
    steps = {p: [] for p in _palace_points(rows)}
    for corner in corners:
        steps[centre].append(corner)
        steps[corner].append(centre)
    return steps


_CHO_PTS = _palace_points(CHO_PALACE_ROWS)
_HAN_PTS = _palace_points(HAN_PALACE_ROWS)
ALL_PALACE_PTS = _CHO_PTS | _HAN_PTS
# Diagonal adjacency over BOTH palaces (a point is only ever in one palace).
DIAG_STEPS = {}
DIAG_STEPS.update(_palace_diag_steps(CHO_PALACE_ROWS))
DIAG_STEPS.update(_palace_diag_steps(HAN_PALACE_ROWS))
# Which palace (by player) a point belongs to, if any.
POINT_PALACE = {}
for p in _CHO_PTS:
    POINT_PALACE[p] = CHO
for p in _HAN_PTS:
    POINT_PALACE[p] = HAN

# Directed diagonal *rays* for the chariot/cannon: for each palace point that is
# the centre or a corner, the diagonal direction(s) it can slide along, plus how
# far the line continues.  Since each diagonal line is exactly centre<->corner
# (2 points), a slider on a corner can go to the centre (and possibly continue to
# the opposite corner — corner, centre, opposite corner are collinear).  Build
# the full straight diagonal lines through the palace.

def _diag_lines(rows):
    cmid = 4
    centre = (cmid, rows[1])
    lines = [
        [(PALACE_COLS[0], rows[0]), centre, (PALACE_COLS[2], rows[2])],
        [(PALACE_COLS[2], rows[0]), centre, (PALACE_COLS[0], rows[2])],
    ]
    return lines


PALACE_LINES = _diag_lines(CHO_PALACE_ROWS) + _diag_lines(HAN_PALACE_ROWS)


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < W and 0 <= r < H


def owner(piece: str) -> int:
    return CHO if piece.isupper() else HAN


def kind(piece: str) -> str:
    return piece.upper()


def _in_palace(player: int, c, r) -> bool:
    rows = CHO_PALACE_ROWS if player == CHO else HAN_PALACE_ROWS
    return c in PALACE_COLS and r in rows


def _forward(player: int) -> int:
    return 1 if player == CHO else -1


def _start_board() -> dict:
    """Standard symmetric Janggi setup.

    Back rank (file 0..8): R H E A . A E H R, with the general on the middle
    palace row.  We use the common *symmetric* arrangement where each side has
    the same left/right layout (no per-side elephant/horse swap)."""
    b = {}
    back = ["R", "H", "E", "A", None, "A", "E", "H", "R"]
    for c, t in enumerate(back):
        if t is not None:
            b[(c, 0)] = t          # Cho back rank (row 0)
            b[(c, 9)] = t.lower()  # Han back rank (row 9)
    # Generals sit one row in, on the centre file, middle palace row.
    b[(4, 1)] = "G"
    b[(4, 8)] = "g"
    # Cannons on the third rank from each edge, files b & h (1 & 7).
    b[(1, 2)] = b[(7, 2)] = "C"
    b[(1, 7)] = b[(7, 7)] = "c"
    # Soldiers: files 0,2,4,6,8 on rank 3 (Cho) / rank 6 (Han).
    for c in (0, 2, 4, 6, 8):
        b[(c, 3)] = "S"
        b[(c, 6)] = "s"
    return b


def _soldier_targets(board, sq, player):
    c, r = sq
    fwd = _forward(player)
    outs = [(c, r + fwd), (c - 1, r), (c + 1, r)]
    outs = [(tc, tr) for tc, tr in outs if _on(tc, tr)]
    # Inside the ENEMY palace, a soldier may also step along palace diagonals
    # (only those that move forward / not backward).
    if POINT_PALACE.get(sq) == (1 - player):
        for d in DIAG_STEPS.get(sq, []):
            # forbid a strictly-backward diagonal
            if (d[1] - r) * fwd >= 0:
                outs.append(d)
    return outs


def _palace_diag_slide(board, sq, pl, capture_ok=True):
    """Slider (chariot) targets along palace diagonal lines through `sq`."""
    out = []
    for line in PALACE_LINES:
        if sq not in line:
            continue
        i = line.index(sq)
        for direction in (1, -1):
            j = i + direction
            while 0 <= j < len(line):
                t = line[j]
                if t not in board:
                    out.append(t)
                    j += direction
                    continue
                if capture_ok and owner(board[t]) != pl:
                    out.append(t)
                break
    return out


def _cannon_diag(board, sq, pl):
    """Cannon targets along palace diagonal lines (jump exactly one screen)."""
    out = []
    for line in PALACE_LINES:
        if sq not in line:
            continue
        i = line.index(sq)
        for direction in (1, -1):
            j = i + direction
            # find the screen
            while 0 <= j < len(line) and line[j] not in board:
                j += direction
            if not (0 <= j < len(line)):
                continue
            screen = line[j]
            if kind(board[screen]) == "C":      # screen may not be a cannon
                continue
            j += direction
            # landing square must be the next point (lines are short); scan to
            # first occupied beyond the screen.
            while 0 <= j < len(line) and line[j] not in board:
                t = line[j]
                out.append(t)                    # empty landing
                j += direction
            if 0 <= j < len(line):
                t = line[j]
                if owner(board[t]) != pl and kind(board[t]) != "C":
                    out.append(t)                # capture (not a cannon)
    return out


def _pseudo_targets(board, sq):
    """Destination squares for the piece at `sq`, ignoring own-general safety.
    Captures of own pieces are already excluded."""
    piece = board[sq]
    pl, t = owner(piece), kind(piece)
    c, r = sq
    out = []

    if t in ("G", "A"):
        for dc, dr in ORTHO:
            tc, tr = c + dc, r + dr
            if _in_palace(pl, tc, tr) and (board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl):
                out.append((tc, tr))
        for tc, tr in DIAG_STEPS.get(sq, []):
            if (board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl):
                out.append((tc, tr))
    elif t == "H":
        # one orthogonal (the leg) then one outward diagonal
        for dc, dr in ORTHO:
            leg = (c + dc, r + dr)
            if not _on(*leg) or leg in board:
                continue
            for ddc, ddr in DIAG:
                # diagonal must continue outward in the same orthogonal sense
                if (dc != 0 and ddc != dc) or (dr != 0 and ddr != dr):
                    continue
                tc, tr = leg[0] + ddc, leg[1] + ddr
                if _on(tc, tr) and (board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl):
                    out.append((tc, tr))
    elif t == "E":
        # one orthogonal then TWO outward diagonals; every intermediate empty
        for dc, dr in ORTHO:
            s1 = (c + dc, r + dr)                 # leg
            if not _on(*s1) or s1 in board:
                continue
            for ddc, ddr in DIAG:
                if (dc != 0 and ddc != dc) or (dr != 0 and ddr != dr):
                    continue
                s2 = (s1[0] + ddc, s1[1] + ddr)  # first diagonal
                if not _on(*s2) or s2 in board:
                    continue
                s3 = (s2[0] + ddc, s2[1] + ddr)  # second diagonal (landing)
                if _on(*s3) and (board.get(s3) is None or owner(board[s3]) != pl):
                    out.append(s3)
    elif t == "R":
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while _on(cc, rr) and (cc, rr) not in board:
                out.append((cc, rr))
                cc += dc
                rr += dr
            if _on(cc, rr) and owner(board[(cc, rr)]) != pl:
                out.append((cc, rr))
        out += _palace_diag_slide(board, sq, pl)
    elif t == "C":
        for dc, dr in ORTHO:
            cc, rr = c + dc, r + dr
            while _on(cc, rr) and (cc, rr) not in board:    # find the screen
                cc += dc
                rr += dr
            if not _on(cc, rr):
                continue
            if kind(board[(cc, rr)]) == "C":                # screen can't be a cannon
                continue
            cc += dc
            rr += dr
            while _on(cc, rr) and (cc, rr) not in board:    # empty landings
                out.append((cc, rr))
                cc += dc
                rr += dr
            if _on(cc, rr):
                tp = board[(cc, rr)]
                if owner(tp) != pl and kind(tp) != "C":     # capture (not a cannon)
                    out.append((cc, rr))
        out += _cannon_diag(board, sq, pl)
    elif t == "S":
        for tc, tr in _soldier_targets(board, sq, pl):
            if board.get((tc, tr)) is None or owner(board[(tc, tr)]) != pl:
                out.append((tc, tr))
    # de-dup (palace lines can overlap orthogonal rays for chariot/cannon)
    seen = set()
    uniq = []
    for o in out:
        if o not in seen:
            seen.add(o)
            uniq.append(o)
    return uniq


def _find_general(board, player):
    g = "G" if player == CHO else "g"
    for sq, p in board.items():
        if p == g:
            return sq
    return None


def _generals_face(board) -> bool:
    """Are the two generals on the same file with nothing between (bikjang)?"""
    gc = _find_general(board, CHO)
    gh = _find_general(board, HAN)
    if gc is None or gh is None or gc[0] != gh[0]:
        return False
    c = gc[0]
    lo, hi = sorted((gc[1], gh[1]))
    for r in range(lo + 1, hi):
        if (c, r) in board:
            return False
    return True


def _attacked(board, sq, by) -> bool:
    """Is `sq` attacked by player `by`?  Used for check detection."""
    c, r = sq
    # Chariot (and chariot-style palace-diagonal slides) along orthogonal rays
    for dc, dr in ORTHO:
        cc, rr = c + dc, r + dr
        while _on(cc, rr) and (cc, rr) not in board:
            cc += dc
            rr += dr
        if _on(cc, rr):
            p = board[(cc, rr)]
            if owner(p) == by and kind(p) == "R":
                return True
            # cannon: look past this (non-cannon) screen for an enemy cannon
            if kind(p) != "C":
                cc += dc
                rr += dr
                while _on(cc, rr) and (cc, rr) not in board:
                    cc += dc
                    rr += dr
                if _on(cc, rr):
                    p2 = board[(cc, rr)]
                    if owner(p2) == by and kind(p2) == "C":
                        return True
    # Chariot / cannon along palace diagonal lines toward sq
    if sq in ALL_PALACE_PTS:
        for line in PALACE_LINES:
            if sq not in line:
                continue
            i = line.index(sq)
            for direction in (1, -1):
                j = i + direction
                while 0 <= j < len(line) and line[j] not in board:
                    j += direction
                if not (0 <= j < len(line)):
                    continue
                p = board[line[j]]
                if owner(p) == by and kind(p) == "R":
                    return True
                if kind(p) != "C":
                    j += direction
                    while 0 <= j < len(line) and line[j] not in board:
                        j += direction
                    if 0 <= j < len(line):
                        p2 = board[line[j]]
                        if owner(p2) == by and kind(p2) == "C":
                            return True
    # Horse: a horse attacks sq from offsets (knight shape) if its leg is clear
    for dc, dr in ORTHO:
        leg_from_sq = (c + dc, r + dr)  # where a horse's landing-leg would be relative
        # enumerate the two knight squares reachable from this leg direction
        for ddc, ddr in DIAG:
            if (dc != 0 and ddc != dc) or (dr != 0 and ddr != dr):
                continue
            hsq = (leg_from_sq[0] + ddc, leg_from_sq[1] + ddr)
            p = board.get(hsq)
            if p is not None and owner(p) == by and kind(p) == "H":
                # the horse's leg is the orthogonal step OUT of hsq toward sq.
                # horse at hsq moves: ortho (-dc,-dr) then diag... reconstruct leg:
                leg = (hsq[0] - ddc, hsq[1] - ddr)  # = leg_from_sq
                if leg not in board:
                    return True
    # Elephant: 1 ortho + 2 diag, path clear
    for dc, dr in ORTHO:
        for ddc, ddr in DIAG:
            if (dc != 0 and ddc != dc) or (dr != 0 and ddr != dr):
                continue
            esq = (c + dc + 2 * ddc, r + dr + 2 * ddr)
            p = board.get(esq)
            if p is not None and owner(p) == by and kind(p) == "E":
                s1 = (esq[0] - 2 * ddc - dc, esq[1] - 2 * ddr - dr)  # leg from elephant
                s2 = (esq[0] - 2 * ddc, esq[1] - 2 * ddr)
                s3 = (esq[0] - ddc, esq[1] - ddr)
                if s1 not in board and s2 not in board and s3 not in board:
                    return True
    # General / Guard: orthogonal palace step or palace-diagonal step onto sq.
    # Both the attacker's square and sq must lie in the attacker's palace.
    for dc, dr in ORTHO:
        asq = (c + dc, r + dr)
        p = board.get(asq)
        if (p is not None and owner(p) == by and kind(p) in ("G", "A")
                and _in_palace(by, *sq) and _in_palace(by, *asq)):
            return True
    for d in DIAG_STEPS.get(sq, []):
        p = board.get(d)
        if p is not None and owner(p) == by and kind(p) in ("G", "A"):
            return True
    # Soldier: enemy soldier adjacent whose move reaches sq
    for nsq in [(c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)] + list(DIAG_STEPS.get(sq, [])):
        p = board.get(nsq)
        if p is not None and owner(p) == by and kind(p) == "S" and sq in _soldier_targets(board, nsq, by):
            return True
    return False


def _in_check(board, player) -> bool:
    g = _find_general(board, player)
    return g is not None and _attacked(board, g, 1 - player)


@dataclass
class JGState:
    board: dict = field(default_factory=dict)   # (c, r) -> piece letter
    to_move: int = CHO
    halfmove: int = 0                            # plies since last capture
    ply: int = 0
    reps: dict = field(default_factory=dict)     # position key -> count


class Janggi(Game):
    uid = "janggi"
    name = "Janggi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> JGState:
        return JGState(board=_start_board())

    def current_player(self, s: JGState) -> int:
        return s.to_move

    def _draw(self, s: JGState) -> bool:
        return (s.halfmove >= NO_CAPTURE_DRAW or s.ply >= PLY_CAP
                or any(v >= 3 for v in s.reps.values()))

    def _gen(self, s: JGState) -> list:
        """Fully legal (from, to) moves for the side to move."""
        moves = []
        for sq, p in s.board.items():
            if owner(p) != s.to_move:
                continue
            for to in _pseudo_targets(s.board, sq):
                nb = dict(s.board)
                nb[to] = nb.pop(sq)
                if _in_check(nb, s.to_move):
                    continue
                if _generals_face(nb):            # bikjang = flying-general: illegal
                    continue
                moves.append((sq, to))
        return moves

    def legal_moves(self, s: JGState) -> list[str]:
        if self._draw(s):
            return []
        return [f"{a[0]},{a[1]}>{b[0]},{b[1]}" for a, b in self._gen(s)]

    def apply_move(self, s: JGState, move: str, rng=None) -> JGState:
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        capture = to in board
        board[to] = board.pop(frm)
        halfmove = 0 if capture else s.halfmove + 1
        reps = {} if capture else dict(s.reps)        # captures are irreversible
        key = self._key(board, 1 - s.to_move)
        reps[key] = reps.get(key, 0) + 1
        return JGState(board=board, to_move=1 - s.to_move,
                       halfmove=halfmove, ply=s.ply + 1, reps=reps)

    def _key(self, board, to_move) -> str:
        return str(to_move) + "|" + ",".join(
            f"{c}{r}{p}" for (c, r), p in sorted(board.items()))

    def is_terminal(self, s: JGState) -> bool:
        return self._draw(s) or not self._gen(s)

    def returns(self, s: JGState) -> list[float]:
        if self._draw(s):
            return [0.0, 0.0]
        # no legal move (checkmate or stalemate): the side to move loses
        return [-1.0, 1.0] if s.to_move == CHO else [1.0, -1.0]

    def serialize(self, s: JGState) -> dict:
        return {
            "board": {f"{c},{r}": p for (c, r), p in s.board.items()},
            "to_move": s.to_move,
            "halfmove": s.halfmove,
            "ply": s.ply,
            "reps": dict(s.reps),
        }

    def deserialize(self, d: dict) -> JGState:
        return JGState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"],
            halfmove=d.get("halfmove", 0),
            ply=d.get("ply", 0),
            reps=dict(d.get("reps", {})),
        )

    def describe_move(self, s: JGState, move: str) -> str:
        frm, to = (_cell(x) for x in move.split(">"))
        p = s.board.get(frm, "?")
        cap = "x" if to in s.board else "-"
        alg = lambda c: f"{'abcdefghi'[c[0]]}{c[1]}"  # noqa: E731
        return f"{p}{alg(frm)}{cap}{alg(to)}"

    def render(self, s: JGState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": owner(p), "label": kind(p)}
                  for (c, r), p in s.board.items()]
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = ("Draw" if ret == [0.0, 0.0]
                       else f"{NAMES[CHO if ret[0] > 0 else HAN]} wins")
        elif _in_check(s.board, s.to_move):
            caption = f"{NAMES[s.to_move]} to move (check)"
        else:
            caption = f"{NAMES[s.to_move]} to move"
        return {
            "board": {"type": "square", "width": W, "height": H},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
