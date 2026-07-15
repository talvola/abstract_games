"""Cathedral — Robert P. Moore (1979). The strategy game of the medieval city.

Two players lay polyomino "buildings" on a 10x10 walled city, claiming enclosed
territory and capturing isolated enemy buildings. A neutral 6-cell Cathedral,
placed by Light before play, mediates: it can be captured, never returns, and
may never form part of a claim boundary.

Rules as implemented follow the official rulesheet (c)1978 Robert P. Moore
(gamecatalog.org/rules/Moore_Cathedral.pdf) — piece shapes read off its figures
— cross-checked against the designer's site (cathedral-game.co.nz). See rules.md.

The enclosure model (the heart of the game): for the player to move, delete that
player's OWN buildings from the board and 4-connect what remains. Every resulting
component is bounded by that player's buildings and/or the city wall — exactly the
rulesheet's "your buildings alone or your buildings and the wall". A component
holding 0 foreign pieces is claimed territory; exactly 1 foreign piece (an enemy
building or the Cathedral) is captured and the space claimed; 2+ foreign pieces
are all safe and the space stays open. This single rule reproduces all six of the
rulesheet's worked notes, including "the Cathedral may not form a boundary" (a
Cathedral that borders open space is *inside* the component, so it leaks the
pocket back to the rest of the board rather than walling it off) — see rules.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game

W = H = 10
LIGHT, DARK, CATH = 0, 1, 2          # seat 0 = light, seat 1 = dark, 2 = neutral

# Safety net only: a capture returns a building to its owner's stock, so play is
# not obviously bounded by the 28 building placements. See rules.md "Termination".
MAX_PLIES = 200

# ---------------------------------------------------------------------------
# The buildings, read directly off the rulesheet's "THE BUILDINGS" figures
# (page 4), top row of each pattern first, as drawn.
# ---------------------------------------------------------------------------
_DRAWN = {
    "Tavern":    ["X"],                        # monomino
    "Stable":    ["XX"],                       # domino
    "Inn":       ["XX",                        # L-tromino
                  ".X"],
    "Bridge":    ["XXX"],                      # I-tromino
    "Manor":     ["XXX",                       # T-tetromino
                  ".X."],
    "Square":    ["XX",                        # O-tetromino
                  "XX"],
    "Abbey":     ["XX.",                       # S/Z-tetromino  (CHIRAL)
                  ".XX"],
    "Infirmary": [".X.",                       # X/plus-pentomino
                  "XXX",
                  ".X."],
    "Castle":    ["XX",                        # U-pentomino
                  "X.",
                  "XX"],
    "Tower":     ["..X",                       # W-pentomino
                  ".XX",
                  "XX."],
    "Academy":   [".X.",                       # F-pentomino  (CHIRAL)
                  ".XX",
                  "XX."],
}
_CATHEDRAL_DRAWN = [".X.",                     # 6-cell Latin cross
                    "XXX",
                    ".X.",
                    ".X."]

COUNTS = {"Tavern": 2, "Stable": 2, "Inn": 2, "Bridge": 1, "Manor": 1,
          "Square": 1, "Abbey": 1, "Infirmary": 1, "Castle": 1, "Tower": 1,
          "Academy": 1}
CATHEDRAL_KEY = "Cathedral"
KEYS = list(_DRAWN)


def _parse(rows):
    """Drawn rows (top row first) -> cell-coord offsets with +r pointing UP, so
    a rendered palette thumbnail matches the rulesheet artwork."""
    nr = len(rows)
    return _norm([(c, nr - 1 - r)
                  for r, row in enumerate(rows)
                  for c, ch in enumerate(row) if ch == "X"])


def _norm(cells):
    """Translate a shape so its ANCHOR sits at (0,0), the anchor being the
    bottom-most then left-most cell the shape actually COVERS.

    The anchor is the cell the player clicks, so it must be part of the tile
    (SPEC: every orientation contains [0,0]). Normalising to the bounding-box
    corner instead would put the anchor on an EMPTY square for the Infirmary
    (a plus), the Abbey and the Academy — you'd click a cell the building never
    occupies. The cost is negative `dc` offsets, which the renderer handles.
    Still a valid canonical form (translation-invariant and deterministic), so
    it doubles as the dedup key in _rotations()."""
    ac, ar = min(cells, key=lambda x: (x[1], x[0]))
    return tuple(sorted((c - ac, r - ar) for c, r in cells))


def _rot(cells):
    """Rotate 90 degrees (a rotation in cell space, never a reflection)."""
    return _norm([(r, -c) for c, r in cells])


def _mirror(cells):
    return _norm([(-c, r) for c, r in cells])


def _rotations(cells):
    """The distinct ROTATIONS of a shape. Cathedral pieces may be turned but
    never flipped over — that ban is what makes the Abbey and the Academy
    meaningfully chiral (the two colours hold opposite forms of each)."""
    out, cur = [], _norm(cells)
    for _ in range(4):
        if cur not in out:
            out.append(cur)
        cur = _rot(cur)
    return out


def is_chiral(cells) -> bool:
    """True if the shape's mirror image is NOT one of its own rotations."""
    return _mirror(cells) not in _rotations(cells)


# Seat 0 (light) holds the shapes exactly as the rulesheet draws them; seat 1
# (dark) holds the mirror image of each CHIRAL one. "All pieces except the Abbey
# and the Academy are the same between colours" — and for the ten achiral
# buildings a mirror image is just one of the piece's own rotations, so mirroring
# them would change nothing but the thumbnail. Which colour gets which hand is
# arbitrary (mirroring the whole game is an isomorphism); see rules.md.
BASE = {LIGHT: {k: _parse(v) for k, v in _DRAWN.items()}}
BASE[DARK] = {k: (_mirror(v) if is_chiral(v) else v)
              for k, v in BASE[LIGHT].items()}
ORIENTS = {seat: {k: _rotations(v) for k, v in BASE[seat].items()}
           for seat in (LIGHT, DARK)}

CATHEDRAL_CELLS = _parse(_CATHEDRAL_DRAWN)
CATHEDRAL_ORIENTS = _rotations(CATHEDRAL_CELLS)

SIZE = {k: len(v) for k, v in BASE[LIGHT].items()}
SIZE[CATHEDRAL_KEY] = len(CATHEDRAL_CELLS)
FULL_STOCK_SQUARES = sum(SIZE[k] * n for k, n in COUNTS.items())    # 47


def _cs(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _sc(text) -> tuple:
    c, r = text.split(",")
    return (int(c), int(r))


@dataclass
class CState:
    board: dict = field(default_factory=dict)        # (c,r) -> pid
    pieces: dict = field(default_factory=dict)       # pid -> (owner, key, cells)
    stock: dict = field(default_factory=dict)        # {seat: {key: count}}
    moves_made: dict = field(default_factory=dict)   # {seat: building placements}
    ply: int = 0
    next_pid: int = 0
    cathedral_gone: bool = False
    last: tuple = ()                                 # cells just placed
    removed: tuple = ()                              # cells freed by a capture


class Cathedral(Game):
    name = "Cathedral"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> CState:
        return CState(stock={LIGHT: dict(COUNTS), DARK: dict(COUNTS)},
                      moves_made={LIGHT: 0, DARK: 0})

    def current_player(self, s: CState) -> int:
        # Ply 0 is Light placing the Cathedral (a setup action, not a "move" —
        # rule 3: dark "makes the first and each alternate move"). Ply 1 is
        # Dark's first building. Alternation then falls out of ply parity, and
        # a pass consumes a ply so it alternates correctly too.
        return s.ply % 2

    # ---- geometry --------------------------------------------------------
    def _covered(self, seat, key, oi, anchor):
        offs = (CATHEDRAL_ORIENTS if key == CATHEDRAL_KEY else ORIENTS[seat][key])[oi]
        return [(anchor[0] + dc, anchor[1] + dr) for dc, dr in offs]

    def _components(self, s: CState, p: int):
        """8-connected components of everything that is NOT p's own buildings.
        Returns [(cells, frozenset_of_foreign_pids)]. Each component is bounded
        purely by p's buildings and/or the city wall.

        The space is flood-filled 8-CONNECTED (diagonals included) on purpose —
        that is exactly rule 4's "The buildings must meet wall to wall, a corner
        to corner contact is not acceptable". Two of p's buildings that meet only
        at a point leave the two cells across that point diagonally adjacent, so
        the pocket leaks back into the rest of the city and is never sealed
        (rulesheet note 4). Only a wall-to-wall (4-connected) chain of buildings
        actually encloses, which is the standard connectivity duality. Every
        building is a polyomino, hence 4-connected, hence always lies wholly
        inside a single component."""
        mine = {c for c, pid in s.board.items() if s.pieces[pid][0] == p}
        seen, out = set(), []
        for r in range(H):
            for c in range(W):
                start = (c, r)
                if start in mine or start in seen:
                    continue
                comp, stack, foreign = [], [start], set()
                seen.add(start)
                while stack:
                    cell = stack.pop()
                    comp.append(cell)
                    pid = s.board.get(cell)
                    if pid is not None:
                        foreign.add(pid)
                    x, y = cell
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            nb = (x + dx, y + dy)
                            if (0 <= nb[0] < W and 0 <= nb[1] < H
                                    and nb not in mine and nb not in seen):
                                seen.add(nb)
                                stack.append(nb)
                out.append((comp, frozenset(foreign)))
        return out

    def _territory(self, s: CState, p: int) -> set:
        """Empty cells claimed by p — the opponent may not build there.

        Rule 4's "Neither you nor your opponent may claim space on your first
        move" is honoured by giving a player no territory until they have made a
        second placement (see rules.md)."""
        if s.moves_made.get(p, 0) < 2:
            return set()
        if not any(s.pieces[pid][0] == p for pid in s.board.values()):
            return set()                        # no buildings => the wall alone
        claimed = set()
        for comp, foreign in self._components(s, p):
            if not foreign:
                claimed.update(comp)
        return claimed

    def _placements(self, s: CState, p: int, first_only=False):
        moves = []
        blocked = self._territory(s, 1 - p)
        for key, n in s.stock[p].items():
            if n <= 0:
                continue
            for oi, offs in enumerate(ORIENTS[p][key]):
                # Offsets are anchor-relative and dc may be NEGATIVE (_norm),
                # so the anchor scan is bounded on both sides.
                lo_c, hi_c = min(c for c, _ in offs), max(c for c, _ in offs)
                lo_r, hi_r = min(r for _, r in offs), max(r for _, r in offs)
                for r in range(-lo_r, H - hi_r):
                    for c in range(-lo_c, W - hi_c):
                        ok = True
                        for dc, dr in offs:
                            cell = (c + dc, r + dr)
                            if cell in s.board or cell in blocked:
                                ok = False
                                break
                        if ok:
                            moves.append(f"{key}:{oi}@{c},{r}")
                            if first_only:
                                return moves
        return moves

    def _can_place(self, s: CState, p: int) -> bool:
        return bool(self._placements(s, p, first_only=True))

    # ---- core loop -------------------------------------------------------
    def legal_moves(self, s: CState) -> list[str]:
        if self.is_terminal(s):
            return []
        if s.ply == 0:                          # Light places the Cathedral
            out = []
            for oi, offs in enumerate(CATHEDRAL_ORIENTS):
                lo_c, hi_c = min(c for c, _ in offs), max(c for c, _ in offs)
                lo_r, hi_r = min(r for _, r in offs), max(r for _, r in offs)
                for r in range(-lo_r, H - hi_r):
                    for c in range(-lo_c, W - hi_c):
                        out.append(f"{CATHEDRAL_KEY}:{oi}@{c},{r}")
            return out
        p = self.current_player(s)
        moves = self._placements(s, p)
        # Rule 6: play continues while EITHER player can move, so a player with
        # no placement passes and the other keeps building.
        return moves if moves else ["pass"]

    def apply_move(self, s: CState, move: str, rng=None) -> CState:
        if move not in self.legal_moves(s):
            raise ValueError(f"illegal move: {move}")
        p = self.current_player(s)
        board = dict(s.board)
        pieces = dict(s.pieces)
        stock = {k: dict(v) for k, v in s.stock.items()}
        moves_made = dict(s.moves_made)
        next_pid = s.next_pid
        cathedral_gone = s.cathedral_gone
        last, removed = (), ()

        if move != "pass":
            keyo, anchor_s = move.split("@")
            key, oi = keyo.split(":")
            anchor = _sc(anchor_s)
            owner = CATH if key == CATHEDRAL_KEY else p
            cells = tuple(sorted(self._covered(p, key, int(oi), anchor)))
            pid = next_pid
            next_pid += 1
            pieces[pid] = (owner, key, cells)
            for cell in cells:
                board[cell] = pid
            last = cells
            if owner != CATH:
                stock[p][key] -= 1
                moves_made[p] += 1

        nxt = CState(board=board, pieces=pieces, stock=stock,
                     moves_made=moves_made, ply=s.ply + 1, next_pid=next_pid,
                     cathedral_gone=cathedral_gone, last=last, removed=())

        # Rule 5: resolve captures — but never on the mover's FIRST building
        # (rule 4's no-claim-on-your-first-move clause; without it Dark's opening
        # building would formally "isolate" the Cathedral in the one big region
        # and carry off the whole board).
        if move != "pass" and moves_made[p] >= 2:
            freed = []
            for comp, foreign in self._components(nxt, p):
                if len(foreign) != 1:
                    continue
                victim = next(iter(foreign))
                v_owner, v_key, v_cells = pieces[victim]
                for cell in v_cells:
                    del board[cell]
                del pieces[victim]
                if v_owner == CATH:
                    cathedral_gone = True       # never replaced (rule 5)
                else:
                    stock[v_owner][v_key] += 1  # may be replayed later (rule 5)
                freed.extend(v_cells)
            removed = tuple(sorted(freed))
            nxt.cathedral_gone = cathedral_gone
            nxt.removed = removed
        return nxt

    def is_terminal(self, s: CState) -> bool:
        if s.ply == 0:
            return False
        if s.ply >= MAX_PLIES:
            return True
        # Rule 6: the game ends when neither player can place.
        return not self._can_place(s, LIGHT) and not self._can_place(s, DARK)

    def unplaced_squares(self, s: CState, p: int) -> int:
        return sum(SIZE[k] * n for k, n in s.stock[p].items())

    def returns(self, s: CState) -> list[float]:
        # Rule 7. "Placed all his buildings while preventing his opponent from
        # doing so" is subsumed: 0 unplaced squares beats any positive count.
        u0 = self.unplaced_squares(s, LIGHT)
        u1 = self.unplaced_squares(s, DARK)
        if u0 < u1:
            return [1.0, -1.0]
        if u1 < u0:
            return [-1.0, 1.0]
        return [0.0, 0.0]                       # published, honest draw

    def heuristic(self, s: CState) -> list:
        """Rollout-cutoff eval: the rule-7 margin, squashed to (-1, 1)."""
        diff = self.unplaced_squares(s, DARK) - self.unplaced_squares(s, LIGHT)
        v = diff / 20.0
        v = max(-1.0, min(1.0, v))
        return [v, -v]

    # ---- persistence -----------------------------------------------------
    def serialize(self, s: CState) -> dict:
        return {
            "board": {_cs(c): pid for c, pid in s.board.items()},
            "pieces": {str(pid): {"owner": o, "key": k,
                                  "cells": [_cs(c) for c in cells]}
                       for pid, (o, k, cells) in s.pieces.items()},
            "stock": {str(seat): dict(v) for seat, v in s.stock.items()},
            "moves_made": {str(seat): v for seat, v in s.moves_made.items()},
            "ply": s.ply,
            "next_pid": s.next_pid,
            "cathedral_gone": s.cathedral_gone,
            "last": [_cs(c) for c in s.last],
            "removed": [_cs(c) for c in s.removed],
        }

    def deserialize(self, d: dict) -> CState:
        return CState(
            board={_sc(k): v for k, v in d["board"].items()},
            pieces={int(pid): (v["owner"], v["key"],
                               tuple(_sc(c) for c in v["cells"]))
                    for pid, v in d["pieces"].items()},
            stock={int(k): dict(v) for k, v in d["stock"].items()},
            moves_made={int(k): v for k, v in d["moves_made"].items()},
            ply=d["ply"],
            next_pid=d["next_pid"],
            cathedral_gone=d["cathedral_gone"],
            last=tuple(_sc(c) for c in d.get("last", [])),
            removed=tuple(_sc(c) for c in d.get("removed", [])),
        )

    # ---- presentation ----------------------------------------------------
    def describe_move(self, s: CState, move: str) -> str:
        who = "Light" if self.current_player(s) == LIGHT else "Dark"
        if move == "pass":
            return f"{who} passes"
        keyo, anchor = move.split("@")
        key = keyo.split(":")[0]
        text = f"{who} {key} @ {anchor}"
        after = self.apply_move(s, move)
        taken = [s.pieces[pid][1] for pid in s.pieces if pid not in after.pieces]
        if taken:
            text += " x" + "+".join(sorted(taken))
        return text

    def render(self, s: CState, perspective=None) -> dict:
        tint = {LIGHT: "#f0cccc", DARK: "#ccd6f0"}
        tints = {}
        for seat in (LIGHT, DARK):
            for cell in self._territory(s, seat):
                tints[_cs(cell)] = tint[seat]

        palette = {}
        for seat in (LIGHT, DARK):
            tiles = []
            if seat == LIGHT and s.ply == 0:
                tiles.append({"key": CATHEDRAL_KEY, "label": "Cathedral",
                              "count": 1,
                              "orients": [[list(x) for x in o]
                                          for o in CATHEDRAL_ORIENTS]})
            for k in KEYS:
                n = s.stock[seat].get(k, 0)
                if n > 0:
                    tiles.append({"key": k, "label": f"{k} ({SIZE[k]})", "count": n,
                                  "orients": [[list(x) for x in o]
                                              for o in ORIENTS[seat][k]]})
            palette[str(seat)] = tiles

        highlights = [{"cell": _cs(c), "kind": "last-move"} for c in s.last]
        highlights += [{"cell": _cs(c), "kind": "last-move"} for c in s.removed]

        u0, u1 = self.unplaced_squares(s, LIGHT), self.unplaced_squares(s, DARK)
        if self.is_terminal(s):
            res = self.returns(s)
            caption = ("Draw" if res[0] == res[1] else
                       ("Light wins" if res[0] > res[1] else "Dark wins"))
            caption += f" — unplaced squares: Light {u0}, Dark {u1}"
        elif s.ply == 0:
            caption = "Light places the Cathedral"
        else:
            who = "Light" if self.current_player(s) == LIGHT else "Dark"
            caption = f"{who} to move — unplaced squares: Light {u0}, Dark {u1}"

        return {
            "board": {"type": "square", "width": W, "height": H, "tints": tints},
            "pieces": [{"cell": _cs(c), "owner": s.pieces[pid][0], "shape": "fill"}
                       for c, pid in s.board.items()],
            "highlights": highlights,
            "palette": palette,
            "caption": caption,
        }
