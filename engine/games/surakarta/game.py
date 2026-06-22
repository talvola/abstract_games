"""Surakarta — a traditional Indonesian capturing game.

Played on a 6x6 grid of intersections (coords "0,0".."5,5"). Two players, 12
pieces each: player 0 (White) fills rows 0 and 1, player 1 (Black) fills rows 4
and 5; the middle two rows (2, 3) start empty.

TWO MOVE TYPES
  (A) NON-CAPTURING STEP — move one piece to any of the up-to-8 orthogonally or
      diagonally adjacent intersections that is EMPTY.
  (B) CAPTURING MOVE — a piece travels along the orthogonal grid LINES (its row
      or column), must pass around at least one of the corner LOOPS, continues
      along the connected perpendicular line, and captures the FIRST piece it
      meets, which must be an enemy. The slide may pass over empty intersections
      but may NOT jump over any piece (the first piece encountered ends the
      slide — capture if enemy, illegal if own or if no loop was traversed).
      Diagonals are for stepping only, never for capturing.

THE LOOP TOPOLOGY (as implemented)
  The 6x6 has 6 rows (r = 0..5) and 6 columns (c = 0..5). Only the INNER FOUR
  lines on each axis have loop tracks; the outermost lines (r/c in {0, 5}) do
  NOT loop. The loops come in two concentric rings, each a single closed cyclic
  track:
    * INNER RING (depth 1): rows r = 1, 4 and columns c = 1, 4. The four small
      corner arcs join the END of each of these lines to the END of the
      perpendicular inner line at the same corner.
    * OUTER RING (depth 2): rows r = 2, 3 and columns c = 2, 3. The four larger
      corner arcs join those lines analogously.
  That is 4 corners x 2 rings = 8 corner arcs total. A capturing slide follows
  one ring: it walks straight along a line, and ONLY at a board edge does an arc
  turn it 90 degrees onto the perpendicular line (interior crossings are passed
  straight through). It must cross >= 1 arc before the captured piece, else the
  move is illegal. The two rings are independent — a slide never switches rings.

  Each ring is modelled as a precomputed cyclic sequence of cells (with the four
  interior crossing cells appearing twice — once per line that passes through
  them); a slide is a walk along that cycle in either direction until it meets a
  piece or returns to its origin.

WIN. Capture ALL of the opponent's pieces.

TERMINATION. Captures strictly reduce material, but non-capturing steps can
shuffle forever, so a no-capture ply cap forces a DRAW (see rules.md).

MOVE NOTATION. The platform ">"-separated cell path. A non-capturing step is
"frm>to" (adjacent). A capture is also "frm>to" where `to` is the captured
enemy's cell reached via the loop slide (the path between is implicit). The two
never collide: a step `to` is adjacent and empty; a capture `to` is the slid-to
enemy cell (never adjacent-empty).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

N = 6              # board is N x N intersections
NO_CAP_CAP = 60    # consecutive non-capturing plies -> draw

DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1),
         (1, 1), (1, -1), (-1, 1), (-1, -1)]


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(c, r):
    return f"{c},{r}"


def _on(c, r):
    return 0 <= c < N and 0 <= r < N


def _build_ring(depth):
    """Cyclic cell sequence for one loop ring.

    depth 1 -> inner ring (rows/cols 1 & 4); depth 2 -> outer (rows/cols 2 & 3).
    The four arc transitions are at the segment boundaries (indices 5, 11, 17,
    23): transition i -> i+1 (mod len) crosses an arc iff i is in the arc set.
    """
    lo = depth
    hi = N - 1 - depth
    seq = []
    for c in range(N):           # row `lo`, left -> right
        seq.append((c, lo))
    for r in range(N):           # col `hi`, bottom -> top
        seq.append((hi, r))
    for c in range(N - 1, -1, -1):  # row `hi`, right -> left
        seq.append((c, hi))
    for r in range(N - 1, -1, -1):  # col `lo`, top -> bottom
        seq.append((lo, r))
    return seq


RINGS = [_build_ring(1), _build_ring(2)]
RING_LEN = len(RINGS[0])                       # 24
ARC_IDX = {RING_LEN - 19, RING_LEN - 13, RING_LEN - 7, RING_LEN - 1}  # {5,11,17,23}

# cell -> list of (ring_index, position_in_ring)
_OCC: dict = {}
for _ri, _seq in enumerate(RINGS):
    for _pos, _c in enumerate(_seq):
        _OCC.setdefault(_c, []).append((_ri, _pos))


def _slide(start_cell, ri, pos, direction, board):
    """Walk ring `ri` from index `pos` (a position of start_cell) in `direction`
    (+1 / -1). Return (target_cell, arcs_crossed) for the FIRST occupied cell
    met, or None if the walk returns to the origin cell first without meeting a
    piece. Does not check enemy/own or arc count — caller does.
    """
    seq = RINGS[ri]
    n = len(seq)
    arcs = 0
    i = pos
    for _ in range(n):
        prev = i
        i = (i + direction) % n
        # crossing an arc? transition prev->i (forward) is arc when prev in set;
        # going backward (i->i+1 was the arc) it's arc when i in set.
        if direction == 1:
            if prev in ARC_IDX:
                arcs += 1
        else:
            if i in ARC_IDX:
                arcs += 1
        cell = seq[i]
        if cell == start_cell:    # came back around to origin -> no capture
            return None
        if board.get(cell) is not None:
            return (cell, arcs)
    return None


def _capture_targets(board, frm, player):
    """Set of enemy cells `frm`'s piece can legally capture (via >= 1 loop)."""
    enemy = 1 - player
    targets = set()
    for ri, pos in _OCC.get(frm, []):
        for direction in (1, -1):
            res = _slide(frm, ri, pos, direction, board)
            if res is None:
                continue
            cell, arcs = res
            if arcs >= 1 and board.get(cell) == enemy:
                targets.add(cell)
    return targets


def _start_board() -> dict:
    b = {}
    for r in (0, 1):
        for c in range(N):
            b[(c, r)] = 0
    for r in (N - 2, N - 1):
        for c in range(N):
            b[(c, r)] = 1
    return b


@dataclass
class SurakartaState:
    board: dict = field(default_factory=dict)  # (c, r) -> player
    to_move: int = 0
    ply: int = 0
    no_cap: int = 0    # consecutive non-capturing plies
    winner: int = -1   # -1 none, 0/1 player, -2 draw


class Surakarta(Game):
    uid = "surakarta"
    name = "Surakarta"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SurakartaState:
        return SurakartaState(board=_start_board())

    def current_player(self, s: SurakartaState) -> int:
        return s.to_move

    # ---- move generation -------------------------------------------------
    def _capture_moves(self, s: SurakartaState):
        out = []
        for pos, pl in s.board.items():
            if pl != s.to_move:
                continue
            for tgt in _capture_targets(s.board, pos, s.to_move):
                out.append(f"{_fmt(*pos)}>{_fmt(*tgt)}")
        return out

    def _step_moves(self, s: SurakartaState):
        out = []
        for (c, r), pl in s.board.items():
            if pl != s.to_move:
                continue
            for dc, dr in DIRS8:
                nc, nr = c + dc, r + dr
                if _on(nc, nr) and s.board.get((nc, nr)) is None:
                    out.append(f"{_fmt(c, r)}>{_fmt(nc, nr)}")
        return out

    def legal_moves(self, s: SurakartaState) -> list[str]:
        if self.is_terminal(s):
            return []
        # captures and steps are BOTH legal (captures are not mandatory in
        # Surakarta). Order captures first for nicer bot/UI behaviour.
        return self._capture_moves(s) + self._step_moves(s)

    # ---- apply -----------------------------------------------------------
    def _is_capture(self, board, frm, to, player):
        return to in _capture_targets(board, frm, player)

    def apply_move(self, s: SurakartaState, move: str, rng=None) -> SurakartaState:
        frm_s, to_s = move.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        board = dict(s.board)
        player = s.to_move
        capture = self._is_capture(board, frm, to, player)
        pl = board.pop(frm)
        if capture:
            board.pop(to, None)   # remove the captured enemy
        board[to] = pl
        nxt = 1 - player
        no_cap = 0 if capture else s.no_cap + 1
        winner = -1
        if not any(v == nxt for v in board.values()):
            winner = player
        elif no_cap >= NO_CAP_CAP:
            winner = -2
        ns = SurakartaState(board=board, to_move=nxt, ply=s.ply + 1,
                            no_cap=no_cap, winner=winner)
        # opponent stalemated (cannot happen with mobile pieces, but be safe):
        if ns.winner == -1 and not self.legal_moves(ns):
            ns.winner = -2
        return ns

    def is_terminal(self, s: SurakartaState) -> bool:
        return s.winner != -1

    def returns(self, s: SurakartaState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- serialize -------------------------------------------------------
    def serialize(self, s: SurakartaState) -> dict:
        return {
            "board": {_fmt(c, r): pl for (c, r), pl in s.board.items()},
            "to_move": s.to_move,
            "ply": s.ply,
            "no_cap": s.no_cap,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> SurakartaState:
        return SurakartaState(
            board={_cell(k): v for k, v in d["board"].items()},
            to_move=d["to_move"], ply=d["ply"],
            no_cap=d.get("no_cap", 0), winner=d["winner"],
        )

    # ---- display ---------------------------------------------------------
    def describe_move(self, s: SurakartaState, move: str) -> str:
        frm_s, to_s = move.split(">")
        frm, to = _cell(frm_s), _cell(to_s)
        sep = "x" if self._is_capture(dict(s.board), frm, to, s.to_move) else "-"
        return f"{frm_s}{sep}{to_s}"

    # ---- render ----------------------------------------------------------
    @staticmethod
    def _grid_lines():
        """Cosmetic orthogonal grooves: the 6 row + 6 column segments."""
        segs = []
        for r in range(N):
            segs.append([[0, r], [N - 1, r]])
        for c in range(N):
            segs.append([[c, 0], [c, N - 1]])
        return segs

    @staticmethod
    def _loop_overlay():
        """The 8 corner loop arcs, drawn as over-cell polylines that bulge out
        past the board edge so the capture tracks are visible. Each arc joins the
        end of a looping row line to the end of the perpendicular column line at
        a corner, for both the inner (depth 1) and outer (depth 2) rings.
        """
        col_inner = "#c9a227"   # inner ring (gold)
        col_outer = "#7aa2c9"   # outer ring (blue)
        overlay = []
        for depth, col in ((1, col_inner), (2, col_outer)):
            lo = depth
            hi = N - 1 - depth
            bulge = 0.45 + 0.35 * (depth - 1)   # outer ring bulges further
            # four corners: (line_end_a, control_outside, line_end_b)
            # bottom-left: row `lo` left end (0,lo) <-> col `lo` bottom end (lo,0)
            overlay.append([[0, lo], [-bulge, -bulge], [lo, 0], col])
            # bottom-right: row `lo` right end (5,lo) <-> col `hi` bottom (hi,0)
            overlay.append([[N - 1, lo], [N - 1 + bulge, -bulge], [hi, 0], col])
            # top-right: row `hi` right end (5,hi) <-> col `hi` top (hi,5)
            overlay.append([[N - 1, hi], [N - 1 + bulge, N - 1 + bulge], [hi, N - 1], col])
            # top-left: row `hi` left end (0,hi) <-> col `lo` top (lo,5)
            overlay.append([[0, hi], [-bulge, N - 1 + bulge], [lo, N - 1], col])
        return overlay

    def render(self, s: SurakartaState, perspective=None) -> dict:
        names = {0: "White", 1: "Black"}
        pieces = [
            {"cell": _fmt(c, r), "owner": pl, "label": ""}
            for (c, r), pl in s.board.items()
        ]
        if self.is_terminal(s):
            if s.winner in (0, 1):
                caption = f"{names[s.winner]} wins"
            else:
                caption = "Draw (no-capture cap)"
        else:
            caption = f"{names[s.to_move]} to move"
        return {
            "board": {
                "type": "square", "width": N, "height": N,
                "lines": self._grid_lines(),
                "overlay": self._loop_overlay(),
            },
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
