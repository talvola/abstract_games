"""Veletas — Luis Bolaños Mures, 2013 (nestorgames). BGG id 151224.

A drawless territory game, a close relative of Amazons, played with SHARED
neutral "shooters" (weathervanes — veletas). Rules implemented from the
official nestorgames rulebook (nestorgames.com/rulebooks/VELETAS_EN.pdf;
Boardspace hosts a byte-identical copy):

* Setup (pie rule): the first player places floor(T/2) shooters and one Black
  stone on empty squares; the second player then chooses which player is Black
  ("swap" = take Black) and which is White; next White places the remaining
  shooters and one White stone. Setup shooters may NOT go on the board
  perimeter (that restriction applies only to the setup — shooters may MOVE to
  the perimeter later). From then on players alternate, Black first.
* Turn: you MAY move one unclaimed shooter like a chess queen to an empty
  square — the path may jump over shooters (claimed or not) but never over
  stones — then you MUST shoot: place a stone of your colour on an empty
  square in a straight orthogonal/diagonal line from the moved shooter (or
  from ANY unclaimed shooter, if none was moved), with no stones in between
  (shooters in between are fine). Claimed shooters cannot move or shoot.
* Claiming: after the shot, every TRAPPED unclaimed shooter (no legal move,
  i.e. no queen-line empty square reachable) is claimed by the player owning
  the biggest group of stones ORTHOGONALLY adjacent to it (a group = a set of
  like-coloured orthogonally connected stones; stones marking claims are not
  part of any group). If there is no adjacent group, or the biggest groups of
  each colour tie, the shooter goes to the OPPONENT of the player who just
  moved (the rulebook's worked example: White traps, sizes tie, Black claims).
* Win: claim a majority of the shooters — 4 of 7 (10x10), 3 of 5 (9x9),
  2 of 3 (7x7). "Draws are not possible" (rulebook): shooter counts are odd,
  every turn adds a stone (finite board), and a turn's shot always exists
  because a trapped shooter never survives unclaimed past the end of a turn.

Board sizes are the rulebook's own: the official 10x10 with 7 shooters, and
the suggested smaller 7x7 (3 shooters; first player places one) and 9x9
(5 shooters; first player places two) variants.

Move encoding (2-click friendly, no prefix traps):
* setup: single cells "c,r" — shooters first (interior only), then the stone;
* pie: action buttons "swap" (take Black) / "stay" (keep White);
* play: "from>to>shot" (move a shooter then shoot from it) or a single cell
  "c,r" (shoot from any unclaimed shooter without moving). Single-cell shots
  target empty cells while 3-part paths start on shooter cells, so the first
  click always disambiguates.

Seats: seat 0 is the first player; `black_seat` records who ended up Black
after the pie choice. Internally stones/turns are colours (0=Black, 1=White);
render/current_player/returns map colours to seats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

BLACK, WHITE = 0, 1  # colour roles: Black moves first in regular play
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
ORTH = [(1, 0), (-1, 0), (0, 1), (0, -1)]
SHOOTERS = {7: 3, 9: 5, 10: 7}  # board size -> total shooter count (rulebook)
COLS = "abcdefghij"


def _cell(s: str):
    c, r = s.split(",")
    return int(c), int(r)


def _fmt(p) -> str:
    return f"{p[0]},{p[1]}"


def _alg(p) -> str:
    return f"{COLS[p[0]]}{p[1] + 1}"


@dataclass
class VState:
    size: int = 9
    shooters: dict = field(default_factory=dict)  # (c,r) -> None | BLACK | WHITE (claim)
    stones: dict = field(default_factory=dict)    # (c,r) -> BLACK | WHITE
    phase: str = "setup1"   # setup1 | pie | setup2 | play
    left: int = 0           # shooters still to place in the current setup phase
    black_seat: int = 0     # which SEAT plays Black (decided in the pie phase)
    turn: int = BLACK       # colour to move (meaningful in the play phase)
    winner: Optional[int] = None  # SEAT index
    last: list = field(default_factory=list)      # cells of the previous move
    ply: int = 0


def _reach(pos, stones: dict, shooters: dict, size: int) -> list:
    """Queen-line landing squares from `pos`: every EMPTY square along each of
    the 8 rays. Stones block the ray; shooters are jumped over (never landed
    on). This is both a shooter's movement range and its shooting range."""
    out = []
    c, r = pos
    for dc, dr in DIRS:
        cc, rr = c + dc, r + dr
        while 0 <= cc < size and 0 <= rr < size:
            cell = (cc, rr)
            if cell in stones:
                break
            if cell not in shooters:
                out.append(cell)
            cc += dc
            rr += dr
    return out


def _group_size(start, stones: dict, cache: dict) -> int:
    """Size of the orthogonally-connected like-coloured group containing
    `start` (a stone cell). Memoised across one claim sweep via `cache`."""
    if start in cache:
        return cache[start]
    colour = stones[start]
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for dc, dr in ORTH:
            nb = (c + dc, r + dr)
            if nb not in seen and stones.get(nb) == colour:
                seen.add(nb)
                stack.append(nb)
    n = len(seen)
    for cell in seen:
        cache[cell] = n
    return n


def _run_claims(shooters: dict, stones: dict, size: int, mover: int) -> None:
    """Claim every trapped, still-unclaimed shooter (mutates `shooters`, which
    the caller has already copied). Attribution: the colour owning the biggest
    group orthogonally adjacent to the shooter; none/tie -> the opponent of
    `mover` (the colour that just shot). Order-independent: claiming changes
    no geometry (claim markers are not stones on the board)."""
    cache: dict = {}
    for pos, claim in shooters.items():
        if claim is not None:
            continue
        if _reach(pos, stones, shooters, size):
            continue  # not trapped
        best = [0, 0]
        c, r = pos
        for dc, dr in ORTH:
            nb = (c + dc, r + dr)
            if nb in stones:
                col = stones[nb]
                best[col] = max(best[col], _group_size(nb, stones, cache))
        if best[BLACK] > best[WHITE]:
            shooters[pos] = BLACK
        elif best[WHITE] > best[BLACK]:
            shooters[pos] = WHITE
        else:
            shooters[pos] = 1 - mover


class Veletas(Game):
    name = "Veletas"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> VState:
        size = int((options or {}).get("size", 9))
        if size not in SHOOTERS:
            raise ValueError(f"size must be one of {sorted(SHOOTERS)}")
        return VState(size=size, left=SHOOTERS[size] // 2)

    def _seat(self, s: VState, colour: int) -> int:
        return s.black_seat if colour == BLACK else 1 - s.black_seat

    def current_player(self, s: VState) -> int:
        if s.phase == "setup1":
            return 0
        if s.phase == "pie":
            return 1
        if s.phase == "setup2":
            return self._seat(s, WHITE)
        return self._seat(s, s.turn)

    # -- move generation ------------------------------------------------------

    def legal_moves(self, s: VState) -> list[str]:
        if self.is_terminal(s):
            return []
        if s.phase == "pie":
            return ["swap", "stay"]
        if s.phase in ("setup1", "setup2"):
            n = s.size
            if s.left > 0:  # setup shooters: interior squares only
                return [f"{c},{r}" for r in range(1, n - 1) for c in range(1, n - 1)
                        if (c, r) not in s.stones and (c, r) not in s.shooters]
            return [f"{c},{r}" for r in range(n) for c in range(n)
                    if (c, r) not in s.stones and (c, r) not in s.shooters]
        # play: optional shooter move + mandatory shot
        moves: list[str] = []
        targets: set = set()
        for p, claim in s.shooters.items():
            if claim is not None:
                continue
            dests = _reach(p, s.stones, s.shooters, s.size)
            targets.update(dests)  # stationary shot from p: same geometry
            for to in dests:
                sh2 = dict(s.shooters)
                del sh2[p]
                sh2[to] = None
                for t in _reach(to, s.stones, sh2, s.size):
                    moves.append(f"{_fmt(p)}>{_fmt(to)}>{_fmt(t)}")
        moves.extend(_fmt(t) for t in sorted(targets))
        return moves

    # -- move application -----------------------------------------------------

    def _finish_stone(self, shooters: dict, stones: dict, size: int,
                      mover: int, black_seat: int) -> Optional[int]:
        """Run the claim sweep after a stone lands; return the winning SEAT if
        a colour now holds a majority of the shooters, else None."""
        _run_claims(shooters, stones, size, mover)
        majority = SHOOTERS[size] // 2 + 1
        for col in (BLACK, WHITE):
            if sum(1 for cl in shooters.values() if cl == col) >= majority:
                return black_seat if col == BLACK else 1 - black_seat
        return None

    def apply_move(self, s: VState, move: str, rng=None) -> VState:
        if s.phase == "pie":
            if move not in ("swap", "stay"):
                raise ValueError(f"bad pie move: {move!r}")
            total = SHOOTERS[s.size]
            return VState(size=s.size, shooters=dict(s.shooters),
                          stones=dict(s.stones), phase="setup2",
                          left=total - total // 2,
                          black_seat=1 if move == "swap" else 0,
                          turn=BLACK, winner=None, last=[], ply=s.ply + 1)
        shooters = dict(s.shooters)
        stones = dict(s.stones)
        if s.phase in ("setup1", "setup2"):
            cell = _cell(move)
            if cell in stones or cell in shooters:
                raise ValueError(f"square {move} is occupied")
            if s.left > 0:
                if not (0 < cell[0] < s.size - 1 and 0 < cell[1] < s.size - 1):
                    raise ValueError("setup shooters may not go on the perimeter")
                shooters[cell] = None
                return VState(size=s.size, shooters=shooters, stones=stones,
                              phase=s.phase, left=s.left - 1,
                              black_seat=s.black_seat, turn=BLACK,
                              winner=None, last=[move], ply=s.ply + 1)
            colour = BLACK if s.phase == "setup1" else WHITE
            stones[cell] = colour
            # A claim here is geometrically impossible (setup shooters are all
            # interior and at most two stones exist), but run the sweep anyway.
            winner = self._finish_stone(shooters, stones, s.size, colour, s.black_seat)
            return VState(size=s.size, shooters=shooters, stones=stones,
                          phase="pie" if s.phase == "setup1" else "play",
                          left=0, black_seat=s.black_seat, turn=BLACK,
                          winner=winner, last=[move], ply=s.ply + 1)
        # play
        parts = move.split(">")
        if len(parts) == 3:
            frm, to, shot = (_cell(x) for x in parts)
            if shooters.get(frm, WHITE) is not None:  # missing or claimed
                raise ValueError(f"no unclaimed shooter on {parts[0]}")
            del shooters[frm]
            shooters[to] = None
            last = list(parts)
        else:
            shot = _cell(move)
            last = [move]
        if shot in stones or shot in shooters:
            raise ValueError(f"shot square {_fmt(shot)} is occupied")
        stones[shot] = s.turn
        winner = self._finish_stone(shooters, stones, s.size, s.turn, s.black_seat)
        return VState(size=s.size, shooters=shooters, stones=stones,
                      phase="play", left=0, black_seat=s.black_seat,
                      turn=1 - s.turn, winner=winner, last=last, ply=s.ply + 1)

    # -- termination / scoring --------------------------------------------------

    def is_terminal(self, s: VState) -> bool:
        return s.winner is not None

    def returns(self, s: VState) -> list[float]:
        return [1.0, -1.0] if s.winner == 0 else [-1.0, 1.0]

    # -- serialization ----------------------------------------------------------

    def serialize(self, s: VState) -> dict:
        return {
            "size": s.size,
            "shooters": {_fmt(p): cl for p, cl in sorted(s.shooters.items())},
            "stones": {_fmt(p): col for p, col in sorted(s.stones.items())},
            "phase": s.phase,
            "left": s.left,
            "black_seat": s.black_seat,
            "turn": s.turn,
            "winner": s.winner,
            "last": list(s.last),
            "ply": s.ply,
        }

    def deserialize(self, d: dict) -> VState:
        return VState(
            size=d["size"],
            shooters={_cell(k): cl for k, cl in d["shooters"].items()},
            stones={_cell(k): col for k, col in d["stones"].items()},
            phase=d["phase"],
            left=d.get("left", 0),
            black_seat=d.get("black_seat", 0),
            turn=d.get("turn", BLACK),
            winner=d.get("winner"),
            last=list(d.get("last", [])),
            ply=d.get("ply", 0),
        )

    # -- presentation -----------------------------------------------------------

    def describe_move(self, s: VState, move: str) -> str:
        if s.phase == "pie":
            return "swap (take Black)" if move == "swap" else "stay (keep White)"
        if s.phase in ("setup1", "setup2"):
            if s.left > 0:
                return f"shooter {_alg(_cell(move))}"
            colour = "Black" if s.phase == "setup1" else "White"
            return f"{colour} stone {_alg(_cell(move))}"
        parts = move.split(">")
        if len(parts) == 3:
            return f"{_alg(_cell(parts[0]))}-{_alg(_cell(parts[1]))}/{_alg(_cell(parts[2]))}"
        return f"shoot {_alg(_cell(move))}"

    def render(self, s: VState, perspective=None) -> dict:
        pieces = [{"cell": _fmt(p), "owner": self._seat(s, col), "label": ""}
                  for p, col in sorted(s.stones.items())]
        for p, cl in sorted(s.shooters.items()):
            owner = 2 if cl is None else self._seat(s, cl)
            pieces.append({"cell": _fmt(p), "owner": owner, "glyph": "✦"})
        highlights = [{"cell": c, "kind": "last-move"} for c in s.last
                      if ">" not in c and "," in c]
        claimed = [sum(1 for cl in s.shooters.values() if cl == col)
                   for col in (BLACK, WHITE)]
        majority = SHOOTERS[s.size] // 2 + 1
        tally = (f"claimed: Black {claimed[BLACK]} / White {claimed[WHITE]}"
                 f" (first to {majority})")
        if s.winner is not None:
            role = "Black" if s.winner == s.black_seat else "White"
            caption = f"Player {s.winner + 1} ({role}) wins — {tally}"
        elif s.phase == "setup1":
            what = (f"place a shooter ({s.left} to go, not on the edge)"
                    if s.left > 0 else "place the Black stone")
            caption = f"Player 1 — {what}"
        elif s.phase == "pie":
            caption = "Player 2 — swap (take Black) or stay (keep White)"
        elif s.phase == "setup2":
            seat = self._seat(s, WHITE)
            what = (f"place a shooter ({s.left} to go, not on the edge)"
                    if s.left > 0 else "place the White stone")
            caption = f"Player {seat + 1} (White) — {what}"
        else:
            seat = self._seat(s, s.turn)
            role = "Black" if s.turn == BLACK else "White"
            caption = (f"Player {seat + 1} ({role}) — move a shooter (optional), "
                       f"then shoot · {tally}")
        return {
            "board": {"type": "square", "width": s.size, "height": s.size},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
        }
