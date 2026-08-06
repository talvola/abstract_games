"""Carnac -- Emiliano "Wentu" Venturini, 2014 (HUCH! & friends).

Implemented from the publisher's own rulebook (the HUCH! 2014 multilingual
sheet, InDesign/2014-07-15, mirrored at
https://www.bordspellenstore.nl/wp-content/uploads/2018/02/Spelregels-Carnac.pdf
-- German pp.1-2 and English pp.3-4 are the same text) plus the designer's
component description on BGG 103061, and differentialled against the
AbstractPlay `gameslib` reference implementation (see `_diff_ap.py`).

THE PIECE.  All 28 megaliths are identical 2x1x1 dicubes.  BGG's official
description states the painting exactly: "three faces (one square and two
OPPOSED rectangular ones) of one color and the other three faces of the other
color".  So

  * the two SQUARE ends are opposite colours -- standing, the placer chooses
    which colour shows on top by which end is up;
  * of the four LONG faces, OPPOSITE ones share a colour and ADJACENT ones
    differ.  Every megalith photo and render in the rulebook agrees: no
    picture anywhere shows two adjacent long faces of one colour.

Standing on a cell, a megalith shows its top square end.  Toppled, it lies
across two cells and both of them show the SAME long face (each long face
carries two symbols -- see the rulebook's "6 white symbols border on each
other" figure).  Pushing the stone over in direction d brings up the long face
that was pointing AWAY from d, so:

  * toppling NORTH or SOUTH brings up the same long-face pair, and
  * toppling EAST or WEST brings up the other pair, which is the other colour.

The placer therefore chooses two independent bits -- the colour standing on
top, and which colour a north/south topple would reveal -- which is exactly
the four orientations offered as the move's "=CHOICE" suffix.

THE TURN ("I cut, you choose").  Player A stands a megalith on any empty
square.  Player B then either

  (i) TOPPLES it -- laying it on two empty squares in one orthogonal direction,
      freeing the square it stood on -- and then places a megalith of their
      own, after which it is A's turn to decide about B's new stone; or
  (ii) DECLINES, in which case the turn goes straight back to A, who stands
      another megalith ("then it is his opponent's (B) turn again. He then
      places a further megalith" -- rulebook (ii)).

If the new stone CANNOT be toppled at all, B does not get the choice but still
takes their turn ("if your opponent is not able to tilt the last placed
megalith, then it is still his turn and he may place a new megalith").

This module splits that turn into two plies for the same seat: from the "tip"
phase the decider plays a topple (or "pass"), and from the "place" phase the
seat on turn stands a stone.  `current_player` handles both, as SPEC.md allows.

SCORING.  A DOLMEN is an orthogonally-connected group of at least three
squares showing one colour, read from directly above ("Gewertet wird aus der
Vogelperspektive").  Diagonal contact does not connect.  The player with the
MOST dolmens wins; equal counts are broken by the largest dolmen, then the
next largest, and so on ("Der Spieler mit den meisten Dolmen gewinnt das
Spiel.  Bei Gleichstand gewinnt der Spieler mit dem groessten Dolmen.  Weitere
Gleichstaende werden von den jeweils naechstkleineren Dolmen entschieden.").
Count comes FIRST: "Bei CARNAC zaehlt die Anzahl der Dolmen und nicht unbedingt
deren Groesse", and merging two of your own dolmens into one destroys a point.
If every dolmen matches, the game is an honest DRAW -- the sheet's tie-break
chain simply runs out.

The game ends the instant the common stock of 28 is exhausted or the board has
no empty square left ("Das Spiel endet sofort").  So the 28th megalith is
never toppled.

Seat 0 is RED and moves first, seat 1 is BLUE (the physical game is red vs
white; blue is this platform's second seat colour).  Neither colour belongs to
a player's stones -- the stock is common and a placer may show either colour.

TERMINATION (no ply cap is needed, and none is used).  Every "place" ply spends
one megalith from the common stock, and every "tip" ply (a topple or a pass) is
immediately followed by a "place" ply, because the tip phase's successor is
always the place phase and the place phase's only moves are placements.  So
plies <= 2 * 28 = 56 whatever the players do, and no state repeats.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from agp.game import Game

RED, BLUE = 0, 1
SEAT_NAMES = ("Red", "Blue")
LETTERS = ("R", "B")
SEAT_OF = {"R": RED, "B": BLUE}

STOCK = 28

# North, East, South, West.  Row 0 is the BOTTOM row, so north is +row -- the
# same convention the renderer uses (it draws row 0 at the bottom).
DIRS = ((0, 1), (1, 0), (0, -1), (-1, 0))
DIR_NAMES = ("north", "east", "south", "west")

BOARDS = {"8x5": (8, 5), "10x7": (10, 7), "14x9": (14, 9)}

PHASE_PLACE = "place"
PHASE_TIP = "tip"


def cell_id(w, idx):
    return f"{idx % w},{idx // w}"


def cell_name(w, idx):
    """Board-printed algebraic name, 'a1' bottom-left (== AbstractPlay's files)."""
    return chr(ord("a") + idx % w) + str(idx // w + 1)


def parse_cell(w, h, s):
    try:
        c, r = (int(x) for x in s.split(","))
    except Exception:
        raise ValueError(f"malformed cell: {s!r}")
    if not (0 <= c < w and 0 <= r < h):
        raise ValueError(f"cell off the board: {s}")
    return r * w + c


@dataclass(frozen=True)
class CState:
    w: int = 10
    h: int = 7
    # One entry per OCCUPIED CELL, sorted by index:
    #   (idx, top_colour, partner_idx)   partner_idx == -1 for a standing stone,
    # otherwise the other cell of the same toppled megalith.
    board: tuple = ()
    reserve: int = STOCK
    phase: str = PHASE_PLACE
    # The stone awaiting the opponent's topple decision: (idx, top, ns) where
    # `ns` is the colour a north/south topple would bring up.  None outside the
    # tip phase.
    pend: object = None
    to_move: int = RED
    last: tuple = ()             # cells to highlight


def _sorted_board(entries):
    return tuple(sorted(entries, key=lambda e: e[0]))


class Carnac(Game):

    @property
    def num_players(self):
        return 2

    # ---- setup ---------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        key = str(opts.get("board", "10x7"))
        if key not in BOARDS:
            key = "10x7"
        w, h = BOARDS[key]
        return CState(w=w, h=h, board=(), reserve=STOCK,
                      phase=PHASE_PLACE, pend=None, to_move=RED, last=())

    def current_player(self, state):
        return state.to_move

    # ---- geometry ------------------------------------------------------
    @staticmethod
    def occupied(state):
        return {e[0] for e in state.board}

    @classmethod
    def empties(cls, state):
        occ = cls.occupied(state)
        return [i for i in range(state.w * state.h) if i not in occ]

    @classmethod
    def topple_options(cls, state, idx):
        """[(dir_index, near_idx, far_idx)] for toppling the stone on `idx`.

        A topple needs the two cells beyond it in that direction to be on the
        board and empty; the square it stood on is freed by the topple itself
        and is never one of them.
        """
        w, h = state.w, state.h
        occ = cls.occupied(state)
        c, r = idx % w, idx // w
        out = []
        for d, (dc, dr) in enumerate(DIRS):
            c1, r1, c2, r2 = c + dc, r + dr, c + 2 * dc, r + 2 * dr
            if not (0 <= c1 < w and 0 <= r1 < h and 0 <= c2 < w and 0 <= r2 < h):
                continue
            near, far = r1 * w + c1, r2 * w + c2
            if near in occ or far in occ:
                continue
            out.append((d, near, far))
        return out

    @staticmethod
    def topple_colour(ns, d):
        """Colour brought up by toppling in direction `d`.

        Opposite long faces share a colour, so north and south reveal the same
        pair (`ns`) and east and west reveal the other one.
        """
        return ns if DIRS[d][0] == 0 else 1 - ns

    # ---- rules ---------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        w = state.w
        if state.phase == PHASE_TIP:
            idx = state.pend[0]
            out = [f"{cell_id(w, idx)}>{cell_id(w, near)}"
                   for _, near, _ in self.topple_options(state, idx)]
            out.append("pass")
            return out
        out = []
        for idx in self.empties(state):
            cell = cell_id(w, idx)
            for top in (RED, BLUE):
                for ns in (RED, BLUE):
                    out.append(f"{cell}={LETTERS[top]}{LETTERS[ns]}")
        return out

    def apply_move(self, state, move, rng=None):
        if self.is_terminal(state):
            raise ValueError("the game is over")
        w, h = state.w, state.h

        if move == "pass":
            if state.phase != PHASE_TIP:
                raise ValueError("nothing to leave standing")
            # Declining hands the turn straight back to the player who stood
            # the stone -- rulebook action (ii).
            return replace(state, phase=PHASE_PLACE, pend=None,
                           to_move=1 - state.to_move, last=(state.pend[0],))

        if ">" in move:
            if state.phase != PHASE_TIP:
                raise ValueError("nothing to topple")
            src, _, dst = move.partition(">")
            idx = parse_cell(w, h, src)
            near = parse_cell(w, h, dst)
            if idx != state.pend[0]:
                raise ValueError(f"not the stone awaiting a decision: {move}")
            chosen = [o for o in self.topple_options(state, idx) if o[1] == near]
            if not chosen:
                raise ValueError(f"illegal topple: {move}")
            d, near, far = chosen[0]
            colour = self.topple_colour(state.pend[2], d)
            board = [e for e in state.board if e[0] != idx]
            board.append((near, colour, far))
            board.append((far, colour, near))
            # The toppler places their own stone next, so the seat does not change.
            return replace(state, board=_sorted_board(board), phase=PHASE_PLACE,
                           pend=None, last=(near, far))

        # ---- a placement -------------------------------------------------
        if state.phase != PHASE_PLACE:
            raise ValueError(f"not a placement phase: {move}")
        cell, _, choice = move.partition("=")
        if len(choice) != 2 or choice[0] not in SEAT_OF or choice[1] not in SEAT_OF:
            raise ValueError(f"malformed orientation: {move!r}")
        idx = parse_cell(w, h, cell)
        if idx in self.occupied(state):
            raise ValueError(f"square already occupied: {cell}")
        top, ns = SEAT_OF[choice[0]], SEAT_OF[choice[1]]

        board = _sorted_board(list(state.board) + [(idx, top, -1)])
        reserve = state.reserve - 1
        nxt = replace(state, board=board, reserve=reserve, phase=PHASE_PLACE,
                      pend=None, to_move=1 - state.to_move, last=(idx,))
        if reserve == 0 or len(board) == w * h:
            # "Das Spiel endet sofort" -- the last megalith is never toppled.
            return nxt
        if self.topple_options(nxt, idx):
            return replace(nxt, phase=PHASE_TIP, pend=(idx, top, ns))
        # Cannot be toppled: the opponent gets no choice but still takes a turn.
        return nxt

    def is_terminal(self, state):
        return state.reserve == 0 or len(state.board) == state.w * state.h

    # ---- scoring -------------------------------------------------------
    @staticmethod
    def dolmen_sizes(state, seat):
        """Sizes of that colour's dolmens (orthogonal groups of >= 3), descending."""
        w, h = state.w, state.h
        own = {e[0] for e in state.board if e[1] == seat}
        seen = set()
        sizes = []
        for start in sorted(own):
            if start in seen:
                continue
            seen.add(start)
            todo = [start]
            n = 0
            while todo:
                cur = todo.pop()
                n += 1
                c, r = cur % w, cur // w
                for dc, dr in DIRS:
                    c2, r2 = c + dc, r + dr
                    if 0 <= c2 < w and 0 <= r2 < h:
                        j = r2 * w + c2
                        if j in own and j not in seen:
                            seen.add(j)
                            todo.append(j)
            if n >= 3:
                sizes.append(n)
        sizes.sort(reverse=True)
        return tuple(sizes)

    @classmethod
    def scores(cls, state):
        return (cls.dolmen_sizes(state, RED), cls.dolmen_sizes(state, BLUE))

    @staticmethod
    def compare(a, b):
        """+1 if the dolmen list `a` beats `b`, -1 if it loses, 0 if identical.

        Most dolmens first; then the largest, then the next largest, and so on.
        """
        if len(a) != len(b):
            return 1 if len(a) > len(b) else -1
        for x, y in zip(a, b):
            if x != y:
                return 1 if x > y else -1
        return 0

    def returns(self, state):
        red, blue = self.scores(state)
        c = self.compare(red, blue)
        if c > 0:
            return [1.0, -1.0]
        if c < 0:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    # ---- persistence ---------------------------------------------------
    def serialize(self, state):
        return {
            "w": state.w,
            "h": state.h,
            "board": [[int(i), int(t), int(p)] for i, t, p in state.board],
            "reserve": int(state.reserve),
            "phase": state.phase,
            "pend": (None if state.pend is None
                     else [int(x) for x in state.pend]),
            "to_move": int(state.to_move),
            "last": [int(i) for i in state.last],
        }

    def deserialize(self, data):
        pend = data.get("pend")
        return CState(
            w=int(data["w"]),
            h=int(data["h"]),
            board=_sorted_board(tuple(int(x) for x in e) for e in data["board"]),
            reserve=int(data["reserve"]),
            phase=str(data["phase"]),
            pend=(None if pend is None else tuple(int(x) for x in pend)),
            to_move=int(data["to_move"]),
            last=tuple(int(i) for i in data["last"]),
        )

    # ---- notation ------------------------------------------------------
    def describe_move(self, state, move):
        w, h = state.w, state.h
        if move == "pass":
            if state.pend is None:
                return "pass"
            return f"leave {cell_name(w, state.pend[0])} standing"
        if ">" in move:
            src, _, dst = move.partition(">")
            idx = parse_cell(w, h, src)
            near = parse_cell(w, h, dst)
            hit = [o for o in self.topple_options(state, idx) if o[1] == near]
            if not hit or state.pend is None:
                return move
            d, near, far = hit[0]
            colour = self.topple_colour(state.pend[2], d)
            return (f"topple {cell_name(w, idx)} {DIR_NAMES[d]} onto "
                    f"{cell_name(w, near)}-{cell_name(w, far)} "
                    f"({SEAT_NAMES[colour]} up)")
        cell, _, choice = move.partition("=")
        if len(choice) != 2 or choice[0] not in SEAT_OF or choice[1] not in SEAT_OF:
            return move
        idx = parse_cell(w, h, cell)
        top, ns = SEAT_OF[choice[0]], SEAT_OF[choice[1]]
        return (f"stand {cell_name(w, idx)} ({SEAT_NAMES[top]} up, "
                f"N/S {SEAT_NAMES[ns]}, E/W {SEAT_NAMES[1 - ns]})")

    # ---- presentation --------------------------------------------------
    BAR = "#12100e"
    PEND = "#f2d271"

    def render(self, state, perspective=None):
        w, h = state.w, state.h
        pend_idx = None if state.pend is None else state.pend[0]

        pieces = []
        overlay = []
        paired = set()
        for idx, top, partner in state.board:
            # Every occupied cell is flooded in the colour it shows from above,
            # so the drawing IS the bird's-eye map the game is scored from and a
            # dolmen reads directly as one block of colour.
            pieces.append({"cell": cell_id(w, idx), "owner": top, "shape": "fill"})
            c, r = idx % w, idx // w
            if partner >= 0:
                key = (min(idx, partner), max(idx, partner))
                if key in paired:
                    continue
                paired.add(key)
                c2, r2 = partner % w, partner // w
                dc, dr = c2 - c, r2 - r
                # A bar through both centres: one toppled megalith reads as one
                # stone even where it merges into a bigger same-coloured dolmen.
                overlay.append([[c - 0.32 * dc, r - 0.32 * dr],
                                [c2 + 0.32 * dc, r2 + 0.32 * dr], self.BAR])
            else:
                # A standing menhir: a diamond, gold while it is the stone the
                # player on turn may topple.
                hot = idx == pend_idx
                k = 0.30 if hot else 0.19
                overlay.append([[c - k, r], [c, r + k], [c + k, r], [c, r - k],
                                [c - k, r], self.PEND if hot else self.BAR])

        highlights = [{"cell": cell_id(w, i), "kind": "last-move"} for i in state.last]
        if pend_idx is not None:
            # Emitted last so it wins the one-kind-per-cell merge in the renderer.
            highlights.append({"cell": cell_id(w, pend_idx), "kind": "goal"})

        spec = {
            "board": {"type": "square", "width": w, "height": h},
            "pieces": pieces,
            "caption": self.caption(state),
            "actionNames": {"pass": "Leave it standing (they place again)"},
            "choiceTitle": "Orientation: colour standing up, then when toppled",
            "choiceNames": {
                f"{LETTERS[t]}{LETTERS[n]}":
                    (f"{SEAT_NAMES[t]} up · N/S→{SEAT_NAMES[n]} "
                     f"· E/W→{SEAT_NAMES[1 - n]}")
                for t in (RED, BLUE) for n in (RED, BLUE)
            },
        }
        if overlay:
            spec["board"]["overlay"] = overlay
        if highlights:
            spec["highlights"] = highlights
        return spec

    def caption(self, state):
        red, blue = self.scores(state)
        tally = (f"dolmens Red {len(red)} ({self._sizes(red)}) "
                 f"vs Blue {len(blue)} ({self._sizes(blue)})")
        if self.is_terminal(state):
            c = self.compare(red, blue)
            if c > 0:
                return f"{SEAT_NAMES[RED]} wins — {tally}"
            if c < 0:
                return f"{SEAT_NAMES[BLUE]} wins — {tally}"
            return f"Draw — {tally}"
        who = SEAT_NAMES[state.to_move]
        if state.phase == PHASE_TIP:
            where = cell_name(state.w, state.pend[0])
            act = f"topple the new menhir on {where}, or leave it standing"
        else:
            act = "stand a menhir on any empty square"
        return f"{who} to move: {act} — {tally}, stock {state.reserve}"

    @staticmethod
    def _sizes(sizes):
        return ",".join(str(n) for n in sizes) if sizes else "-"
