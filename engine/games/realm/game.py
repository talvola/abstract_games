"""Realm — Phil Orbanes (with Sid Sackson), Gamut of Games, 1973.

Implemented from the designer-maintained complete ruleset: "Realm" by
William L. Mikulas, Abstract Games magazine issue 9 (Spring 2002).
Mikulas and Stanley Levin acquired the rights from Orbanes; their article
explicitly supersedes the original rules (which lacked the rearrangement
limit and end-by-agreement, and used 13 Bases).

Board: 12x12 = 16 Realms of 3x3. Each Realm's middle square is its Center
(cells with col%3==1 and row%3==1); the other eight are Border Spaces.
Cells are "col,row", 0-based; col 0 = article file 'a', row 0 = article
rank 1. A player controls a Realm iff his Base is on its Center.

Pieces per player: 3 Powers (move like rooks, must end in a NEW Realm,
may pass through a vacant Center but never end on one), 8 Enforcers
(move like Powers but only the way they point; before moving the owner
may turn them 90 degrees left or right — never reverse — and they end
pointing the way they moved; immobilized Enforcers cannot move), and
12 Bases (created on Centers, never move).

TURN ENCODING (multi-sub-move pattern, cf. games/blooms):
  * setup: bases then powers are single-cell placements "c,r".
  * a normal piece move is "fc,fr>tc,tr" (cross-Realm by rule).  A turn is
    one or more such moves followed by "done"; the sequence must stay
    consistent with Dispersal (all sources share one Realm) or
    Concentration (all destinations share one Realm; >=2 pieces to finish
    that way — one move + done is always a legal 1-piece Dispersal).
  * a from>to move WITHIN one Realm starts a Rearrangement of that Realm
    (normal moves can never stay in a Realm, so the encoding is
    unambiguous): every own Power/Enforcer there must then be reassigned
    to a different space; mobile Enforcers carry a facing suffix "=N/S/E/W";
    the turn commits and ends automatically with the last assignment.
    No Special Events. A player may not rearrange the same Realm three of
    his turns in a row.
  * Special Events resolve after each individual piece move, in sub-move
    order.  A created Enforcer is a follow-up forced choice "c,r=D"
    (vacant Border Space in that Realm + facing).  When an Enforcer must
    immobilize one of SEVERAL mobile enemy Enforcers, the follow-up choice
    is that Enforcer's cell "c,r" (a single candidate resolves
    automatically).
  * "pass" (whole turn): the article ends the game "by agreement" when
    neither player can create another Base; two consecutive passes end
    the game (documented design decision in rules.md).

Game end: immediately ("as soon as") when a player's 12th Base is created
(setup placements count toward the 12) — even mid-turn; or double pass; or
a defensive hard ply cap (scored the same way).  Score: more controlled
Realms wins; tie -> greater (mobile Enforcers on board + uncreated
Enforcers); still equal -> honest draw.

Interpretations documented in rules.md: only Bases ever occupy Centers
(so rearrangement and Enforcer creation place on Border Spaces only —
matches every example in the article and the independent AbstractPlay
implementation); rearrangement moves EACH picked-up piece to a different
space (Bases stay put); a piece may move at most once per turn; a pass
breaks a rearrangement streak.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

SIZE = 12
N_BASES = 12
N_ENFORCERS = 8
N_POWERS = 3
MAX_PLY = 1000  # defensive hard cap on sub-moves; scored like a normal end

DIRS = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
GLYPH_MOBILE = {"N": "▲", "S": "▼", "E": "▶", "W": "◀"}
GLYPH_FROZEN = {"N": "△", "S": "▽", "E": "▷", "W": "◁"}
SEAT_NAMES = ("White", "Black")


def _realm(cell):
    return (cell[0] // 3, cell[1] // 3)


def _center(realm):
    return (3 * realm[0] + 1, 3 * realm[1] + 1)


def _is_center(cell):
    return cell[0] % 3 == 1 and cell[1] % 3 == 1


def _realm_cells(realm):
    C, R = realm
    return [(3 * C + dc, 3 * R + dr) for dr in range(3) for dc in range(3)]


def _cell(s: str):
    c, r = s.split(",")
    return (int(c), int(r))


def _cid(cell) -> str:
    return f"{cell[0]},{cell[1]}"


def _alg(cell) -> str:
    return f"{chr(ord('a') + cell[0])}{cell[1] + 1}"


# Piece = (owner, kind, dir, mobile); kind in "BPE"; dir None except Enforcers.


@dataclass
class RState:
    phase: str = "setup_b"              # setup_b | setup_p | play
    board: dict = field(default_factory=dict)   # (c,r) -> (owner, kind, dir, mobile)
    to_move: int = 0
    bases_created: list = field(default_factory=lambda: [0, 0])
    enf_created: list = field(default_factory=lambda: [0, 0])
    captured: list = field(default_factory=lambda: [0, 0])  # bases captured BY player
    tmode: Optional[str] = None          # None | "move" | "rearr"
    tmoves: list = field(default_factory=list)   # [(src, dst), ...] this turn
    locked: list = field(default_factory=list)   # cells that may not move again this turn
    rearr_realm: Optional[tuple] = None
    rearr_asg: list = field(default_factory=list)  # [(src, dst, dir|None), ...]
    pending: Optional[tuple] = None      # ("create", C, R) | ("immob", C, R, mover_cell)
    passes: int = 0
    rearr_hist: list = field(default_factory=lambda: [[None, 0], [None, 0]])
    ply: int = 0
    last: list = field(default_factory=list)     # cells to highlight
    over: bool = False
    winner: Optional[int] = None


def _copy(s: RState) -> RState:
    return RState(
        phase=s.phase, board=dict(s.board), to_move=s.to_move,
        bases_created=list(s.bases_created), enf_created=list(s.enf_created),
        captured=list(s.captured), tmode=s.tmode, tmoves=list(s.tmoves),
        locked=list(s.locked), rearr_realm=s.rearr_realm,
        rearr_asg=list(s.rearr_asg), pending=s.pending, passes=s.passes,
        rearr_hist=[list(h) for h in s.rearr_hist], ply=s.ply,
        last=list(s.last), over=s.over, winner=s.winner,
    )


def _ray_targets(board, cell, d):
    """Cells a rook-mover at ``cell`` may END on going direction ``d``."""
    out = []
    src_realm = _realm(cell)
    dc, dr = DIRS[d]
    c, r = cell[0] + dc, cell[1] + dr
    while 0 <= c < SIZE and 0 <= r < SIZE and (c, r) not in board:
        if _realm((c, r)) != src_realm and not _is_center((c, r)):
            out.append((c, r))
        c += dc
        r += dr
    return out


def _piece_moves(board, cell):
    """All (src, dst) normal moves for the piece at ``cell``."""
    owner, kind, d, mobile = board[cell]
    if kind == "P":
        dirs = "NESW"
    elif kind == "E" and mobile:
        dirs = [x for x in "NESW" if x != OPP[d]]
    else:
        return []
    res = []
    for dd in dirs:
        res.extend((cell, t) for t in _ray_targets(board, cell, dd))
    return res


def _seq_ok(seq):
    """Sequence of (src,dst) is still consistent with Dispersal or Concentration."""
    if len(seq) < 2:
        return True
    if len({_realm(s) for s, _ in seq}) == 1:
        return True   # Dispersal: one common source Realm
    if len({_realm(t) for _, t in seq}) == 1:
        return True   # Concentration: one common target Realm (sources are
    return False      # outside it automatically — moves must change Realm)


class Realm(Game):
    name = "Realm"

    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> RState:
        return RState()

    def current_player(self, s: RState) -> int:
        return s.to_move

    # ------------------------------------------------------------- helpers

    def _controlled(self, s, p):
        return sum(1 for v in s.board.values() if v[0] == p and v[1] == "B")

    def _enf_score(self, s, p):
        mobile = sum(1 for v in s.board.values()
                     if v[0] == p and v[1] == "E" and v[3])
        return mobile + (N_ENFORCERS - s.enf_created[p])

    def _finish(self, ns):
        ns.over = True
        r0, r1 = self._controlled(ns, 0), self._controlled(ns, 1)
        if r0 != r1:
            ns.winner = 0 if r0 > r1 else 1
        else:
            e0, e1 = self._enf_score(ns, 0), self._enf_score(ns, 1)
            ns.winner = None if e0 == e1 else (0 if e0 > e1 else 1)

    def _rearr_pieces_spaces(self, s, realm, p):
        cells = _realm_cells(realm)
        pieces = [c for c in cells
                  if c in s.board and s.board[c][0] == p and s.board[c][1] in "PE"]
        spaces = [c for c in cells if not _is_center(c)
                  and (c not in s.board
                       or (s.board[c][0] == p and s.board[c][1] != "B"))]
        return pieces, spaces

    @staticmethod
    def _rearr_feasible(pieces_left, spaces_left):
        """Can every remaining piece still get a space != its own?  Each piece
        excludes only its own cell, so Hall's condition can only fail for a
        final singleton stuck with exactly its own square."""
        if len(spaces_left) < len(pieces_left):
            return False
        if len(pieces_left) == 1 and spaces_left == [pieces_left[0]]:
            return False
        return True

    def _rearr_moves(self, s, realm, p, assigned):
        pieces, spaces = self._rearr_pieces_spaces(s, realm, p)
        asg_src = {a[0] for a in assigned}
        asg_dst = {a[1] for a in assigned}
        pieces_left = [c for c in pieces if c not in asg_src]
        spaces_left = [c for c in spaces if c not in asg_dst]
        out = []
        for pc in pieces_left:
            _, kind, d, mobile = s.board[pc]
            for t in spaces_left:
                if t == pc:
                    continue
                rem_p = [x for x in pieces_left if x != pc]
                rem_s = [x for x in spaces_left if x != t]
                if not self._rearr_feasible(rem_p, rem_s):
                    continue
                base = f"{_cid(pc)}>{_cid(t)}"
                if kind == "E" and mobile:
                    out.extend(f"{base}={dd}" for dd in "NESW")
                else:
                    out.append(base)
        return out

    # ------------------------------------------------------- move generation

    def legal_moves(self, s: RState) -> list[str]:
        if s.over:
            return []
        p = s.to_move

        if s.phase == "setup_b":
            own_realms = [_realm(c) for c, v in s.board.items()
                          if v[0] == p and v[1] == "B"]
            rows = {r[1] for r in own_realms}
            cols = {r[0] for r in own_realms}
            out = []
            for C in range(4):
                for R in range(4):
                    if C in cols or R in rows:
                        continue
                    ctr = _center((C, R))
                    if ctr not in s.board:
                        out.append(_cid(ctr))
            return out

        if s.phase == "setup_p":
            out = []
            for c, v in s.board.items():
                if v[0] == p and v[1] == "B":
                    realm = _realm(c)
                    cells = _realm_cells(realm)
                    if any(s.board.get(x, (None, None))[1] == "P"
                           and s.board[x][0] == p for x in cells if x in s.board):
                        continue
                    out.extend(_cid(x) for x in cells
                               if x not in s.board and not _is_center(x))
            return out

        # ---- play phase
        if s.pending is not None:
            if s.pending[0] == "create":
                realm = (s.pending[1], s.pending[2])
                vac = [c for c in _realm_cells(realm)
                       if c not in s.board and not _is_center(c)]
                return [f"{_cid(c)}={d}" for c in vac for d in "NESW"]
            else:  # immob choice
                realm = (s.pending[1], s.pending[2])
                enemies = [c for c in _realm_cells(realm)
                           if c in s.board and s.board[c][0] == 1 - p
                           and s.board[c][1] == "E" and s.board[c][3]]
                return [_cid(c) for c in sorted(enemies)]

        if s.tmode == "rearr":
            return self._rearr_moves(s, s.rearr_realm, p, s.rearr_asg)

        locked = set(s.locked)
        moves = []
        for cell, v in s.board.items():
            if v[0] != p or cell in locked:
                continue
            for src, dst in _piece_moves(s.board, cell):
                if s.tmode == "move" and not _seq_ok(s.tmoves + [(src, dst)]):
                    continue
                moves.append(f"{_cid(src)}>{_cid(dst)}")

        if s.tmode == "move":
            moves.append("done")
            return moves

        # turn start: rearrangement openers + pass
        realms = {}
        for cell, v in s.board.items():
            if v[0] == p and v[1] in "PE":
                realms.setdefault(_realm(cell), True)
        hist_realm, hist_n = s.rearr_hist[p]
        for realm in realms:
            if hist_realm is not None and tuple(hist_realm) == realm and hist_n >= 2:
                continue  # would be the third rearrangement there in a row
            moves.extend(self._rearr_moves(s, realm, p, []))
        moves.append("pass")
        return moves

    # ------------------------------------------------------------ transition

    def apply_move(self, s: RState, move: str, rng=None) -> RState:
        if s.over:
            raise ValueError("game over")
        ns = _copy(s)
        ns.ply += 1
        p = ns.to_move

        if ns.phase == "setup_b":
            self._apply_setup_base(ns, move, p)
        elif ns.phase == "setup_p":
            self._apply_setup_power(ns, move, p)
        elif move == "pass":
            if ns.tmode is not None or ns.pending is not None:
                raise ValueError("pass must be a whole turn")
            ns.passes += 1
            ns.rearr_hist[p] = [None, 0]   # a pass turn breaks the streak
            ns.last = []
            if ns.passes >= 2:
                self._finish(ns)
            else:
                ns.to_move = 1 - p
        elif move == "done":
            if ns.tmode != "move" or not ns.tmoves or ns.pending is not None:
                raise ValueError("nothing to end")
            self._end_turn(ns, [t for _, t in ns.tmoves])
        elif ns.pending is not None:
            self._apply_pending(ns, move, p)
        else:
            self._apply_piece_or_rearr(ns, move, p)

        if not ns.over and ns.ply >= MAX_PLY:
            self._finish(ns)
        return ns

    def _apply_setup_base(self, ns, move, p):
        cell = _cell(move)
        if not _is_center(cell) or cell in ns.board:
            raise ValueError(f"bad base placement {move!r}")
        ns.board[cell] = (p, "B", None, False)
        ns.bases_created[p] += 1
        if ns.bases_created[0] == 3 and ns.bases_created[1] == 3:
            ns.phase = "setup_p"
        ns.to_move = 1 - p
        ns.last = [cell]

    def _apply_setup_power(self, ns, move, p):
        cell = _cell(move)
        if cell in ns.board or _is_center(cell):
            raise ValueError(f"bad power placement {move!r}")
        ns.board[cell] = (p, "P", None, True)
        ns.to_move = 1 - p
        ns.last = [cell]
        if sum(1 for v in ns.board.values() if v[1] == "P") == 2 * N_POWERS:
            ns.phase = "play"
            ns.to_move = 0

    def _apply_pending(self, ns, move, p):
        kind = ns.pending[0]
        realm = (ns.pending[1], ns.pending[2])
        if kind == "create":
            cell_part, d = move.split("=")
            cell = _cell(cell_part)
            if (cell in ns.board or _is_center(cell) or _realm(cell) != realm
                    or d not in DIRS):
                raise ValueError(f"bad enforcer placement {move!r}")
            ns.board[cell] = (p, "E", d, True)
            ns.enf_created[p] += 1
            ns.locked.append(cell)
            ns.pending = None
        else:  # immob: choose the enemy Enforcer to flip
            cell = _cell(move)
            v = ns.board.get(cell)
            if (v is None or v[0] != 1 - p or v[1] != "E" or not v[3]
                    or _realm(cell) != realm):
                raise ValueError(f"bad immobilization target {move!r}")
            mover_cell = tuple(ns.pending[3])
            ns.board[cell] = (v[0], "E", v[2], False)
            self._maybe_self_immobilize(ns, realm, mover_cell, p)
            ns.pending = None

    def _maybe_self_immobilize(self, ns, realm, mover_cell, p):
        my_p = sum(1 for c in _realm_cells(realm)
                   if c in ns.board and ns.board[c][0] == p and ns.board[c][1] == "P")
        en_p = sum(1 for c in _realm_cells(realm)
                   if c in ns.board and ns.board[c][0] == 1 - p
                   and ns.board[c][1] == "P")
        if not my_p > en_p:
            o, k, d, _ = ns.board[mover_cell]
            ns.board[mover_cell] = (o, k, d, False)

    def _apply_piece_or_rearr(self, ns, move, p):
        if ">" not in move:
            raise ValueError(f"bad move {move!r}")
        rest = move
        newdir = None
        if "=" in rest:
            rest, newdir = rest.split("=")
            if newdir not in DIRS:
                raise ValueError(f"bad facing {move!r}")
        a, b = rest.split(">")
        src, dst = _cell(a), _cell(b)
        v = ns.board.get(src)
        if v is None or v[0] != p:
            raise ValueError(f"no piece to move {move!r}")

        if _realm(src) == _realm(dst):
            # rearrangement sub-move
            if ns.tmode not in (None, "rearr"):
                raise ValueError("cannot rearrange mid-move-turn")
            realm = _realm(src)
            if ns.tmode is None:
                hist_realm, hist_n = ns.rearr_hist[p]
                if hist_realm is not None and tuple(hist_realm) == realm and hist_n >= 2:
                    raise ValueError("may not rearrange that Realm three turns in a row")
                ns.tmode = "rearr"
                ns.rearr_realm = realm
            elif realm != ns.rearr_realm:
                raise ValueError("rearrangement is confined to one Realm")
            legal = self._rearr_moves(ns, realm, p, ns.rearr_asg)
            if move not in legal:
                raise ValueError(f"illegal rearrangement {move!r}")
            ns.rearr_asg.append((src, dst, newdir))
            pieces, _ = self._rearr_pieces_spaces(ns, realm, p)
            if len(ns.rearr_asg) == len(pieces):
                self._commit_rearrangement(ns, realm, p)
            return

        # normal (cross-Realm) piece move
        if newdir is not None:
            raise ValueError("facing suffix only in rearrangement")
        if ns.tmode == "rearr":
            raise ValueError("finish the rearrangement first")
        if src in set(ns.locked):
            raise ValueError("that piece already moved this turn")
        if dst not in {t for _, t in _piece_moves(ns.board, src)}:
            raise ValueError(f"illegal move {move!r}")
        if not _seq_ok(ns.tmoves + [(src, dst)]):
            raise ValueError("turn must stay a Dispersal or a Concentration")
        owner, kind, d, mobile = v
        if src[0] != dst[0]:
            mdir = "E" if dst[0] > src[0] else "W"
        else:
            mdir = "N" if dst[1] > src[1] else "S"
        del ns.board[src]
        ns.board[dst] = (owner, kind, mdir if kind == "E" else None, mobile)
        ns.tmode = "move"
        ns.tmoves.append((src, dst))
        ns.locked.append(dst)
        if kind == "P":
            self._power_stopped(ns, dst, p)
        else:
            self._enforcer_stopped(ns, dst, p)

    def _commit_rearrangement(self, ns, realm, p):
        moved = {}
        for src, dst, d in ns.rearr_asg:
            moved[dst] = (src, d)
        pieces = {src: ns.board[src] for src, _, _ in ns.rearr_asg}
        for src in pieces:
            del ns.board[src]
        for dst, (src, d) in moved.items():
            owner, kind, old_d, mobile = pieces[src]
            if kind == "E" and mobile:
                ns.board[dst] = (owner, "E", d, True)
            else:
                ns.board[dst] = (owner, kind, old_d, mobile)
        hist_realm, hist_n = ns.rearr_hist[p]
        if hist_realm is not None and tuple(hist_realm) == realm:
            ns.rearr_hist[p] = [realm, hist_n + 1]
        else:
            ns.rearr_hist[p] = [realm, 1]
        dsts = [dst for _, dst, _ in ns.rearr_asg]
        ns.passes = 0
        ns.to_move = 1 - p
        ns.tmode = None
        ns.tmoves = []
        ns.locked = []
        ns.rearr_realm = None
        ns.rearr_asg = []
        ns.last = dsts

    def _end_turn(self, ns, dsts):
        p = ns.to_move
        ns.rearr_hist[p] = [None, 0]   # a non-rearrangement turn breaks the streak
        ns.passes = 0
        ns.to_move = 1 - p
        ns.tmode = None
        ns.tmoves = []
        ns.locked = []
        ns.last = dsts

    # ---- Special Events (checked once, when the piece stops; the four
    # events are mutually exclusive at evaluation time — the sample game
    # confirms a Base creation does not chain into an Enforcer creation).

    def _power_stopped(self, ns, cell, p):
        realm = _realm(cell)
        ctr = _center(realm)
        cells = _realm_cells(realm)
        at_ctr = ns.board.get(ctr)
        if at_ctr is None:
            enemy_powers = any(c in ns.board and ns.board[c][0] == 1 - p
                               and ns.board[c][1] == "P" for c in cells)
            if not enemy_powers and ns.bases_created[p] < N_BASES:
                ns.board[ctr] = (p, "B", None, False)
                ns.bases_created[p] += 1
                if ns.bases_created[p] == N_BASES:
                    self._finish(ns)   # ends "as soon as" the 12th Base exists
        elif at_ctr[0] == p and at_ctr[1] == "B":
            any_mobile_e = any(c in ns.board and ns.board[c][1] == "E"
                               and ns.board[c][3] for c in cells)
            vac = any(c not in ns.board and not _is_center(c) for c in cells)
            if not any_mobile_e and vac and ns.enf_created[p] < N_ENFORCERS:
                ns.pending = ("create", realm[0], realm[1])

    def _enforcer_stopped(self, ns, cell, p):
        realm = _realm(cell)
        cells = _realm_cells(realm)
        enemy_mobile = [c for c in cells
                        if c in ns.board and ns.board[c][0] == 1 - p
                        and ns.board[c][1] == "E" and ns.board[c][3]]
        if enemy_mobile:
            if len(enemy_mobile) == 1:
                c = enemy_mobile[0]
                o, k, d, _ = ns.board[c]
                ns.board[c] = (o, k, d, False)
                self._maybe_self_immobilize(ns, realm, cell, p)
            else:
                ns.pending = ("immob", realm[0], realm[1], cell)
            return
        ctr = _center(realm)
        at_ctr = ns.board.get(ctr)
        if at_ctr is not None and at_ctr[0] == 1 - p and at_ctr[1] == "B":
            my_p = sum(1 for c in cells if c in ns.board
                       and ns.board[c][0] == p and ns.board[c][1] == "P")
            en_p = sum(1 for c in cells if c in ns.board
                       and ns.board[c][0] == 1 - p and ns.board[c][1] == "P")
            if my_p > en_p:
                del ns.board[ctr]
                ns.captured[p] += 1
                if my_p == en_p + 1:
                    o, k, d, _ = ns.board[cell]
                    ns.board[cell] = (o, k, d, False)

    # -------------------------------------------------------------- terminal

    def is_terminal(self, s: RState) -> bool:
        return s.over

    def returns(self, s: RState) -> list[float]:
        if s.winner == 0:
            return [1.0, -1.0]
        if s.winner == 1:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def heuristic(self, s: RState) -> list:
        d = (0.6 * (self._controlled(s, 0) - self._controlled(s, 1))
             + 0.2 * (s.bases_created[0] - s.bases_created[1])
             + 0.08 * (self._enf_score(s, 0) - self._enf_score(s, 1)))
        v = math.tanh(0.4 * d)
        return [v, -v]

    # --------------------------------------------------------- serialization

    def serialize(self, s: RState) -> dict:
        return {
            "phase": s.phase,
            "board": {_cid(c): [v[0], v[1], v[2], v[3]]
                      for c, v in s.board.items()},
            "to_move": s.to_move,
            "bases_created": list(s.bases_created),
            "enf_created": list(s.enf_created),
            "captured": list(s.captured),
            "tmode": s.tmode,
            "tmoves": [[_cid(a), _cid(b)] for a, b in s.tmoves],
            "locked": [_cid(c) for c in s.locked],
            "rearr_realm": (list(s.rearr_realm) if s.rearr_realm else None),
            "rearr_asg": [[_cid(a), _cid(b), d] for a, b, d in s.rearr_asg],
            "pending": (None if s.pending is None else
                        (["create", s.pending[1], s.pending[2]]
                         if s.pending[0] == "create" else
                         ["immob", s.pending[1], s.pending[2], _cid(s.pending[3])])),
            "passes": s.passes,
            "rearr_hist": [[(list(h[0]) if h[0] is not None else None), h[1]]
                           for h in s.rearr_hist],
            "ply": s.ply,
            "last": [_cid(c) for c in s.last],
            "over": s.over,
            "winner": s.winner,
        }

    def deserialize(self, d: dict) -> RState:
        pend = d.get("pending")
        if pend is not None:
            if pend[0] == "create":
                pend = ("create", pend[1], pend[2])
            else:
                pend = ("immob", pend[1], pend[2], _cell(pend[3]))
        return RState(
            phase=d["phase"],
            board={_cell(k): (v[0], v[1], v[2], v[3])
                   for k, v in d["board"].items()},
            to_move=d["to_move"],
            bases_created=list(d["bases_created"]),
            enf_created=list(d["enf_created"]),
            captured=list(d["captured"]),
            tmode=d.get("tmode"),
            tmoves=[(_cell(a), _cell(b)) for a, b in d.get("tmoves", [])],
            locked=[_cell(c) for c in d.get("locked", [])],
            rearr_realm=(tuple(d["rearr_realm"]) if d.get("rearr_realm") else None),
            rearr_asg=[(_cell(a), _cell(b), dd) for a, b, dd in d.get("rearr_asg", [])],
            pending=pend,
            passes=d.get("passes", 0),
            rearr_hist=[[(tuple(h[0]) if h[0] is not None else None), h[1]]
                        for h in d.get("rearr_hist", [[None, 0], [None, 0]])],
            ply=d.get("ply", 0),
            last=[_cell(c) for c in d.get("last", [])],
            over=d.get("over", False),
            winner=d.get("winner"),
        )

    # --------------------------------------------------------- presentation

    def describe_move(self, s: RState, move: str) -> str:
        if move in ("done", "pass"):
            return move
        if s.phase == "setup_b":
            return "B" + _alg(_cell(move))
        if s.phase == "setup_p":
            return "P" + _alg(_cell(move))
        if s.pending is not None:
            if s.pending[0] == "create":
                cell_part, d = move.split("=")
                return "E" + _alg(_cell(cell_part)) + d
            return "xE" + _alg(_cell(move))
        if ">" in move:
            rest = move.split("=")[0]
            a, b = rest.split(">")
            src, dst = _cell(a), _cell(b)
            kind = s.board[src][1] if src in s.board else "?"
            label = f"{kind}{_alg(src)}{_alg(dst)}"
            if _realm(src) == _realm(dst):
                return label + " (rearrange)"
            # annotate Special Events by diffing a trial application
            try:
                ns = self.apply_move(s, move)
            except ValueError:
                return label
            parts = []
            for c, v in ns.board.items():
                if v[1] == "B" and c not in s.board:
                    parts.append("B" + _alg(c))
            for c, v in s.board.items():
                if v[1] == "B" and c not in ns.board:
                    parts.append("xB" + _alg(c))
            for c, v in ns.board.items():
                if (v[1] == "E" and not v[3] and c in s.board
                        and s.board[c][1] == "E" and s.board[c][3]):
                    parts.append("xE" + _alg(c))
            if dst in ns.board and ns.board[dst][1] == "E" and not ns.board[dst][3]:
                parts.append("xE" + _alg(dst))
            if ns.pending is not None:
                parts.append("E+" if ns.pending[0] == "create" else "xE?")
            return label + (f"({','.join(parts)})" if parts else "")
        return move

    def render(self, s: RState, perspective=None) -> dict:
        tints = {}
        for c in range(SIZE):
            for r in range(SIZE):
                C, R = c // 3, r // 3
                if c % 3 == 1 and r % 3 == 1:
                    tints[f"{c},{r}"] = "#c9b98e"
                elif (C + R) % 2 == 0:
                    tints[f"{c},{r}"] = "#f0ead9"
                else:
                    tints[f"{c},{r}"] = "#ddd3ba"

        pieces = []
        for cell, (owner, kind, d, mobile) in s.board.items():
            pc = {"cell": _cid(cell), "owner": owner}
            if kind == "B":
                pc["glyph"] = "■"
            elif kind == "E":
                pc["glyph"] = GLYPH_MOBILE[d] if mobile else GLYPH_FROZEN[d]
            pieces.append(pc)

        highlights = [{"cell": _cid(c), "kind": "last-move"} for c in s.last]
        for _, t in s.tmoves:
            highlights.append({"cell": _cid(t), "kind": "last-move"})

        p = s.to_move
        name = SEAT_NAMES[p]
        r0, r1 = self._controlled(s, 0), self._controlled(s, 1)
        score = (f"Realms {r0}:{r1} · Bases {s.bases_created[0]}/12 : "
                 f"{s.bases_created[1]}/12")
        if s.over:
            if s.winner is None:
                caption = f"Draw — {score}"
            else:
                caption = f"{SEAT_NAMES[s.winner]} wins — {score}"
        elif s.phase == "setup_b":
            left = 3 - s.bases_created[p]
            caption = (f"{name}: place a Base on a free Realm centre "
                       f"({left} left; no two of yours in one Realm row/column)")
        elif s.phase == "setup_p":
            caption = (f"{name}: place a Power on a border space of a Realm "
                       f"you control (one per Realm)")
        elif s.pending is not None and s.pending[0] == "create":
            caption = (f"{name}: place the created Enforcer "
                       f"(pick a space, then its facing) — {score}")
        elif s.pending is not None:
            caption = f"{name}: choose an enemy Enforcer to immobilize — {score}"
        elif s.tmode == "rearr":
            caption = (f"{name}: rearranging — place your remaining pieces "
                       f"in the Realm — {score}")
        elif s.tmode == "move":
            caption = (f"{name}: move another piece (same Dispersal/"
                       f"Concentration) or End turn — {score}")
        else:
            caption = (f"{name} to move — one Realm out (Dispersal), "
                       f"many into one (Concentration), or rearrange — {score}")

        return {
            "board": {"type": "square", "width": SIZE, "height": SIZE,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "caption": caption,
            "reserve": {
                "0": {"B": N_BASES - s.bases_created[0],
                      "E": N_ENFORCERS - s.enf_created[0]},
                "1": {"B": N_BASES - s.bases_created[1],
                      "E": N_ENFORCERS - s.enf_created[1]},
            },
            "actionNames": {"done": "End turn",
                            "pass": "Pass (offer to end the game)"},
            "choiceNames": {"N": "North ▲", "S": "South ▼",
                            "E": "East ▶", "W": "West ◀"},
            "choiceTitle": "Enforcer facing",
        }
