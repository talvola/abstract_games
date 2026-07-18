"""Chase (Tom Kruszewski, TSR 1985/87) — dice armies on a cylindrical hex board.

Board: 9x9 hexagons, rows A (bottom, first player's home) to I (top), columns
1-9. Cell ids are "c,r" with c = column 1..9 and r = row 1..9 (r1 = A). Rows
B, D, F, H sit half a hex to the LEFT of rows A, C, E, G, I (the Abstract
Games issue 9 diagram convention, which moves the physical board's half-hexes
B1/D1/F1/H1 to the left edge to make whole hexes). The board is a CYLINDER:
column 9 is adjacent to column 1 in every row. The central hex E5 ("5,5") is
the Chamber.

Pieces are dice; the face showing is the die's "speed". Each side starts with
nine dice on its home row at speeds 1,2,3,4,5,4,3,2,1 (total 25) plus one die
off the board. A player's on-board speeds must always total 25; a player
reduced to four or fewer dice in play (max 4x6 = 24) loses.

A turn: move one die in a straight hex line exactly its speed. Moving off the
left/right edge wraps around (cylinder); a die that runs into the top or
bottom edge ricochets like a billiard ball (never straight back, never along
the edge). A die may never pass over any piece or over the Chamber. Landing
by exact count on an enemy die captures it; on a friendly die BUMPS it one
hex onward in the same billiard direction (chaining through further friendly
dice; a bump onto an enemy die captures it and ends the move; a move whose
bump chain would push any die into the Chamber is illegal). Landing in the
Chamber splits the die: two dice exit onto the two hexes adjacent to the
point of entry, the speed split as evenly as possible with the LARGER half
exiting to the LEFT of the direction of travel (a speed-1 die does not split
and exits left; a player already at the 10-piece maximum does not split
either — the mover simply exits left at full speed). Chamber exits may land
on pieces, bumping/capturing as usual (left exit resolved first, then right).

After losing a piece, its owner must restore their total to 25 BEFORE moving:
the lost speed is added to their lowest-speed die (capped at 6, any overflow
continuing to the next-lowest, and so on). When several dice tie for lowest
and the outcome genuinely depends on which is raised, the owner chooses: the
game enters a "dist" phase in which the owner's legal moves are the tied
cells (click the die to receive the points); forced steps are auto-applied.

Two adjacent same-colour dice may instead EXCHANGE: redistribute their
combined speed between them (each die 1..6; the pair must actually change).
This costs the whole turn. Move encodings:
  movement   "c,r>first,r>dest,r"  (origin, first step, destination — the
             first step disambiguates direction; speed-1 moves are "a>b",
             suffixed "=M" when an exchange with the same pair also exists)
  exchange   "a>b=n"  (the second die's new speed becomes n)
  distribute "c,r"    (during the dist phase: the die to receive points)

Interpretations (documented in rules.md): a bumped die may NOT be pushed into
the Chamber (Abstract Games issue 9 explicit rule; overrides S. O'Sullivan's
review which allows it); chamber exits resolve left first; a player with no
legal move loses (unreachable in practice); draws by 100 quiet plies (no
capture / no chamber move) or a 600-ply hard cap (platform termination
guarantee — Chase can cycle).

Sources: Abstract Games magazine issue 9 (Spring 2002) pp.13-17, 21, 29,
"Chase — A 1980's Yard Sale Classic" by C. Rodeffer & J. Neto (full rules +
worked examples + two problems with printed solutions, all reproduced by this
implementation's selftest); cross-checked against Wikipedia "Chase (board
game)" and Steffan O'Sullivan's SOS' Gameviews review (panix.com/~sos/bc).
"""

from __future__ import annotations

import math

from agp.game import Game

W = 9
H = 9
CHAMBER = (5, 5)
OPENING = (1, 2, 3, 4, 5, 4, 3, 2, 1)
QUIET_CAP = 100
PLY_CAP = 600

# Directions in CCW angular order (y up, row 1 = A at the bottom of the board).
E, NE, NW, WD, SW, SE = range(6)
_REFL = {NE: SE, NW: SW, SE: NE, SW: NW}
_UP = (NE, NW)
_DOWN = (SW, SE)

_ROWS = "ABCDEFGHI"
_FILL = ("#d23b3b", "#3b6fd2")  # seat colours (red = first player, blue = second)
_NAMES = ("Red", "Blue")


def _step(c, r, d):
    """Neighbour of (c, r) in direction d (column wraps; row NOT checked)."""
    if d == E:
        return c % 9 + 1, r
    if d == WD:
        return (c - 2) % 9 + 1, r
    odd = r % 2 == 1  # rows A,C,E,G,I are unshifted; B,D,F,H sit half-left
    dr = 1 if d in _UP else -1
    if d in (NE, SE):
        return (c % 9 + 1 if odd else c), r + dr
    return (c if odd else (c - 2) % 9 + 1), r + dr


def _next(c, r, d):
    """One billiard step from (c, r) heading d: reflect off the top/bottom
    edge first, then step. Returns ((c2, r2), d2)."""
    if r == H and d in _UP:
        d = _REFL[d]
    elif r == 1 and d in _DOWN:
        d = _REFL[d]
    return _step(c, r, d), d


def _ray(c, r, d, n):
    """The n cells entered from (c, r) heading d: [((c, r), d_of_entry), ...]."""
    out = []
    for _ in range(n):
        (c, r), d = _next(c, r, d)
        out.append(((c, r), d))
    return out


def _cid(cell):
    return f"{cell[0]},{cell[1]}"


def _cell(cid):
    a, b = cid.split(",")
    return int(a), int(b)


def _name(cell):
    return f"{_ROWS[cell[1] - 1]}{cell[0]}"


def _exchange_values(sa, sb):
    """Legal new speeds for the SECOND die of an adjacent same-colour pair."""
    t = sa + sb
    return [n for n in range(max(1, t - 6), min(6, t - 1) + 1) if n != sb]


def _land(nb, cell, d, die):
    """Resolve `die` = (owner, speed) arriving on `cell` heading d. Mutates
    nb. Returns the captured enemy speed (0 if none) or None if illegal
    (the bump chain would push a die into the Chamber)."""
    occ = nb.get(cell)
    if occ is None:
        nb[cell] = die
        return 0
    if occ[0] != die[0]:
        nb[cell] = die
        return occ[1]
    chain = [(cell, occ)]  # friendly dice about to shift one hex onward
    (cc, cr), cd = cell, d
    cap = 0
    while True:
        (ncell), cd = _next(cc, cr, cd)
        if ncell == CHAMBER:
            return None  # "a piece may never be bumped into the Chamber"
        t = nb.get(ncell)
        if t is None:
            break
        if t[0] != die[0]:
            cap = t[1]  # bumped into an enemy: captured, chain still shifts
            break
        chain.append((ncell, t))
        cc, cr = ncell
        if len(chain) > 40:  # safety net; unreachable (billiard orbits > 10)
            return None
    nb[ncell] = chain[-1][1]
    for i in range(len(chain) - 1, 0, -1):
        nb[chain[i][0]] = chain[i - 1][1]
    nb[chain[0][0]] = die
    return cap


def _path_ok(board, origin, cells):
    """May the mover traverse cells[:-1]? (Own origin counts as empty.)"""
    for cell in cells[:-1]:
        if cell == CHAMBER or (cell != origin and cell in board):
            return False
    return True


def _chain_ok(board, origin, cell, d, owner):
    """Cheap legality probe for landing on a friendly die (no board copy)."""
    (cc, cr), cd = cell, d
    while True:
        ncell, cd = _next(cc, cr, cd)
        if ncell == CHAMBER:
            return False
        t = board.get(ncell) if ncell != origin else None
        if t is None or t[0] != owner:
            return True
        cc, cr = ncell


def _resolve(board, origin, path, speed, owner):
    """Fully resolve a movement. Returns (new_board, captured_total,
    chamber_flag) or None if illegal."""
    cells = [p[0] for p in path]
    nb = dict(board)
    del nb[origin]
    for cell in cells[:-1]:
        if cell == CHAMBER or cell in nb:
            return None
    dest = cells[-1]
    d_in = path[-1][1]
    cap = 0
    chamber = False
    if dest == CHAMBER:
        chamber = True
        in_play = 1 + sum(1 for v in nb.values() if v[0] == owner)
        dl, dr = (d_in + 2) % 6, (d_in + 4) % 6
        lcell, rcell = _step(5, 5, dl), _step(5, 5, dr)
        if in_play >= 10 or speed == 1:
            c1 = _land(nb, lcell, dl, (owner, speed))
            if c1 is None:
                return None
            cap += c1
        else:
            c1 = _land(nb, lcell, dl, (owner, (speed + 1) // 2))  # Large=Left
            if c1 is None:
                return None
            cap += c1
            c2 = _land(nb, rcell, dr, (owner, speed // 2))
            if c2 is None:
                return None
            cap += c2
    else:
        c1 = _land(nb, dest, d_in, (owner, speed))
        if c1 is None:
            return None
        cap += c1
    return nb, cap, chamber


def _dist_step(board, seat, deficit):
    """Auto-apply every FORCED redistribution step; mutates board. Returns
    (deficit_left, tied_lowest_cells) — nonempty cells mean the owner must
    choose which lowest die receives the next points."""
    while deficit > 0:
        mine = [(v[1], k) for k, v in board.items() if v[0] == seat]
        m = min(s for s, _ in mine)
        assert m < 6, "distribution with all dice at 6 (loss missed?)"
        low = sorted(k for s, k in mine if s == m)
        room = sum(6 - m for _ in low)
        if len(low) == 1:
            add = min(deficit, 6 - m)
            board[low[0]] = (seat, m + add)
            deficit -= add
        elif deficit >= room:
            for k in low:  # every tied die reaches 6 whatever the order
                board[k] = (seat, 6)
            deficit -= room
        else:
            return deficit, low
    return 0, []


class Chase(Game):
    name = "Chase"

    @property
    def num_players(self):
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        board = {}
        for i, sp in enumerate(OPENING):
            board[(i + 1, 1)] = (0, sp)  # first player: home row A
            board[(i + 1, H)] = (1, sp)  # second player: home row I
        return {"board": board, "to_move": 0, "phase": "move", "deficit": 0,
                "winner": None, "quiet": 0, "ply": 0, "last": []}

    # ---- helpers ---------------------------------------------------------
    @staticmethod
    def _copy(s):
        return {"board": dict(s["board"]), "to_move": s["to_move"],
                "phase": s["phase"], "deficit": s["deficit"],
                "winner": s["winner"], "quiet": s["quiet"], "ply": s["ply"],
                "last": list(s["last"])}

    def _piece_moves(self, board, origin):
        """Legal movement strings (with their rays) for the die at origin."""
        owner, speed = board[origin]
        seen = set()
        out = []
        for d in range(6):
            path = _ray(origin[0], origin[1], d, speed)
            key = tuple(p[0] for p in path)
            if key in seen:  # edge-start rays merge with their reflection
                continue
            seen.add(key)
            cells = [p[0] for p in path]
            if not _path_ok(board, origin, cells):
                continue
            dest = cells[-1]
            d_in = path[-1][1]
            occ = board.get(dest) if dest != origin else None
            if dest == CHAMBER:
                if _resolve(board, origin, path, speed, owner) is None:
                    continue
            elif occ is not None and occ[0] == owner:
                if not _chain_ok(board, origin, dest, d_in, owner):
                    continue
            if speed == 1:
                m = f"{_cid(origin)}>{_cid(dest)}"
                if occ is not None and occ[0] == owner and \
                        _exchange_values(speed, occ[1]):
                    m += "=M"  # an exchange shares this click path
            else:
                m = f"{_cid(origin)}>{_cid(cells[0])}>{_cid(dest)}"
            out.append((m, path))
        return out

    def _exchange_moves(self, board, seat):
        out = []
        for cell, (o, s) in board.items():
            if o != seat:
                continue
            for d in range(6):
                if (cell[1] == H and d in _UP) or (cell[1] == 1 and d in _DOWN):
                    continue
                nbc = _step(cell[0], cell[1], d)
                occ = board.get(nbc)
                if occ and occ[0] == seat:
                    for n in _exchange_values(s, occ[1]):
                        out.append(f"{_cid(cell)}>{_cid(nbc)}={n}")
        return out

    def _all_moves(self, state):
        board = state["board"]
        seat = state["to_move"]
        moves = []
        for cell, (o, _sp) in board.items():
            if o == seat:
                moves.extend(m for m, _ in self._piece_moves(board, cell))
        moves.extend(self._exchange_moves(board, seat))
        return moves

    # ---- core loop -------------------------------------------------------
    def current_player(self, state):
        return state["to_move"]

    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        if state["phase"] == "dist":
            seat = state["to_move"]
            mine = [(v[1], k) for k, v in state["board"].items() if v[0] == seat]
            m = min(s for s, _ in mine)
            return [_cid(k) for k in sorted(k for s, k in mine if s == m)]
        return sorted(self._all_moves(state))

    def apply_move(self, state, move, rng=None):
        s = self._copy(state)
        board = s["board"]
        me = s["to_move"]

        if s["phase"] == "dist":  # choose which lowest die receives points
            cell = _cell(move)
            o, sp = board[cell]
            add = min(s["deficit"], 6 - sp)
            board[cell] = (o, sp + add)
            s["deficit"] -= add
            left, _choices = _dist_step(board, me, s["deficit"])
            s["deficit"] = left
            s["last"] = [move]
            if left == 0:
                s["phase"] = "move"
                self._post(s, 1 - me)  # the (rare) stuck check for the victim
            return s

        if "=" in move and not move.endswith("=M"):  # exchange
            pathpart, n = move.rsplit("=", 1)
            aid, bid = pathpart.split(">")
            a, b = _cell(aid), _cell(bid)
            n = int(n)
            t = board[a][1] + board[b][1]
            board[a] = (me, t - n)
            board[b] = (me, n)
            s["quiet"] += 1
            s["ply"] += 1
            s["to_move"] = 1 - me
            s["last"] = [aid, bid]
            self._post(s, me)
            return s

        core = move[:-2] if move.endswith("=M") else move
        parts = core.split(">")
        origin = _cell(parts[0])
        res = None
        for mstr, path in self._piece_moves(board, origin):
            if mstr == move:
                res = _resolve(board, origin, path, board[origin][1], me)
                break
        if res is None:
            raise ValueError(f"illegal move: {move}")
        nb, cap, chamber = res
        s["board"] = nb
        s["ply"] += 1
        s["quiet"] = 0 if (cap or chamber) else s["quiet"] + 1
        opp = 1 - me
        s["to_move"] = opp
        s["last"] = [parts[0], parts[-1]]
        if cap:
            if sum(1 for v in nb.values() if v[0] == opp) <= 4:
                s["winner"] = me  # cannot total 25 any more
                return s
            left, _choices = _dist_step(nb, opp, cap)
            s["deficit"] = left
            if left:
                s["phase"] = "dist"
                return s
        self._post(s, me)
        return s

    def _post(self, s, mover):
        """End-of-turn bookkeeping: draw caps + the stuck-player rule."""
        if s["winner"] is not None:
            return
        if s["quiet"] >= QUIET_CAP or s["ply"] >= PLY_CAP:
            s["winner"] = "draw"
            return
        if not self._all_moves(s):
            s["winner"] = mover  # opponent cannot complete a turn (see rules.md)

    def is_terminal(self, state):
        return state["winner"] is not None

    def returns(self, state):
        w = state["winner"]
        if w == "draw":
            return [0.0, 0.0]
        return [1.0, -1.0] if w == 0 else [-1.0, 1.0]

    def heuristic(self, state):
        n0 = sum(1 for v in state["board"].values() if v[0] == 0)
        n1 = sum(1 for v in state["board"].values() if v[0] == 1)
        v = math.tanh(0.3 * (n0 - n1))  # speeds always total 25: dice COUNT wins
        return [v, -v]

    # ---- persistence -----------------------------------------------------
    def serialize(self, state):
        return {"board": {_cid(k): list(v) for k, v in sorted(state["board"].items())},
                "to_move": state["to_move"], "phase": state["phase"],
                "deficit": state["deficit"], "winner": state["winner"],
                "quiet": state["quiet"], "ply": state["ply"],
                "last": list(state["last"])}

    def deserialize(self, data):
        return {"board": {_cell(k): (v[0], v[1]) for k, v in data["board"].items()},
                "to_move": data["to_move"], "phase": data["phase"],
                "deficit": data["deficit"], "winner": data["winner"],
                "quiet": data["quiet"], "ply": data["ply"],
                "last": list(data.get("last", []))}

    # ---- notation --------------------------------------------------------
    def describe_move(self, state, move):
        board = state["board"]
        if state["phase"] == "dist":
            cell = _cell(move)
            add = min(state["deficit"], 6 - board[cell][1])
            return f"+{add} → {_name(cell)}"
        if "=" in move and not move.endswith("=M"):
            pathpart, n = move.rsplit("=", 1)
            a, b = (_cell(x) for x in pathpart.split(">"))
            n = int(n)
            t = board[a][1] + board[b][1]
            return f"{_name(a)}⇄{_name(b)} ({t - n}/{n})"
        core = move[:-2] if move.endswith("=M") else move
        parts = core.split(">")
        a, dest = _cell(parts[0]), _cell(parts[-1])
        sp = board[a][1]
        if dest == CHAMBER:
            return f"{_name(a)}→Chamber ({sp})"
        occ = board.get(dest)
        if occ is None:
            return f"{_name(a)}→{_name(dest)} ({sp})"
        if occ[0] != board[a][0]:
            return f"{_name(a)}×{_name(dest)} ({sp})"
        return f"{_name(a)}→{_name(dest)} bump"

    # ---- rendering -------------------------------------------------------
    _S = 20.0  # hex circumradius (pointy-top); width = sqrt(3) * _S

    def render(self, state, perspective=None):
        s_ = self._S
        hw = s_ * math.sqrt(3) / 2
        cells = []
        for r in range(1, H + 1):
            for c in range(1, W + 1):
                cx = c * 2 * hw - (0 if r % 2 == 1 else hw)
                cy = (H - r) * 1.5 * s_ + s_
                pts = []
                for k in range(6):
                    a = math.radians(60 * k + 30)
                    pts.append([round(cx + s_ * math.cos(a), 2),
                                round(cy + s_ * math.sin(a), 2)])
                cells.append({"id": _cid((c, r)), "points": pts})
        pieces = [{"cell": _cid(k), "owner": v[0], "label": str(v[1]),
                   "fill": _FILL[v[0]], "stroke": "#ffffff"}
                  for k, v in sorted(state["board"].items())]
        n_play = [sum(1 for v in state["board"].values() if v[0] == p)
                  for p in (0, 1)]
        w = state["winner"]
        if w == "draw":
            caption = "Draw"
        elif w is not None:
            caption = f"{_NAMES[w]} wins"
        elif state["phase"] == "dist":
            caption = (f"{_NAMES[state['to_move']]}: add +{state['deficit']} "
                       f"to a lowest die (click it)")
        else:
            caption = f"{_NAMES[state['to_move']]} to move"
        caption += f" · off-board Red {10 - n_play[0]}, Blue {10 - n_play[1]}"
        return {
            "board": {"type": "polygons", "cells": cells,
                      "tints": {"5,5": "#e0c95f"}},
            "pieces": pieces,
            "highlights": [{"cell": cid, "kind": "last-move"}
                           for cid in state["last"]],
            "caption": caption,
            "choiceTitle": "Move or exchange",
            "choiceNames": {"M": "Move here (bump)",
                            **{str(n): f"Exchange → {n}" for n in range(1, 7)}},
        }
