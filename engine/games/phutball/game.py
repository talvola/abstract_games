"""Phutball — Philosopher's Football (John H. Conway, *Winning Ways*).

Two players share a board of POINTS, a set of neutral MEN (stones owned by
neither player), and a single BALL. The players differ only in which GOAL LINE
they aim the ball at: player 0 attacks one short edge of the board, player 1 the
other.

A TURN is EITHER:
  (A) PLACE one man on any empty point (men are neutral; never the ball's point);
  (B) JUMP the ball through a chain of one or more jumps and stop. In one jump,
      from the ball pick one of the 8 directions; if the immediately adjacent
      point(s) in that direction form an unbroken line of >=1 men ending at an
      EMPTY point, the ball hops to that empty point and every jumped man is
      REMOVED. You may keep jumping from the new point (any direction) and you
      choose when to stop. You may NOT both place a man and jump in one turn.

WIN: a player wins when, as a result of their move, the ball lands ON or jumps
OVER their target goal line (the short edge they attack).

Coordinates are "c,r" (c = column 0..W-1, r = row 0..H-1). The two goal rows are
r == 0 (player 1's target) and r == H-1 (player 0's target).

Move notation (kept bounded so legal_moves never blows up combinatorially — see
the modelling note in rules.md):
  - a PLACEMENT is the point id, e.g. "7,9";
  - a ball JUMP is a SINGLE hop to its landing point, e.g. "7,11". A jump chain
    is played as successive single-hop moves by the SAME player (the ball-mover
    keeps the turn); after at least one hop the mover may also play "stop" to end
    the chain and pass. A landing "over" the goal line is encoded with row -1
    (off the r==0 edge) or H (off the r==H-1 edge) and ends the game immediately.
  - For the move log / UI, describe_move renders the running path with "→".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

# Owner codes for rendering. Players are 0 and 1; MEN are owner 2 (neutral).
MAN = 2
NAMES = {0: "Down", 1: "Up"}
DIRS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]

# Defensive ply cap (Phutball is finite in practice; this bounds pathological
# random self-play). Counts both placements and individual ball hops.
PLY_CAP = 600


def _parse_size(opt) -> tuple[int, int]:
    s = str(opt or "15x19")
    w, h = s.split("x")
    return int(w), int(h)


def _cell(s: str) -> tuple[int, int]:
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class PhutballState:
    width: int = 15
    height: int = 19
    men: frozenset = field(default_factory=frozenset)   # set of (c, r) holding a man
    ball: tuple = (7, 9)                                 # (c, r) of the ball
    to_move: int = 0
    winner: Optional[int] = None
    plies: int = 0
    # True once the ball-mover has made >=1 hop this turn (so "stop" is allowed
    # and placements are no longer allowed — the turn is now a ball turn).
    chaining: bool = False
    # The ball's position at the START of the current ball turn, kept only for a
    # nicer move-log path; not used by the rules.
    chain_start: Optional[tuple] = None


class Phutball(Game):
    uid = "phutball"
    name = "Phutball"

    @property
    def num_players(self) -> int:
        return 2

    # ----- goal geometry -------------------------------------------------
    def _crossed(self, s: PhutballState, player: int, r: int) -> bool:
        """True if landing-row `r` is ON or OVER `player`'s goal line.

        Player 0 attacks the bottom (large r): win if r >= height-1.
        Player 1 attacks the top (small r):    win if r <= 0.
        """
        if player == 0:
            return r >= s.height - 1
        return r <= 0

    def _in_play(self, s: PhutballState, c: int, r: int) -> bool:
        """A point that can hold a man / be a non-winning ball landing."""
        return 0 <= c < s.width and 0 <= r < s.height

    # ----- core ----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> PhutballState:
        w, h = _parse_size((options or {}).get("size", "15x19"))
        ball = (w // 2, h // 2)
        return PhutballState(width=w, height=h, men=frozenset(), ball=ball)

    def current_player(self, s: PhutballState) -> int:
        return s.to_move

    # ----- single-jump enumeration --------------------------------------
    def _single_jumps(self, s: PhutballState):
        """From the ball, yield (landing_pos, jumped_men_tuple) for each legal
        single hop. `landing_pos` may be an off-board winning point (row -1 or
        height) when it crosses the MOVER's goal line.
        """
        out = []
        c0, r0 = s.ball
        men = s.men
        for dc, dr in DIRS:
            jumped = []
            c, r = c0 + dc, r0 + dr
            while self._in_play(s, c, r) and (c, r) in men:
                jumped.append((c, r))
                c, r = c + dc, r + dr
            if not jumped:
                continue
            if self._in_play(s, c, r):
                if (c, r) not in men:           # empty landing point -> legal
                    out.append(((c, r), tuple(jumped)))
            else:
                # Off the board: legal only if it crosses the MOVER's goal line
                # (lands on/over the goal) AND the landing column stays on board.
                if 0 <= c < s.width and self._crossed(s, s.to_move, r):
                    out.append(((c, r), tuple(jumped)))
        return out

    def legal_moves(self, s: PhutballState) -> list[str]:
        if self.is_terminal(s):
            return []
        moves = []
        # Ball hops (always available if any exist).
        for (c, r), _ in self._single_jumps(s):
            moves.append(f"{c},{r}")
        if s.chaining:
            # Mid-chain: the mover may also stop (end the ball turn).
            moves.append("stop")
        else:
            # Fresh turn: placing a man is an alternative to starting a jump.
            ball = s.ball
            men = s.men
            for c in range(s.width):
                for r in range(s.height):
                    if (c, r) == ball or (c, r) in men:
                        continue
                    moves.append(f"{c},{r}")
        return moves

    def apply_move(self, s: PhutballState, move: str, rng=None) -> PhutballState:
        if move == "stop":
            # End the ball turn; pass to the opponent.
            return PhutballState(
                width=s.width, height=s.height, men=s.men, ball=s.ball,
                to_move=1 - s.to_move, winner=None, plies=s.plies + 1,
                chaining=False, chain_start=None,
            )

        target = _cell(move)

        # Is `target` a legal ball hop?
        hop = None
        for land, jumped in self._single_jumps(s):
            if land == target:
                hop = (land, jumped)
                break

        if hop is not None:
            land, jumped = hop
            new_men = set(s.men)
            for m in jumped:
                new_men.discard(m)
            won = self._crossed(s, s.to_move, land[1])
            if won:
                return PhutballState(
                    width=s.width, height=s.height, men=frozenset(new_men),
                    ball=land, to_move=1 - s.to_move, winner=s.to_move,
                    plies=s.plies + 1, chaining=False, chain_start=None,
                )
            # Continue the chain: same player keeps the move.
            return PhutballState(
                width=s.width, height=s.height, men=frozenset(new_men),
                ball=land, to_move=s.to_move, winner=None, plies=s.plies + 1,
                chaining=True,
                chain_start=s.chain_start if s.chaining else s.ball,
            )

        # Otherwise it must be a placement (only legal on a fresh turn).
        if s.chaining:
            raise ValueError(f"illegal move {move!r}: mid-chain, must hop or stop")
        new_men = set(s.men)
        new_men.add(target)
        return PhutballState(
            width=s.width, height=s.height, men=frozenset(new_men),
            ball=s.ball, to_move=1 - s.to_move, winner=None,
            plies=s.plies + 1, chaining=False, chain_start=None,
        )

    def is_terminal(self, s: PhutballState) -> bool:
        return s.winner is not None or s.plies >= PLY_CAP

    def returns(self, s: PhutballState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ----- serialization -------------------------------------------------
    def serialize(self, s: PhutballState) -> dict:
        return {
            "width": s.width,
            "height": s.height,
            "men": [f"{c},{r}" for (c, r) in sorted(s.men)],
            "ball": f"{s.ball[0]},{s.ball[1]}",
            "to_move": s.to_move,
            "winner": s.winner,
            "plies": s.plies,
            "chaining": s.chaining,
            "chain_start": (f"{s.chain_start[0]},{s.chain_start[1]}"
                            if s.chain_start is not None else None),
        }

    def deserialize(self, d: dict) -> PhutballState:
        cs = d.get("chain_start")
        return PhutballState(
            width=d["width"],
            height=d["height"],
            men=frozenset(_cell(k) for k in d["men"]),
            ball=_cell(d["ball"]),
            to_move=d["to_move"],
            winner=d["winner"],
            plies=d.get("plies", 0),
            chaining=d.get("chaining", False),
            chain_start=_cell(cs) if cs else None,
        )

    def describe_move(self, s: PhutballState, move: str) -> str:
        if move == "stop":
            return f"{NAMES[s.to_move]}: end ball chain"
        target = _cell(move)
        is_hop = any(land == target for land, _ in self._single_jumps(s))
        if is_hop:
            start = s.chain_start if s.chaining else s.ball
            return (f"{NAMES[s.to_move]}: ball "
                    f"{start[0]},{start[1]}→{target[0]},{target[1]}")
        return f"{NAMES[s.to_move]}: man {target[0]},{target[1]}"

    # ----- rendering -----------------------------------------------------
    def render(self, s: PhutballState, perspective=None) -> dict:
        pieces = [{"cell": f"{c},{r}", "owner": MAN, "label": ""}
                  for (c, r) in sorted(s.men)]
        bc, br = s.ball
        br_disp = min(max(br, 0), s.height - 1)
        pieces.append({"cell": f"{bc},{br_disp}",
                       "owner": s.winner if s.winner is not None else 0,
                       "label": "O", "ball": True})

        # goal-line tints: player 0 attacks bottom (r=h-1), player 1 the top (r=0)
        tints = {}
        for c in range(s.width):
            tints[f"{c},0"] = "#22324d"                  # top goal (player 1, Up)
            tints[f"{c},{s.height - 1}"] = "#4d2222"      # bottom goal (player 0, Down)

        if s.winner is not None:
            caption = f"{NAMES[s.winner]} wins"
        elif s.plies >= PLY_CAP:
            caption = "Draw (ply cap)"
        elif s.chaining:
            caption = f"{NAMES[s.to_move]}: continue jumping or stop"
        else:
            caption = f"{NAMES[s.to_move]} to move (place a man or jump the ball)"

        return {
            "board": {"type": "square", "width": s.width, "height": s.height,
                      "tints": tints},
            "pieces": pieces,
            "highlights": [{"cell": f"{bc},{br_disp}", "kind": "last-move"}],
            "caption": caption,
        }
