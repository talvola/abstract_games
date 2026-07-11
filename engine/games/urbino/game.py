"""Urbino -- Dieter Stein's 2018 city-building placement game on a 9x9 board.

Two players jointly develop the town: two SHARED architect figures stand on
the board, and buildings may only be erected on empty squares that both
architects can "see" (queen-lines -- horizontal, vertical, diagonal -- not
looking over occupied squares). Each turn = optionally REPOSITION one
architect (it is *placed* on any unoccupied square -- architects teleport,
they do not travel along lines) and then MANDATORILY erect one of your
buildings (house=1, palace=2, tower=3) on a sight-line intersection, subject
to: (2.2) every district (orthogonally connected buildings) may contain at
most ONE block per player (all your buildings inside a district must stay
orthogonally connected), and (2.3) a tower may never be orthogonally adjacent
to another tower, nor a palace to another palace (either colour). Voluntary
passing is forbidden; a player who cannot make any (reposition +) build must
skip. Two consecutive skips end the game.

Scoring: only two-coloured districts score; in each, the player whose
buildings there total the higher value scores HIS OWN total (tie inside a
district -> compare counts of towers, then palaces, then houses; still tied
-> nobody scores it). Highest grand total wins; a tie compares the scored
buildings the same way (towers, palaces, houses); a full tie is a DRAW.

The optional MONUMENTS variant (manifest option) doubles a line of three:
town wall H-H-H = 6, ducal palace P-H-P = 10, cathedral T-P-T = 16; at most
one monument per block, and district ties are first broken by the more
valuable scored monument.

Rules verified against the designer's pages:
https://spielstein.com/games/urbino/rules (+ /rules/monuments)

Opening: Dark places architect 1 anywhere, Light places architect 2, then
Dark decides who erects the first building (that first turn has no
reposition action).

Cells are "c,r" ((0,0)=a1). Moves: architect placement "c,r"; the choice
"dark-starts"/"light-starts"; a turn is two sub-moves -- reposition
"c1,r1>c2,r2" or "pass" (keep architects), then build "c,r=H|P|T" (the
=CHOICE picker); a whole-turn forced skip is the single move "skip".
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from agp.game import Game

SIZE = 9
DARK, LIGHT = 0, 1
NAMES = {DARK: "Dark", LIGHT: "Light"}
KINDS = ("H", "P", "T")
KIND_VALUE = {"H": 1, "P": 2, "T": 3}
SUPPLY0 = {"H": 18, "P": 6, "T": 3}
ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]

# Monuments variant: pattern (a straight orthogonal line of 3 of one player's
# buildings) -> (rank, extra points over the pieces' base value).
#   town wall  H-H-H = 6  (base 3, +3, rank 1)
#   ducal pal. P-H-P = 10 (base 5, +5, rank 2)
#   cathedral  T-P-T = 16 (base 8, +8, rank 3)
MONUMENTS = {"HHH": (1, 3), "PHP": (2, 5), "TPT": (3, 8)}

PLY_CAP = 500          # structural termination exists (builds are finite); pure backstop
LOT_TINT = "#3d4457"   # subtle slate tint marking current building lots


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(cell):
    return f"{cell[0]},{cell[1]}"


def _on(c, r):
    return 0 <= c < SIZE and 0 <= r < SIZE


# Precomputed queen rays: RAYS[cell] = list of 8 tuples of cells walking
# outward from `cell` (bounds already applied) — the sight-line hot path.
RAYS = {}
for _c in range(SIZE):
    for _r in range(SIZE):
        rays = []
        for _dc, _dr in DIRS8:
            ray = []
            _x, _y = _c + _dc, _r + _dr
            while 0 <= _x < SIZE and 0 <= _y < SIZE:
                ray.append((_x, _y))
                _x, _y = _x + _dc, _y + _dr
            if ray:
                rays.append(tuple(ray))
        RAYS[(_c, _r)] = tuple(rays)


@dataclass
class UState:
    board: dict = field(default_factory=dict)   # (c,r) -> (owner, kind)
    arch: list = field(default_factory=list)    # 0..2 architect cells (shared figures)
    supply: list = field(default_factory=lambda: [dict(SUPPLY0), dict(SUPPLY0)])
    to_move: int = DARK
    phase: str = "ARCH"                          # ARCH -> CHOOSE -> (MOVE -> BUILD)*
    skips: int = 0                               # consecutive whole-turn skips
    ply: int = 0
    last: object = None                          # last placed/moved cell (highlight)
    monuments: bool = False


class Urbino(Game):

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        opts = options or {}
        mon = opts.get("monuments", False)
        if isinstance(mon, str):
            mon = mon.lower() in ("true", "on", "1", "yes")
        return UState(monuments=bool(mon))

    def current_player(self, state):
        return state.to_move

    # ---- sight lines ---------------------------------------------------------
    def _visible(self, occupied, a):
        """Empty squares the architect at `a` sees: straight rays in the 8
        queen directions, stopping at (and excluding) any occupied square."""
        out = set()
        add = out.add
        for ray in RAYS[a]:
            for xy in ray:
                if xy in occupied:
                    break
                add(xy)
        return out

    def _lots(self, board, arch):
        """Squares seen by BOTH architects (potential building lots).

        The official special case -- two collinear architects with no building
        between them make every square between them a lot -- falls out
        naturally: each architect's ray reaches all those squares."""
        occ = set(board) | set(arch)
        return self._visible(occ, arch[0]) & self._visible(occ, arch[1])

    # ---- placement legality (board-only rules 2.2 + 2.3) ---------------------
    def _ok_adjacent(self, board, cell, kind):
        """2.3: no tower orthogonally next to a tower, no palace next to a
        palace (either colour). Houses are unrestricted."""
        if kind == "H":
            return True
        for dc, dr in ORTH:
            b = board.get((cell[0] + dc, cell[1] + dr))
            if b is not None and b[1] == kind:
                return False
        return True

    def _ok_district(self, board, cell, owner, owner_map=None):
        """2.2: after placing, the district containing `cell` may hold at most
        one block (orthogonally connected same-colour group) per player.

        `owner_map` (cell -> owner over existing buildings) may be passed by a
        bulk caller to avoid rebuilding it per candidate."""
        # fast path: an isolated building forms its own 1-block district
        if not any((cell[0] + dc, cell[1] + dr) in board for dc, dr in ORTH):
            return True
        if owner_map is None:
            owner_map = {xy: o for xy, (o, _k) in board.items()}
        occ_owner = dict(owner_map)
        occ_owner[cell] = owner
        # collect the district containing the new building
        seen = {cell}
        stack = [cell]
        while stack:
            c, r = stack.pop()
            for dc, dr in ORTH:
                n = (c + dc, r + dr)
                if n in occ_owner and n not in seen:
                    seen.add(n)
                    stack.append(n)
        for col in (DARK, LIGHT):
            cells = {x for x in seen if occ_owner[x] == col}
            if not cells:
                continue
            start = next(iter(cells))
            comp = {start}
            stack = [start]
            while stack:
                c, r = stack.pop()
                for dc, dr in ORTH:
                    n = (c + dc, r + dr)
                    if n in cells and n not in comp:
                        comp.add(n)
                        stack.append(n)
            if comp != cells:
                return False
        return True

    def _kinds_at(self, board, cell, owner, supply, owner_map=None):
        """Building kinds `owner` may legally erect on `cell` (board rules
        only -- the caller supplies sight legality)."""
        kinds = [k for k in KINDS if supply[k] > 0 and self._ok_adjacent(board, cell, k)]
        if kinds and not self._ok_district(board, cell, owner, owner_map):
            return []
        return kinds

    def _buildable(self, board, owner, supply):
        """All building-rule-legal cells (independent of architects):
        {cell: [kinds]} over squares with no building."""
        owner_map = {xy: o for xy, (o, _k) in board.items()}
        out = {}
        for r in range(SIZE):
            for c in range(SIZE):
                if (c, r) in board:
                    continue
                ks = self._kinds_at(board, (c, r), owner, supply, owner_map)
                if ks:
                    out[(c, r)] = ks
        return out

    # ---- move generation ------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        b, arch, p = state.board, state.arch, state.to_move

        if state.phase == "ARCH":
            occ = set(arch)
            return [f"{c},{r}" for r in range(SIZE) for c in range(SIZE)
                    if (c, r) not in occ]

        if state.phase == "CHOOSE":
            return ["dark-starts", "light-starts"]

        if state.phase == "BUILD":
            buildable = self._buildable(b, p, state.supply[p])
            out = []
            for cell in sorted(self._lots(b, arch)):
                for k in buildable.get(cell, ()):
                    out.append(f"{_fmt(cell)}={k}")
            # Unreachable after a MOVE sub-move (those are filtered to keep a
            # build available); defensively a buildless first turn is a skip.
            return out or ["skip"]

        # MOVE: keep the architects ("pass") or teleport ONE of them to any
        # unoccupied square -- but only choices that leave at least one build.
        buildable = self._buildable(b, p, state.supply[p])
        moves = []
        occ = set(b) | set(arch)
        if buildable:
            vis = [self._visible(occ, a) for a in arch]
            if any(l in buildable for l in (vis[0] & vis[1])):
                moves.append("pass")
            empties = [(c, r) for r in range(SIZE) for c in range(SIZE)
                       if (c, r) not in occ]
            bset = set(buildable)
            occ_b = set(b)                       # buildings only
            for i, a in enumerate(arch):
                other = arch[1 - i]
                # the stationary architect's vision with the moved one lifted
                # off the board entirely (buildings are the only blockers)...
                vo_free = self._visible(occ_b, other) & bset
                occ2 = set(occ_b)
                occ2.add(other)
                for t in empties:
                    occ2.add(t)
                    vm = self._visible(occ2, t)
                    occ2.discard(t)
                    cand = vm & vo_free
                    if not cand:
                        continue
                    # ...then per target discard lots the landed architect at
                    # `t` now hides from `other` (strictly beyond t on the
                    # other->t ray). t itself is excluded already (t in occ2).
                    dc, dr = t[0] - other[0], t[1] - other[1]
                    if dc == 0 or dr == 0 or abs(dc) == abs(dr):
                        sc = (dc > 0) - (dc < 0)
                        sr = (dr > 0) - (dr < 0)
                        x, y = t[0] + sc, t[1] + sr
                        while _on(x, y) and (x, y) not in occ_b:
                            cand.discard((x, y))
                            x, y = x + sc, y + sr
                    if cand:
                        moves.append(f"{_fmt(a)}>{_fmt(t)}")
        return moves or ["skip"]

    # ---- apply ------------------------------------------------------------------
    def apply_move(self, state, move, rng=None):
        p = state.to_move
        ns = UState(board=dict(state.board), arch=list(state.arch),
                    supply=[dict(state.supply[0]), dict(state.supply[1])],
                    to_move=p, phase=state.phase, skips=state.skips,
                    ply=state.ply + 1, last=state.last,
                    monuments=state.monuments)

        if state.phase == "ARCH":
            cell = _cell(move)
            ns.arch.append(cell)
            ns.last = cell
            if len(ns.arch) == 1:
                ns.to_move = LIGHT
            else:
                ns.to_move = DARK
                ns.phase = "CHOOSE"
        elif state.phase == "CHOOSE":
            ns.to_move = DARK if move == "dark-starts" else LIGHT
            ns.phase = "BUILD"              # the first turn has no reposition
        elif move == "skip":                 # forced whole-turn skip
            ns.skips = state.skips + 1
            ns.to_move = 1 - p
            ns.phase = "MOVE"
        elif state.phase == "MOVE":
            if move != "pass":
                frm, _, to = move.partition(">")
                src, dst = _cell(frm), _cell(to)
                ns.arch[ns.arch.index(src)] = dst
                ns.last = dst
            ns.phase = "BUILD"
        else:                                # BUILD
            cellstr, _, k = move.partition("=")
            cell = _cell(cellstr)
            ns.board[cell] = (p, k)
            ns.supply[p][k] -= 1
            ns.skips = 0
            ns.to_move = 1 - p
            ns.phase = "MOVE"
            ns.last = cell
        return ns

    # ---- terminal / scoring -------------------------------------------------
    def is_terminal(self, state):
        return state.skips >= 2 or state.ply >= PLY_CAP

    def _best_monument(self, kinds_by_cell):
        """Best monument (rank, bonus) in one player's block: a straight
        orthogonal line of three of their buildings matching H-H-H, P-H-P or
        T-P-T. Patterns are palindromes, so scanning +x/+y suffices. Only ONE
        monument per block scores -> keep the max."""
        best = (0, 0)
        for (c, r), k in kinds_by_cell.items():
            for dc, dr in ((1, 0), (0, 1)):
                k2 = kinds_by_cell.get((c + dc, r + dr))
                k3 = kinds_by_cell.get((c + 2 * dc, r + 2 * dr))
                if k2 is None or k3 is None:
                    continue
                m = MONUMENTS.get(k + k2 + k3)
                if m and m > best:
                    best = m
        return best

    def _score(self, state):
        """Totals + overall-tiebreak tuples.

        Returns (totals[2], tb[2]) where tb[p] = (cathedrals, ducal palaces,
        town walls, towers, palaces, houses) counted over the buildings p
        actually scored (his own buildings in districts he won) -- the
        official tie rule 'the more valuable buildings that have been scored
        prevail', compared lexicographically."""
        board = state.board
        totals = [0, 0]
        tb = [[0] * 6 for _ in range(2)]
        left = set(board)
        while left:
            start = left.pop()
            comp = {start}
            stack = [start]
            while stack:
                c, r = stack.pop()
                for dc, dr in ORTH:
                    n = (c + dc, r + dr)
                    if n in board and n not in comp:
                        comp.add(n)
                        left.discard(n)
                        stack.append(n)
            kinds = [{}, {}]
            for xy in comp:
                o, k = board[xy]
                kinds[o][xy] = k
            if not kinds[0] or not kinds[1]:
                continue                     # one-colour district: no points
            val, mono, cnt = [0, 0], [(0, 0), (0, 0)], [None, None]
            for q in (DARK, LIGHT):
                val[q] = sum(KIND_VALUE[k] for k in kinds[q].values())
                if state.monuments:
                    mono[q] = self._best_monument(kinds[q])
                    val[q] += mono[q][1]
                ks = list(kinds[q].values())
                cnt[q] = (ks.count("T"), ks.count("P"), ks.count("H"))
            if val[0] != val[1]:
                w = 0 if val[0] > val[1] else 1
            elif state.monuments and mono[0][0] != mono[1][0]:
                w = 0 if mono[0][0] > mono[1][0] else 1
            elif cnt[0] != cnt[1]:
                w = 0 if cnt[0] > cnt[1] else 1
            else:
                w = None                     # dead heat: nobody scores it
            if w is not None:
                totals[w] += val[w]
                if mono[w][0]:
                    tb[w][3 - mono[w][0]] += 1   # rank 3->idx0 ... rank 1->idx2
                t, pp, h = cnt[w]
                tb[w][3] += t
                tb[w][4] += pp
                tb[w][5] += h
        return totals, [tuple(x) for x in tb]

    def _winner(self, state):
        totals, tb = self._score(state)
        if totals[0] != totals[1]:
            return 0 if totals[0] > totals[1] else 1
        if tb[0] != tb[1]:
            return 0 if tb[0] > tb[1] else 1
        return None

    def returns(self, state):
        w = self._winner(state)
        if w is None:
            return [0.0, 0.0]
        return [1.0 if i == w else -1.0 for i in range(2)]

    def heuristic(self, state):
        totals, _ = self._score(state)
        t = math.tanh((totals[0] - totals[1]) / 8.0)
        return [t, -t]

    # ---- presentation ---------------------------------------------------------
    def _alg(self, cell):
        return "abcdefghi"[cell[0]] + str(cell[1] + 1)

    def describe_move(self, state, move):
        if move == "skip":
            return "skip (cannot build)"
        if move == "pass":
            return "keep architects"
        if move == "dark-starts":
            return "Dark builds first"
        if move == "light-starts":
            return "Light builds first"
        if state.phase == "ARCH":
            return f"A@{self._alg(_cell(move))}"
        if ">" in move:
            frm, _, to = move.partition(">")
            return f"A {self._alg(_cell(frm))}-{self._alg(_cell(to))}"
        cellstr, _, k = move.partition("=")
        return f"{k}@{self._alg(_cell(cellstr))}"

    def render(self, state, perspective=None):
        pieces = []
        for (c, r), (o, k) in state.board.items():
            pieces.append({"cell": f"{c},{r}", "owner": o,
                           "stack": [o] * KIND_VALUE[k]})
        for a in state.arch:
            pieces.append({"cell": _fmt(a), "owner": 2, "glyph": "▲"})
        tints = {}
        if len(state.arch) == 2 and not self.is_terminal(state):
            tints = {_fmt(l): LOT_TINT for l in self._lots(state.board, state.arch)}
        highlights = ([{"cell": _fmt(state.last), "kind": "last-move"}]
                      if state.last else [])

        sup = state.supply
        def bag(q):
            return f"H{sup[q]['H']} P{sup[q]['P']} T{sup[q]['T']}"
        totals, _ = self._score(state)
        score = f"score {totals[0]}–{totals[1]}"
        if self.is_terminal(state):
            w = self._winner(state)
            cap = (f"Draw · {score}" if w is None
                   else f"{NAMES[w]} wins · {score}")
        elif state.phase == "ARCH":
            cap = f"{NAMES[state.to_move]}: place architect {len(state.arch) + 1} of 2"
        elif state.phase == "CHOOSE":
            cap = "Dark chooses who erects the first building"
        elif state.phase == "MOVE":
            cap = (f"{NAMES[state.to_move]}: reposition an architect or pass, "
                   f"then build · {score} · Dark {bag(0)} / Light {bag(1)}")
        else:
            cap = (f"{NAMES[state.to_move]}: erect a building on a tinted lot "
                   f"· {score} · Dark {bag(0)} / Light {bag(1)}")
        board = {"type": "square", "width": SIZE, "height": SIZE}
        if tints:
            board["tints"] = tints
        return {"board": board, "pieces": pieces,
                "highlights": highlights, "caption": cap,
                # "=P" must read Palace, not the chess picker's Pawn
                "choiceNames": {"H": "House (1)", "P": "Palace (2)", "T": "Tower (3)"}}

    # ---- serialise -------------------------------------------------------------
    def serialize(self, state):
        return {
            "board": {f"{c},{r}": [o, k] for (c, r), (o, k) in state.board.items()},
            "arch": [_fmt(a) for a in state.arch],
            "supply": [dict(state.supply[0]), dict(state.supply[1])],
            "to_move": state.to_move, "phase": state.phase,
            "skips": state.skips, "ply": state.ply,
            "last": None if state.last is None else _fmt(state.last),
            "monuments": state.monuments,
        }

    def deserialize(self, d):
        return UState(
            board={_cell(k): (int(v[0]), str(v[1])) for k, v in d["board"].items()},
            arch=[_cell(a) for a in d.get("arch", [])],
            supply=[dict(d["supply"][0]), dict(d["supply"][1])],
            to_move=d["to_move"], phase=d.get("phase", "ARCH"),
            skips=d.get("skips", 0), ply=d.get("ply", 0),
            last=None if d.get("last") is None else _cell(d["last"]),
            monuments=bool(d.get("monuments", False)))
