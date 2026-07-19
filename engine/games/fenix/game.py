"""Fenix (Strike) — Fred Horn, 1975; published by HUCH! 2019.

9x9 board, 28 discs per side arranged as solid corner triangles (all cells with
c+r <= 6 for Red, c+r >= 10 for Black). Each player's first five turns stack own
discs into exactly 3 Generals (2-stacks) and 1 King (a disc onto a General ->
3-stack), in any order.

Battle: Soldier (single) steps orthogonally; General (2-stack) slides like a
rook; King (3-stack) steps one square in any direction. Captures are
checkers-style jumps (the General jumps a distant enemy on its line and lands
on any vacant square beyond), COMPULSORY, chained until exhausted; each enemy
piece may be jumped only once per turn (reaching it again blocks the chain) and
jumped pieces stay on the board as obstacles until the END of the turn. Among
all complete capture sequences you must play one of maximum total VALUE
(King=3, General=2, Soldier=1 stones).

Reconstitution: if the opponent captured one or more of your Generals last
turn, you MAY spend this turn stacking two orthogonally adjacent Soldiers into
one new General (this overrides the compulsion to capture). If your King was
captured last turn you MUST spend this turn stacking a Soldier onto an
orthogonally adjacent General to rebuild it — if you cannot, you lose.

Variants (manifest option "rules"):
  original  — setup stacks must be built from orthogonally adjacent pieces;
              repeating the same position (with the same player to move and
              pending rights) a third time LOSES for the repeater (rule 11).
  published — HUCH! box rules: setup stacking needs no adjacency; no
              repetition rule (the stale game peters out to the draw below).

"If neither player can capture the other's King, the game is drawn" is
implemented as a no-progress rule: 60 consecutive plies without a capture or a
stack creation — plus a hard 1000-ply cap — end the game in a draw. A player
with no legal move loses (this covers the explicit "King captured and cannot
be rebuilt" loss; general stalemate-loses is a documented interpretation in
the draughts tradition).

Move grammar (all clickable cell paths): setup/rebuild stacking is
"from>to" onto an OWN piece; steps and slides are "from>to" onto a vacant
square; capture chains are "from>land1>land2>..." landing squares.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from agp.game import Game

N = 9
QUIET_CAP = 60          # plies without capture/stacking -> draw (rule 12 proxy)
PLY_CAP = 1000          # hard backstop
ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
ALL8 = ORTH + [(1, 1), (1, -1), (-1, 1), (-1, -1)]
LETTER = {1: "S", 2: "G", 3: "K"}


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _id(q) -> str:
    return f"{q[0]},{q[1]}"


def _on(q) -> bool:
    return 0 <= q[0] < N and 0 <= q[1] < N


def _adj(a, b) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


@dataclass
class FState:
    board: dict = field(default_factory=dict)   # (c,r) -> (owner, height 1..3)
    to_move: int = 0
    setup: list = field(default_factory=lambda: [0, 0])   # stacking turns done
    mrk: list = field(default_factory=lambda: [False, False])  # must rebuild King
    mrg: list = field(default_factory=lambda: [False, False])  # may rebuild General
    winner: object = None    # None | 0 | 1 (only set by the repetition rule)
    quiet: int = 0
    ply: int = 0
    rep: dict = field(default_factory=dict)     # position key -> count (original)
    variant: str = "original"
    last: list = field(default_factory=list)    # cells of the last move


def _start_board() -> dict:
    b = {}
    for c in range(N):
        for r in range(N):
            if c + r <= 6:
                b[(c, r)] = (0, 1)
            elif c + r >= 10:
                b[(c, r)] = (1, 1)
    return b


def _chains(work, pos, player, height, jumped):
    """Complete capture chains for a piece at ``pos`` (already lifted off
    ``work``, so its origin square is genuinely vacant). Jumped pieces stay on
    the board (they block sliding, landing, and re-jumping); ``jumped`` is the
    set of squares already jumped this turn. Returns visited-square paths; a
    path is only emitted once no further capture exists from its last square
    (chaining is compulsory)."""
    paths = []
    if height == 2:  # General: fly over vacants, jump one enemy, land beyond
        for d in ORTH:
            i, over = 1, None
            while True:
                sq = (pos[0] + i * d[0], pos[1] + i * d[1])
                if not _on(sq):
                    break
                if sq in work:
                    over = sq
                    break
                i += 1
            if over is None or work[over][0] == player or over in jumped:
                continue
            j = 1
            while True:
                land = (over[0] + j * d[0], over[1] + j * d[1])
                if not _on(land) or land in work:
                    break
                cont = _chains(work, land, player, height, jumped | {over})
                if cont:
                    paths += [[pos] + p for p in cont]
                else:
                    paths.append([pos, land])
                j += 1
    else:  # Soldier (orthogonal) / King (all 8): adjacent enemy, land beyond
        for d in (ORTH if height == 1 else ALL8):
            over = (pos[0] + d[0], pos[1] + d[1])
            land = (pos[0] + 2 * d[0], pos[1] + 2 * d[1])
            if not _on(land) or land in work:
                continue
            occ = work.get(over)
            if occ is None or occ[0] == player or over in jumped:
                continue
            cont = _chains(work, land, player, height, jumped | {over})
            if cont:
                paths += [[pos] + p for p in cont]
            else:
                paths.append([pos, land])
    return paths


def _cap_squares(work, path):
    """The jumped enemy squares along a visited-square path: exactly the first
    occupied square strictly between consecutive vertices (``work`` has the
    moving piece removed)."""
    caps = []
    for a, b in zip(path, path[1:]):
        dc = (b[0] > a[0]) - (b[0] < a[0])
        dr = (b[1] > a[1]) - (b[1] < a[1])
        sq = (a[0] + dc, a[1] + dr)
        while sq != b:
            if sq in work:
                caps.append(sq)
                break
            sq = (sq[0] + dc, sq[1] + dr)
    return caps


class Fenix(Game):
    name = "Fenix"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -------------------------------------------------------------

    def initial_state(self, options=None, rng=None) -> FState:
        variant = (options or {}).get("rules", "original")
        if variant not in ("original", "published"):
            variant = "original"
        return FState(board=_start_board(), variant=variant)

    def current_player(self, s: FState) -> int:
        return s.to_move

    # ---- move generation ---------------------------------------------------

    def _own(self, s: FState, height):
        return [q for q, (o, h) in s.board.items() if o == s.to_move and h == height]

    def _setup_moves(self, s: FState) -> list[str]:
        """First five turns per player: stack a Soldier onto an own Soldier
        (-> General, at most 4 such creations) or onto an own General
        (-> the one King). Original rules require orthogonal adjacency."""
        singles, twos, threes = self._own(s, 1), self._own(s, 2), self._own(s, 3)
        creations = len(twos) + len(threes)
        need_adj = s.variant == "original"
        moves = []
        for src in singles:
            if creations < 4:
                for dst in singles:
                    if dst != src and (not need_adj or _adj(src, dst)):
                        moves.append(f"{_id(src)}>{_id(dst)}")
            if not threes:
                for dst in twos:
                    if not need_adj or _adj(src, dst):
                        moves.append(f"{_id(src)}>{_id(dst)}")
        return sorted(moves)

    def _king_rebuilds(self, s: FState) -> list[str]:
        return sorted(
            f"{_id(src)}>{_id(dst)}"
            for src in self._own(s, 1) for dst in self._own(s, 2) if _adj(src, dst)
        )

    def _general_rebuilds(self, s: FState) -> list[str]:
        singles = self._own(s, 1)
        return sorted(
            f"{_id(a)}>{_id(b)}" for a in singles for b in singles
            if a != b and _adj(a, b)
        )

    def _capture_moves(self, s: FState) -> list[str]:
        p = s.to_move
        best, out = 0, {}
        for pos, (o, h) in s.board.items():
            if o != p:
                continue
            work = dict(s.board)
            del work[pos]
            for path in _chains(work, pos, p, h, frozenset()):
                value = sum(work[q][1] for q in _cap_squares(work, path))
                mv = ">".join(_id(q) for q in path)
                if value > best:
                    best, out = value, {mv: True}
                elif value == best:
                    out[mv] = True
        return sorted(out)

    def _quiet_moves(self, s: FState) -> list[str]:
        p, moves = s.to_move, []
        for pos, (o, h) in s.board.items():
            if o != p:
                continue
            if h == 2:
                for d in ORTH:
                    i = 1
                    while True:
                        t = (pos[0] + i * d[0], pos[1] + i * d[1])
                        if not _on(t) or t in s.board:
                            break
                        moves.append(f"{_id(pos)}>{_id(t)}")
                        i += 1
            else:
                for d in (ORTH if h == 1 else ALL8):
                    t = (pos[0] + d[0], pos[1] + d[1])
                    if _on(t) and t not in s.board:
                        moves.append(f"{_id(pos)}>{_id(t)}")
        return sorted(moves)

    def _moves(self, s: FState) -> list[str]:
        p = s.to_move
        if s.setup[p] < 5:
            return self._setup_moves(s)
        if s.mrk[p]:
            # MUST rebuild the King; overrides everything (incl. compulsory
            # capture). Empty => the player has lost (handled by is_terminal).
            return self._king_rebuilds(s)
        caps = self._capture_moves(s)
        extra = self._general_rebuilds(s) if s.mrg[p] else []
        if caps:
            # Rebuilding a General is allowed INSTEAD of the compulsory capture
            # (AG20 editorial clarification), but never compulsory.
            return sorted(set(caps + extra))
        return sorted(set(self._quiet_moves(s) + extra))

    def legal_moves(self, s: FState) -> list[str]:
        if s.winner is not None or s.quiet >= QUIET_CAP or s.ply >= PLY_CAP:
            return []
        return self._moves(s)

    # ---- applying moves ----------------------------------------------------

    def _poskey(self, board, to_move, mrk, mrg) -> str:
        cells = ".".join(
            f"{c}{r}{o}{h}" for (c, r), (o, h) in sorted(board.items())
        )
        flags = "".join("1" if f else "0" for f in mrk + mrg)
        return f"{cells}|{to_move}|{flags}"

    def apply_move(self, s: FState, move: str, rng=None) -> FState:
        cells = [_cell(x) for x in move.split(">")]
        p = s.to_move
        board = dict(s.board)
        setup = list(s.setup)
        mrk, mrg = list(s.mrk), list(s.mrg)
        if cells[0] not in board or board[cells[0]][0] != p:
            raise ValueError(f"no own piece on {move!r} source")
        dest = cells[-1]
        stacking = len(cells) == 2 and dest in board and board[dest][0] == p
        if stacking:
            if board[cells[0]][1] != 1:
                raise ValueError("only a single Soldier may be stacked")
            del board[cells[0]]
            board[dest] = (p, board[dest][1] + 1)
            if setup[p] < 5:
                setup[p] += 1
            progress = True
        else:
            piece = board.pop(cells[0])
            caps = _cap_squares(board, cells)
            heights = [board[q][1] for q in caps]
            for q in caps:
                del board[q]                      # removal at END of the turn
            board[dest] = piece
            progress = bool(caps)
            for h in heights:
                if h == 3:
                    mrk[1 - p] = True             # King down: must rebuild next turn
                if h == 2:
                    mrg[1 - p] = True             # General down: may rebuild next turn
        mrk[p] = False                            # one-shot rights expire with the turn
        mrg[p] = False
        winner = s.winner
        rep = {}
        if s.variant == "original" and winner is None:
            rep = {} if progress else dict(s.rep)
            key = self._poskey(board, 1 - p, mrk, mrg)
            rep[key] = rep.get(key, 0) + 1
            if rep[key] >= 3:
                winner = 1 - p                    # the repeater loses (rule 11)
        return FState(
            board=board, to_move=1 - p, setup=setup, mrk=mrk, mrg=mrg,
            winner=winner, quiet=0 if progress else s.quiet + 1, ply=s.ply + 1,
            rep=rep, variant=s.variant, last=[_id(q) for q in cells],
        )

    # ---- results -----------------------------------------------------------

    def _draw(self, s: FState) -> bool:
        return s.winner is None and (s.quiet >= QUIET_CAP or s.ply >= PLY_CAP)

    def is_terminal(self, s: FState) -> bool:
        if s.winner is not None or self._draw(s):
            return True
        return not self._moves(s)

    def returns(self, s: FState) -> list[float]:
        if s.winner is not None:
            return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]
        if self._draw(s):
            return [0.0, 0.0]
        return [-1.0, 1.0] if s.to_move == 0 else [1.0, -1.0]  # stuck player loses

    def heuristic(self, s: FState):
        st = [0, 0]
        for (o, h) in s.board.values():
            st[o] += h
        v = math.tanh((st[0] - st[1]) / 8.0)
        return [v, -v]

    # ---- persistence -------------------------------------------------------

    def serialize(self, s: FState) -> dict:
        return {
            "board": {_id(q): [o, h] for q, (o, h) in s.board.items()},
            "to_move": s.to_move,
            "setup": list(s.setup),
            "mrk": list(s.mrk),
            "mrg": list(s.mrg),
            "winner": s.winner,
            "quiet": s.quiet,
            "ply": s.ply,
            "rep": dict(s.rep),
            "variant": s.variant,
            "last": list(s.last),
        }

    def deserialize(self, d: dict) -> FState:
        return FState(
            board={_cell(k): tuple(v) for k, v in d["board"].items()},
            to_move=d["to_move"], setup=list(d["setup"]),
            mrk=list(d["mrk"]), mrg=list(d["mrg"]), winner=d["winner"],
            quiet=d["quiet"], ply=d["ply"], rep=dict(d["rep"]),
            variant=d["variant"], last=list(d["last"]),
        )

    # ---- presentation ------------------------------------------------------

    def describe_move(self, s: FState, move: str) -> str:
        cells = [_cell(x) for x in move.split(">")]
        src, dst = cells[0], cells[-1]
        tgt = s.board.get(dst)
        if len(cells) == 2 and tgt is not None and tgt[0] == s.to_move:
            what = "General" if tgt[1] == 1 else "King"
            verb = "Make" if s.setup[s.to_move] < 5 else "Rebuild"
            return f"{verb} {what} {_id(src)}>{_id(dst)}"
        letter = LETTER[s.board[src][1]]
        work = dict(s.board)
        del work[src]
        caps = _cap_squares(work, cells)
        if caps:
            value = sum(work[q][1] for q in caps)
            return f"{letter} " + "x".join(_id(q) for q in cells) + f" (+{value})"
        return f"{letter} {_id(src)}-{_id(dst)}"

    def render(self, s: FState, perspective=None) -> dict:
        names = {0: "Red", 1: "Black"}
        pieces = []
        for q, (o, h) in sorted(s.board.items()):
            piece = {"cell": _id(q), "owner": o}
            if h > 1:
                piece["stack"] = [o] * h
            pieces.append(piece)
        p = s.to_move
        if self.is_terminal(s):
            ret = self.returns(s)
            caption = "Draw" if ret[0] == 0 else f"{names[0 if ret[0] > 0 else 1]} wins"
        elif s.setup[p] < 5:
            caption = f"{names[p]}: setup — build a stack ({s.setup[p] + 1}/5)"
        elif s.mrk[p]:
            caption = f"{names[p]} must rebuild the King"
        elif s.mrg[p]:
            caption = f"{names[p]} to move (may rebuild a General)"
        else:
            caption = f"{names[p]} to move"
        return {
            "board": {"type": "square", "width": N, "height": N},
            "pieces": pieces,
            "highlights": [{"cell": x, "kind": "last-move"} for x in s.last],
            "caption": caption,
        }
