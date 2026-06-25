"""Octi (Don Green, 1999; MENSA Select) — the basic / beginner 2-player game.

Implements the well-documented FoxMind "basic game" (the 6x7 board): 4 pods and
12 prongs per player. Pods ("octagons") gain movement directions when prongs
(arrows) are inserted; a pod may move or jump only in a direction it has a prong.

Board geometry (matches the renderer's screen convention — row 0 at the BOTTOM):
  width 7 (cols 0..6), height 6 (rows 0..5).
  Player 0 bases: column 1, rows 1..4  (left side).
  Player 1 bases: column 5, rows 1..4  (right side).
Each player starts with a pod on each of its own 4 bases and 12 prongs in reserve.

A turn is ONE of:
  * ADD A PRONG  — take a prong from your reserve and add it to one of your pods
    in any of the 8 directions that pod doesn't already have (encoded "c,r=DIR").
  * MOVE A POD   — step one square ("from>to") in a direction the pod HAS a prong,
    onto an empty square.
  * JUMP         — in a pronged direction, if the ADJACENT square holds a pod (yours
    or the enemy's) and the square BEYOND (same direction) is empty, the pod jumps
    over it to that empty square. A jump may CHAIN (continue jumping in any pronged
    direction). Encoded as a path "a>b>c"; an optional "=CAP"/"=KEEP" suffix when
    the path jumps over at least one enemy pod chooses whether to CAPTURE all the
    jumped enemy pods (remove them) or leave them (KEEP). Friendly pods are never
    removed. (Capturing is optional — the standard Octi rule.)

Win: land a pod on ANY enemy base square, OR capture all enemy pods.
Termination: prong-adds are finite (the reserve); pure movement could cycle, so a
no-capture/no-add ply cap forces a draw.

Prong direction -> board (dc, dr), with 0 = +row (UP on screen), clockwise:
  0:(0,+1) 1:(+1,+1) 2:(+1,0) 3:(+1,-1) 4:(0,-1) 5:(-1,-1) 6:(-1,0) 7:(-1,+1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH = 7
HEIGHT = 6
PODS_PER_PLAYER = 4
PRONG_SUPPLY = 12
MAX_PRONGS = 8

# Direction names in screen convention (0 = up = +row, clockwise).
DIR_NAMES = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
NAME_TO_DIR = {n: i for i, n in enumerate(DIR_NAMES)}
# Prong direction -> (dc, dr); 0 points up on screen = +row.
DELTA = [(0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1)]

BASES = {
    0: frozenset({(1, 1), (1, 2), (1, 3), (1, 4)}),
    1: frozenset({(5, 1), (5, 2), (5, 3), (5, 4)}),
}

NAMES = {0: "Red", 1: "Blue"}  # match the platform seat colours (P0 red disc, P1 blue disc)

# Force a draw if neither a prong is added nor a pod is captured for this many
# plies (movement-only stall). Generous so real play is unaffected.
NO_PROGRESS_CAP = 80


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _on(c, r):
    return 0 <= c < WIDTH and 0 <= r < HEIGHT


@dataclass
class OctiState:
    # (c, r) -> {"owner": int, "prongs": frozenset[int]}
    pods: dict = field(default_factory=dict)
    supply: list = field(default_factory=lambda: [PRONG_SUPPLY, PRONG_SUPPLY])
    to_move: int = 0
    winner: Optional[int] = None
    draw: bool = False
    no_progress: int = 0


class Octi(Game):
    uid = "octi"
    name = "Octi"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> OctiState:
        pods = {}
        for owner in (0, 1):
            for cell in sorted(BASES[owner]):
                pods[cell] = {"owner": owner, "prongs": frozenset()}
        return OctiState(pods=pods)

    def current_player(self, s: OctiState) -> int:
        return s.to_move

    # ---- move generation -------------------------------------------------

    def _add_prong_moves(self, s: OctiState) -> list:
        out = []
        if s.supply[s.to_move] <= 0:
            return out
        for (c, r), pod in s.pods.items():
            if pod["owner"] != s.to_move:
                continue
            for d in range(8):
                if d not in pod["prongs"]:
                    out.append(f"{c},{r}={DIR_NAMES[d]}")
        return out

    def _step_moves(self, s: OctiState) -> list:
        out = []
        for (c, r), pod in s.pods.items():
            if pod["owner"] != s.to_move:
                continue
            for d in pod["prongs"]:
                dc, dr = DELTA[d]
                nc, nr = c + dc, r + dr
                if _on(nc, nr) and (nc, nr) not in s.pods:
                    out.append(f"{c},{r}>{nc},{nr}")
        return out

    def _jump_paths(self, s: OctiState):
        """Yield (path, jumped_enemy_count) for every legal jump sequence.

        path is a list of (c,r) cells starting at the pod's origin. A jump moves
        2 squares in a pronged direction over an occupied adjacent square to an
        empty landing square. Jumped pods stay on the board during search (a pod
        is not removed until capture is resolved at the end) — but the jumping
        pod may not land on an occupied square, and may not revisit its own path
        cells (prevents infinite chains; the pod can't sit where it already was).
        """
        results = []

        def search(pos, prongs, path, visited, jumped_enemy):
            # A jump path of length > 1 (i.e. at least one jump made) is a legal
            # move on its own — the player MAY stop here even if more jumps exist.
            if len(path) > 1:
                results.append((path, jumped_enemy))
            for d in prongs:
                dc, dr = DELTA[d]
                over = (pos[0] + dc, pos[1] + dr)
                land = (pos[0] + 2 * dc, pos[1] + 2 * dr)
                if not _on(*land):
                    continue
                over_pod = s.pods.get(over)
                if over_pod is None:
                    continue  # nothing to jump over
                if land in s.pods or land in visited:
                    continue  # landing must be empty (and not a path cell)
                je = jumped_enemy + (1 if over_pod["owner"] != s.to_move else 0)
                search(land, prongs, path + [land], visited | {land}, je)

        for (c, r), pod in s.pods.items():
            if pod["owner"] != s.to_move:
                continue
            search((c, r), pod["prongs"], [(c, r)], {(c, r)}, 0)
        return results

    def _jump_moves(self, s: OctiState) -> list:
        out = []
        seen = set()
        for path, jumped_enemy in self._jump_paths(s):
            key = tuple(path)
            base = ">".join(f"{c},{r}" for c, r in path)
            if jumped_enemy > 0:
                for suf in ("CAP", "KEEP"):
                    m = f"{base}={suf}"
                    if m not in seen:
                        seen.add(m)
                        out.append(m)
            else:
                if base not in seen:
                    seen.add(base)
                    out.append(base)
        return out

    def legal_moves(self, s: OctiState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = self._add_prong_moves(s) + self._step_moves(s) + self._jump_moves(s)
        if not moves:
            # The side to move is stalled (no prong, no move, no jump). Treat as
            # a pass so legal_moves is never empty on a non-terminal state.
            return ["pass"]
        return moves

    # ---- apply -----------------------------------------------------------

    def apply_move(self, s: OctiState, move: str, rng=None) -> OctiState:
        pods = {cell: {"owner": p["owner"], "prongs": p["prongs"]}
                for cell, p in s.pods.items()}
        supply = list(s.supply)
        me = s.to_move
        winner = None
        progressed = False  # did this move add a prong or capture? (resets stall)

        if move == "pass":
            return OctiState(pods=pods, supply=supply, to_move=1 - me,
                             winner=None, draw=False,
                             no_progress=s.no_progress + 1)

        body, _, choice = move.partition("=")

        if ">" not in body:
            # ADD A PRONG: "c,r=DIR"
            cell = _cell(body)
            d = NAME_TO_DIR[choice]
            pod = pods[cell]
            pods[cell] = {"owner": pod["owner"],
                          "prongs": pod["prongs"] | {d}}
            supply[me] -= 1
            progressed = True
        else:
            path = [_cell(x) for x in body.split(">")]
            frm, to = path[0], path[-1]
            pod = pods.pop(frm)
            # capture: only on a jump path with the =CAP choice
            if len(path) > 2 or (len(path) == 2 and
                                 abs(path[1][0] - path[0][0]) +
                                 abs(path[1][1] - path[0][1]) > 1):
                # a jump path (2-square steps). Resolve optional capture.
                if choice == "CAP":
                    for i in range(len(path) - 1):
                        a, b = path[i], path[i + 1]
                        over = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
                        op = pods.get(over)
                        if op is not None and op["owner"] != me:
                            del pods[over]
                            supply[me] += len(op["prongs"])  # banked prongs return
                            progressed = True
            pods[to] = pod
            if to in BASES[1 - me]:
                winner = me

        if winner is None:
            # capture-all win
            opp_pods = [c for c, p in pods.items() if p["owner"] == 1 - me]
            if not opp_pods:
                winner = me

        no_progress = 0 if progressed else s.no_progress + 1
        draw = winner is None and no_progress >= NO_PROGRESS_CAP
        return OctiState(pods=pods, supply=supply, to_move=1 - me,
                         winner=winner, draw=draw, no_progress=no_progress)

    def is_terminal(self, s: OctiState) -> bool:
        return s.winner is not None or s.draw

    def returns(self, s: OctiState) -> list[float]:
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    # ---- serialization ---------------------------------------------------

    def serialize(self, s: OctiState) -> dict:
        return {
            "pods": {f"{c},{r}": {"owner": p["owner"],
                                  "prongs": sorted(p["prongs"])}
                     for (c, r), p in s.pods.items()},
            "supply": list(s.supply),
            "to_move": s.to_move,
            "winner": s.winner,
            "draw": s.draw,
            "no_progress": s.no_progress,
        }

    def deserialize(self, d: dict) -> OctiState:
        return OctiState(
            pods={_cell(k): {"owner": v["owner"],
                             "prongs": frozenset(v["prongs"])}
                  for k, v in d["pods"].items()},
            supply=list(d["supply"]),
            to_move=d["to_move"],
            winner=d["winner"],
            draw=d.get("draw", False),
            no_progress=d.get("no_progress", 0),
        )

    # ---- move notation ---------------------------------------------------

    def describe_move(self, s: OctiState, move: str) -> str:
        if move == "pass":
            return "pass"
        body, _, choice = move.partition("=")
        if ">" not in body:
            return f"+{choice}@{body}"
        path = body.replace(">", "→")
        if choice == "CAP":
            return f"{path} x"
        return path

    # ---- render ----------------------------------------------------------

    def render(self, s: OctiState, perspective=None) -> dict:
        pieces = []
        for (c, r), pod in s.pods.items():
            pieces.append({
                "cell": f"{c},{r}",
                "owner": pod["owner"],
                "prongs": sorted(pod["prongs"]),
            })
        # mark base squares with terrain tints
        tints = {}
        for cell in BASES[0]:
            tints[f"{cell[0]},{cell[1]}"] = "#e8c3bb"  # faint red (seat 0 home)
        for cell in BASES[1]:
            tints[f"{cell[0]},{cell[1]}"] = "#bcc8e8"  # faint blue (seat 1 home)

        if self.is_terminal(s):
            if s.draw:
                caption = "Draw"
            else:
                caption = f"{NAMES[s.winner]} wins"
        else:
            caption = (f"{NAMES[s.to_move]} to move  |  "
                       f"prongs — {NAMES[0]}: {s.supply[0]}, "
                       f"{NAMES[1]}: {s.supply[1]}")
        return {
            "board": {"type": "square", "width": WIDTH, "height": HEIGHT,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [],
            "caption": caption,
        }
