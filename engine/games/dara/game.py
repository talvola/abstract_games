"""Dara (Dakon / Doki / Derrah) -- a West African 'running-three' game.

Two phases on a filled rectangular grid (standard 6 columns x 5 rows = 30 cells,
12 pieces each):

* PLACEMENT ("drop"): players alternately drop one piece on any empty cell until
  all 24 are placed. Three-in-a-rows formed during the drop do NOT capture, and
  forming a line of FOUR OR MORE of your own pieces is illegal at any time --
  during the drop such a placement is simply not offered.

* MOVEMENT: a player slides one of their pieces one step orthogonally to an
  adjacent empty cell. If this forms a NEW orthogonal line of EXACTLY THREE of
  the mover's pieces (a line of four or more does not count and the move that
  would create one is illegal), the mover removes one enemy piece that is not
  itself part of an enemy three. Multiple threes formed by one move still yield
  exactly one capture.

WIN: a player who can no longer form any three (typically reduced to fewer than
three pieces) or who has no legal move loses.

Anti-shuffle: see ``_scoring_threes`` -- a three only scores if the piece that
just moved was NOT already part of that same line of three before the move
(i.e. you cannot slide a piece out of and straight back into the same three to
re-score it). A hard no-progress ply cap forces a draw.

Coordinates are ``"c,r"`` (column 0..W-1, row 0..H-1).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agp.game import Game


def _parse_size(size):
    # "<cols>x<rows>"
    c, r = size.lower().split("x")
    return int(c), int(r)


@dataclass
class DState:
    pos: dict = field(default_factory=dict)        # "c,r" -> player (0/1)
    to_move: int = 0
    placed: list = field(default_factory=lambda: [0, 0])  # pieces dropped per player
    removing: bool = False                          # a three was formed; remove an enemy
    # anti-shuffle: per player, the set of own three-lines (as frozensets of
    # cells) that the player's *immediately preceding* move dismantled. A line
    # in this set may not be re-scored on the very next move by that player.
    broke: list = field(default_factory=lambda: [frozenset(), frozenset()])
    no_progress: int = 0                            # plies since last capture (draw clock)
    width: int = 6
    height: int = 5
    pieces_each: int = 12
    winner: object = None


class Dara(Game):
    uid = "dara"
    name = "Dara"
    DRAW_PLIES = 60     # movement plies with no capture -> draw

    @property
    def num_players(self):
        return 2

    def current_player(self, state):
        return state.to_move

    # ---- geometry ----------------------------------------------------------
    def initial_state(self, options=None, rng=None):
        opts = options or {}
        w, h = _parse_size(opts.get("size", "6x5"))
        return DState(width=w, height=h, pieces_each=12)

    def _cells(self, st):
        return [f"{c},{r}" for r in range(st.height) for c in range(st.width)]

    def _xy(self, cell):
        c, r = cell.split(",")
        return int(c), int(r)

    def _neighbors(self, st, cell):
        c, r = self._xy(cell)
        out = []
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nc, nr = c + dc, r + dr
            if 0 <= nc < st.width and 0 <= nr < st.height:
                out.append(f"{nc},{nr}")
        return out

    # ---- run-length helpers ------------------------------------------------
    def _run_len(self, pos, cell, owner, dc, dr):
        """Length of the maximal contiguous run of `owner` through `cell` along
        the (dc,dr) axis, given the placement `pos` (cell assumed = owner)."""
        c, r = self._xy(cell)
        n = 1
        # forward
        x, y = c + dc, r + dr
        while pos.get(f"{x},{y}") == owner:
            n += 1
            x += dc
            y += dr
        # backward
        x, y = c - dc, r - dr
        while pos.get(f"{x},{y}") == owner:
            n += 1
            x -= dc
            y -= dr
        return n

    def _max_run(self, pos, cell, owner):
        """Longest orthogonal run of `owner` through `cell` (max of H and V)."""
        h = self._run_len(pos, cell, owner, 1, 0)
        v = self._run_len(pos, cell, owner, 0, 1)
        return max(h, v)

    def _run_cells(self, pos, cell, owner, dc, dr):
        """The set of cells in the maximal run of `owner` through `cell`."""
        c, r = self._xy(cell)
        cells = {cell}
        x, y = c + dc, r + dr
        while pos.get(f"{x},{y}") == owner:
            cells.add(f"{x},{y}")
            x += dc
            y += dr
        x, y = c - dc, r - dr
        while pos.get(f"{x},{y}") == owner:
            cells.add(f"{x},{y}")
            x -= dc
            y -= dr
        return cells

    def _exact_three_lines(self, pos, cell, owner):
        """Return list of frozensets, one per axis where `cell` sits in a run of
        EXACTLY three of `owner` (not 4+)."""
        out = []
        for dc, dr in ((1, 0), (0, 1)):
            if self._run_len(pos, cell, owner, dc, dr) == 3:
                out.append(frozenset(self._run_cells(pos, cell, owner, dc, dr)))
        return out

    # ---- move legality -----------------------------------------------------
    def _placement_ok(self, st, cell, owner):
        """A drop is illegal if it would create a run of FOUR OR MORE."""
        pos = dict(st.pos)
        pos[cell] = owner
        return self._max_run(pos, cell, owner) < 4

    def _move_ok(self, st, frm, to, owner):
        """A slide is illegal if it would create a run of FOUR OR MORE of owner."""
        pos = dict(st.pos)
        del pos[frm]
        pos[to] = owner
        return self._max_run(pos, to, owner) < 4

    # ---- moves -------------------------------------------------------------
    def legal_moves(self, state):
        if self.is_terminal(state):
            return []
        pl = state.to_move
        if state.removing:
            return self._removable(state, 1 - pl)
        if self._phase_placing(state, pl):
            return [c for c in self._cells(state)
                    if c not in state.pos and self._placement_ok(state, c, pl)]
        # movement phase
        out = []
        for cell, v in state.pos.items():
            if v != pl:
                continue
            for nb in self._neighbors(state, cell):
                if nb in state.pos:
                    continue
                if self._move_ok(state, cell, nb, pl):
                    out.append(f"{cell}>{nb}")
        return out

    def _phase_placing(self, state, pl):
        return state.placed[pl] < state.pieces_each

    def _on_board(self, state, pl):
        return sum(1 for v in state.pos.values() if v == pl)

    def _removable(self, state, enemy):
        """Enemy pieces that may be removed: those not part of an enemy three.
        If every enemy piece is in a three, any enemy piece may be removed."""
        men = [p for p, v in state.pos.items() if v == enemy]
        free = [p for p in men
                if not self._exact_three_lines(state.pos, p, enemy)]
        return free if free else men

    def _formed_threes(self, st, frm, to, pl):
        """Exact-three lines of `pl` that EXIST after the slide frm->to and pass
        through the destination cell `to`. (Candidate scoring lines.)"""
        pos = dict(st.pos)
        del pos[frm]
        pos[to] = pl
        return self._exact_three_lines(pos, to, pl)

    def _broken_threes(self, st, frm, to, pl):
        """Exact-three lines of `pl` that the slide frm->to DISMANTLED: lines of
        three that stood (through `frm`) before the move but no longer stand."""
        before = set(self._exact_three_lines(st.pos, frm, pl))
        pos = dict(st.pos)
        del pos[frm]
        pos[to] = pl
        # a line is broken if it contained frm and is no longer a complete three
        broken = set()
        for line in before:
            if all(pos.get(c) == pl for c in line):
                continue        # still intact (shouldn't happen since frm left)
            broken.add(line)
        return broken

    def apply_move(self, state, move, rng=None):
        pl = state.to_move
        pos = dict(state.pos)
        placed = list(state.placed)
        no_progress = state.no_progress

        if state.removing:
            del pos[move]
            ns = self._mk(state, pos, 1 - pl, placed, False,
                          broke=[frozenset(), frozenset()], no_progress=0)
            return self._settle(ns)

        if ">" in move:                              # movement
            frm, to = move.split(">")
            broken = self._broken_threes(state, frm, to, pl)
            pos[to] = pos.pop(frm)
            no_progress += 1
            formed = self._formed_threes(state, frm, to, pl)
            # anti-shuffle: a freshly-formed three does not score if it is one
            # the SAME player dismantled on their immediately preceding move
            # (break-and-remake), nor if the moved piece merely shuffled within
            # the line (frm already in the line).
            recent = state.broke[pl]
            scoring = [s for s in formed if s not in recent and frm not in s]
            # the player's broken-line memory for THIS move (used next turn)
            broke = list(state.broke)
            broke[pl] = frozenset(broken)   # records only the mover's own move
            if scoring and self._has_enemy(pos, 1 - pl):
                ns = self._mk(state, pos, pl, placed, True,
                              broke=broke, no_progress=no_progress)
                return ns
            ns = self._mk(state, pos, 1 - pl, placed, False,
                          broke=broke, no_progress=no_progress)
            return self._settle(ns)

        # placement (drop) -- threes never capture here
        pos[move] = pl
        placed[pl] += 1
        ns = self._mk(state, pos, 1 - pl, placed, False,
                      broke=[frozenset(), frozenset()], no_progress=0)
        return self._settle(ns)

    def _has_enemy(self, pos, enemy):
        return any(v == enemy for v in pos.values())

    def _mk(self, state, pos, to_move, placed, removing, broke, no_progress):
        return DState(pos=pos, to_move=to_move, placed=placed, removing=removing,
                      broke=broke, no_progress=no_progress, width=state.width,
                      height=state.height, pieces_each=state.pieces_each,
                      winner=state.winner)

    def _settle(self, ns):
        """At the start of ns.to_move's turn decide loss by reduction / stuck."""
        if ns.winner is not None:
            return ns
        pl = ns.to_move
        if not self._phase_placing(ns, pl):
            # cannot possibly form a three with < 3 pieces -> loss
            if self._on_board(ns, pl) < 3:
                ns.winner = 1 - pl
                return ns
            # no legal move -> loss (but not when the game is a no-progress draw)
            if ns.no_progress < self.DRAW_PLIES and not self.legal_moves(ns):
                ns.winner = 1 - pl
        return ns

    # ---- terminal ----------------------------------------------------------
    def _draw(self, state):
        return state.winner is None and state.no_progress >= self.DRAW_PLIES

    def is_terminal(self, state):
        return state.winner is not None or self._draw(state)

    def returns(self, state):
        if state.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == state.winner else -1.0 for i in range(2)]

    # ---- serialize ---------------------------------------------------------
    @staticmethod
    def _enc_broke(lines):
        # set-of-frozensets -> canonical sorted list of sorted lists
        return sorted(sorted(line) for line in lines)

    @staticmethod
    def _dec_broke(data):
        return frozenset(frozenset(line) for line in (data or []))

    def serialize(self, state):
        return {
            "pos": dict(state.pos),
            "to_move": state.to_move,
            "placed": list(state.placed),
            "removing": state.removing,
            "broke": [self._enc_broke(state.broke[0]),
                      self._enc_broke(state.broke[1])],
            "no_progress": state.no_progress,
            "width": state.width,
            "height": state.height,
            "pieces_each": state.pieces_each,
            "winner": state.winner,
        }

    def deserialize(self, d):
        broke = d.get("broke", [[], []])
        return DState(
            pos=dict(d["pos"]),
            to_move=d["to_move"],
            placed=list(d["placed"]),
            removing=d.get("removing", False),
            broke=[self._dec_broke(broke[0]), self._dec_broke(broke[1])],
            no_progress=d.get("no_progress", 0),
            width=d.get("width", 6),
            height=d.get("height", 5),
            pieces_each=d.get("pieces_each", 12),
            winner=d.get("winner"),
        )

    # ---- presentation ------------------------------------------------------
    def describe_move(self, state, move):
        if state.removing:
            return f"x{move}"
        if ">" in move:
            return move.replace(">", "-")
        return f"@{move}"

    def render(self, state, perspective=None):
        names = {0: "White", 1: "Black"}
        pieces = [{"cell": c, "owner": v} for c, v in state.pos.items()]
        if state.winner is not None:
            cap = f"{names[state.winner]} wins"
        elif self._draw(state):
            cap = "Draw"
        elif state.removing:
            cap = f"{names[state.to_move]}: remove an enemy piece"
        elif self._phase_placing(state, state.to_move):
            left = state.pieces_each - state.placed[state.to_move]
            cap = f"{names[state.to_move]} to place ({left} in hand)"
        else:
            cap = f"{names[state.to_move]} to move"
        return {
            "board": {"type": "square", "width": state.width, "height": state.height},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
