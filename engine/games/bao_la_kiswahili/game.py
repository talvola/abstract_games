"""Bao la Kiswahili -- the Zanzibari / East-African master Mancala.

Board model for the platform: an 8-wide x 4-tall SQUARE board. Every cell is a
pit; its rendered LABEL is the seed count. Each player owns the two rows
nearest them; the row adjacent to the opponent is the *front* (inner) row.

Rows (bottom to top on screen):
    row 0 = player 0 (South) BACK  row
    row 1 = player 0 (South) FRONT row
    row 2 = player 1 (North) FRONT row
    row 3 = player 1 (North) BACK  row

The ruleset implemented is the de Voogt master ruleset (see rules.md for the
full as-implemented writeup, glossary and source notes). Headline features:

* two stages -- *namua* (each turn introduces one reserve seed into the front
  row) and *mtaji* (sowing from the board);
* captures take the opponent's opposite FRONT-row pit and re-enter the
  captured seeds at one of the mover's *kichwa* (front-row end pits), with the
  kichwa/kimbi side-forcing and direction-continuation rules;
* the *nyumba* (house, the 4th front-row pit from each player's right) with
  its tax, mandatory-stop and safari rules;
* multi-lap (relay) sowing, mandatory captures, the 16-seed rule, the
  takata restrictions (front row first, no singletons, the front row may
  never be emptied) and the rare *takasia* rule;
* loss when your front row is empty or you cannot move.

Move encoding (all enumerable / clickable):
    "c,r"        namua capture-placement whose entry kichwa is forced
    "c,r=L/R"    namua placement or mtaji-stage sow with a side choice
                 (captures: which kichwa to enter from; sows: which way round
                 your own 16-pit circuit -- L/R name the direction of travel
                 along YOUR FRONT ROW as seen on screen)
    "stop"/"safari"  resolve a pending nyumba decision (same player)

Never-ending single moves are a proven Bao phenomenon (Kronenburg, Donkers &
de Voogt, ICGA J. 2006); a cycle detector scores them as a draw unless the
opponent's front row was already emptied.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from agp.game import Game

WIDTH = 8
SOUTH, NORTH = 0, 1
SIDE_NAME = {SOUTH: "South", NORTH: "North"}

FRONT_ROW = {SOUTH: 1, NORTH: 2}
BACK_ROW = {SOUTH: 0, NORTH: 3}


def IDX(c: int, r: int) -> int:
    return r * 8 + c


def CELL(i: int) -> str:
    return f"{i % 8},{i // 8}"


FRONT = {p: [IDX(c, FRONT_ROW[p]) for c in range(8)] for p in (SOUTH, NORTH)}
BACK = {p: [IDX(c, BACK_ROW[p]) for c in range(8)] for p in (SOUTH, NORTH)}
FRONT_SET = {p: frozenset(FRONT[p]) for p in (SOUTH, NORTH)}
ALL_PITS = {p: FRONT[p] + BACK[p] for p in (SOUTH, NORTH)}

# Opposite front pit (same screen column, the facing front row).
OPP = {}
for c in range(8):
    OPP[IDX(c, 1)] = IDX(c, 2)
    OPP[IDX(c, 2)] = IDX(c, 1)

# The nyumba ("house"): the 4th front-row pit from each player's right.
# South sits at the bottom (his right = screen right) -> column 4.
# North sits at the top (his right = screen left)     -> column 3.
# (Matches the Ludii encoding's square holes, sites {12, 19}.)
HOUSE = {SOUTH: IDX(4, 1), NORTH: IDX(3, 2)}

# Sowing circuits: each player's own 16 pits form a loop. Direction labels are
# SCREEN-relative for both players: "R" travels rightward along the player's
# front row (then back along the back row), "L" is the reverse.
CYCLE = {}
POS = {}
for p in (SOUTH, NORTH):
    fr, br = FRONT_ROW[p], BACK_ROW[p]
    cyc_r = [IDX(c, fr) for c in range(8)] + [IDX(c, br) for c in range(7, -1, -1)]
    cyc_l = [IDX(c, fr) for c in range(7, -1, -1)] + [IDX(c, br) for c in range(8)]
    CYCLE[p] = {"R": cyc_r, "L": cyc_l}
    POS[p] = {d: {h: i for i, h in enumerate(CYCLE[p][d])} for d in ("R", "L")}

# kichwa = front-row end pits; kimbi = the end + penultimate front pits.
KICHWA = {p: {"L": IDX(0, FRONT_ROW[p]), "R": IDX(7, FRONT_ROW[p])}
          for p in (SOUTH, NORTH)}
KIMBI_COLS_LEFT = (0, 1)
KIMBI_COLS_RIGHT = (6, 7)

TOTAL_SEEDS = 64
QUIET_CAP = 200          # plies without a capture/introduction -> draw
PLY_CAP = 2000           # absolute anti-loop ply cap -> draw
LAP_DETECT_AFTER = 32    # start cycle-detection hashing after this many laps
LAP_GUARD = 100000       # absolute per-move lap guard


@dataclass
class BaoState:
    board: list = field(default_factory=list)   # 32 seed counts, IDX order
    hands: list = field(default_factory=lambda: [0, 0])
    alive: list = field(default_factory=lambda: [True, True])  # house alive?
    to_move: int = SOUTH
    variant: str = "kiswahili"
    pending: Optional[dict] = None  # {"dir": "L"/"R", "captured": bool}
    takasia: Optional[int] = None   # takasiaed pit of the player to move
    winner: Optional[int] = None
    draw: bool = False
    loop_period: int = 0            # >0 when a never-ending move was detected
    ply: int = 0
    quiet: int = 0
    last: Optional[int] = None
    _moves: Optional[list] = field(default=None, repr=False, compare=False)


def _parse(move: str):
    """-> (pit index, side or None)."""
    if "=" in move:
        cell, side = move.split("=")
    else:
        cell, side = move, None
    c, r = cell.split(",")
    return IDX(int(c), int(r)), side


class BaoLaKiswahili(Game):
    name = "Bao la Kiswahili"

    @property
    def num_players(self) -> int:
        return 2

    # -- setup ---------------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> BaoState:
        variant = (options or {}).get("variant", "kiswahili")
        board = [0] * 32
        if variant == "kujifunza":
            board = [2] * 32
            return BaoState(board=board, hands=[0, 0], alive=[False, False],
                            variant="kujifunza")
        # Master game: 6 seeds in each nyumba, 2 in each of the two front pits
        # on the nyumba's right (the player's right); 22 seeds in hand.
        board[HOUSE[SOUTH]] = 6
        board[IDX(5, 1)] = 2
        board[IDX(6, 1)] = 2
        board[HOUSE[NORTH]] = 6
        board[IDX(2, 2)] = 2
        board[IDX(1, 2)] = 2
        return BaoState(board=board, hands=[22, 22], alive=[True, True],
                        variant="kiswahili")

    def current_player(self, s: BaoState) -> int:
        return s.to_move

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _functional_house(board, alive, p) -> bool:
        return alive[p] and board[HOUSE[p]] >= 6

    @staticmethod
    def _front_empty(board, p) -> bool:
        return all(board[i] == 0 for i in FRONT[p])

    # -- the sowing engine ---------------------------------------------------
    def _sow_loop(self, bd, alive, p, direction, cursor, hand, capture_turn,
                  stage, mtaji_first, init_hand, takasia_idx, first_src,
                  track_front):
        """Run relay laps until the turn ends.

        bd / alive are mutated in place. Returns a dict:
          outcome: "end" | "pending" | "infinite"
          dir, captured_any, violation (front row emptied during a takata sow),
          period (loop period when outcome == "infinite").
        """
        cyc = CYCLE[p][direction]
        posmap = POS[p][direction]
        front = FRONT_SET[p]
        house = HOUSE[p]
        q = 1 - p
        captured_any = capture_turn and stage == "namua"  # namua capture already took
        violation = False
        fcnt = sum(bd[i] for i in FRONT[p]) if track_front else 0
        lap = 0
        seen = None
        while True:
            lap += 1
            last = None
            for _ in range(hand):
                cursor = (cursor + 1) & 15
                last = cyc[cursor]
                bd[last] += 1
                if track_front:
                    if last in front:
                        fcnt += 1
                    elif fcnt == 0:
                        violation = True
            hand = 0
            landed = bd[last]
            if mtaji_first and lap == 1:
                if (init_hand <= 15 and landed >= 2 and last in front
                        and bd[OPP[last]] > 0):
                    capture_turn = True
            if landed == 1:  # fell into an empty pit -> turn over
                return {"outcome": "end", "dir": direction,
                        "captured": captured_any, "violation": violation,
                        "period": 0, "last": last}
            # occupied landing
            if capture_turn and last in front and bd[OPP[last]] > 0:
                # (chain) capture
                oh = OPP[last]
                taken = bd[oh]
                bd[oh] = 0
                if oh == HOUSE[q]:
                    alive[q] = False
                captured_any = True
                col = last % 8
                if col in KIMBI_COLS_LEFT:
                    side = "L"
                elif col in KIMBI_COLS_RIGHT:
                    side = "R"
                else:
                    side = "L" if direction == "R" else "R"
                direction = "R" if side == "L" else "L"
                cyc = CYCLE[p][direction]
                posmap = POS[p][direction]
                cursor = (posmap[KICHWA[p][side]] - 1) & 15
                hand = taken
                continue
            if (takasia_idx is not None and last == takasia_idx
                    and not capture_turn
                    and not (lap == 1 and first_src == house)):
                # a lap ending in the mover's takasiaed pit is not continued
                return {"outcome": "end", "dir": direction,
                        "captured": captured_any, "violation": violation,
                        "period": 0, "last": last}
            if last == house and alive[p] and bd[last] >= 6:
                if capture_turn:
                    if stage == "namua":
                        return {"outcome": "pending", "dir": direction,
                                "captured": captured_any,
                                "violation": violation, "period": 0,
                                "last": last}
                    # mtaji stage: forced safari (falls through to the pickup,
                    # which kills the house below)
                else:
                    # takata: the lap ends in the functional nyumba -> stop
                    return {"outcome": "end", "dir": direction,
                            "captured": captured_any, "violation": violation,
                            "period": 0, "last": last}
            # relay: pick the pit up and keep sowing
            if last == house and alive[p]:
                alive[p] = False    # its contents are moved in a lap
            hand = bd[last]
            bd[last] = 0
            if track_front and last in front:
                fcnt -= hand
            cursor = posmap[last]
            if lap > LAP_DETECT_AFTER:
                if seen is None:
                    seen = {}
                key = (bytes(bd), cursor, direction, hand, capture_turn)
                prev = seen.get(key)
                if prev is not None:
                    return {"outcome": "infinite", "dir": direction,
                            "captured": captured_any, "violation": violation,
                            "period": lap - prev, "last": last}
                seen[key] = lap
            if lap > LAP_GUARD:  # defensive; cycle detection fires first
                return {"outcome": "infinite", "dir": direction,
                        "captured": captured_any, "violation": violation,
                        "period": 0, "last": last}

    def _first_lap_capture(self, bd, p, src, d):
        """Mtaji stage: does sowing `src` in direction `d` capture on lap 1?
        Returns the victim pit index or None. O(1)."""
        n = bd[src]
        if n < 2 or n > 15:
            return None
        land = CYCLE[p][d][(POS[p][d][src] + n) & 15]
        if land in FRONT_SET[p] and bd[land] >= 1 and bd[OPP[land]] > 0:
            return OPP[land]
        return None

    # -- turn execution (shared by apply_move and legality probes) -----------
    def _exec(self, s: BaoState, move: str, probe: bool):
        """Execute `move` on copies of the state's mutable data.

        Returns (bd, hands, alive, result-dict, meta) where meta notes
        introduced/last. Does not touch `s`.
        """
        p = s.to_move
        bd = list(s.board)
        hands = list(s.hands)
        alive = list(s.alive)
        stage = "namua" if hands[p] > 0 else "mtaji"

        if move in ("stop", "safari"):
            # a pending nyumba decision only ever arises inside a namua-stage
            # capture turn, so the turn introduced a seed and captured
            info = s.pending
            if move == "stop":
                res = {"outcome": "end", "dir": info["dir"],
                       "captured": info["captured"], "violation": False,
                       "period": 0, "last": HOUSE[p]}
                return bd, hands, alive, res, {"introduced": True}
            # safari: destroy the house and relay its contents
            alive[p] = False
            hand = bd[HOUSE[p]]
            bd[HOUSE[p]] = 0
            d = info["dir"]
            cursor = POS[p][d][HOUSE[p]]
            res = self._sow_loop(bd, alive, p, d, cursor, hand, True, "namua",
                                 False, hand, None, None, False)
            if not res["captured"]:
                res["captured"] = info["captured"]
            return bd, hands, alive, res, {"introduced": True}

        pit, side = _parse(move)

        if stage == "namua":
            hands[p] -= 1
            bd[pit] += 1
            if bd[OPP[pit]] > 0:
                # capture placement (bd[pit] was >0 before by legality)
                oh = OPP[pit]
                taken = bd[oh]
                bd[oh] = 0
                if oh == HOUSE[1 - p]:
                    alive[1 - p] = False
                col = pit % 8
                if col in KIMBI_COLS_LEFT:
                    entry = "L"
                elif col in KIMBI_COLS_RIGHT:
                    entry = "R"
                else:
                    entry = side  # free choice, from the move suffix
                d = "R" if entry == "L" else "L"
                cursor = (POS[p][d][KICHWA[p][entry]] - 1) & 15
                res = self._sow_loop(bd, alive, p, d, cursor, taken, True,
                                     "namua", False, taken, None, None, False)
                res["captured"] = True
                return bd, hands, alive, res, {"introduced": True}
            # takasa placement
            if pit == HOUSE[p] and alive[p] and bd[pit] - 1 >= 6:
                # tax the nyumba: sow just two of its seeds
                bd[pit] -= 2
                hand = 2
            else:
                if pit == HOUSE[p] and alive[p]:
                    alive[p] = False
                hand = bd[pit]
                bd[pit] = 0
            d = side
            cursor = POS[p][d][pit]
            res = self._sow_loop(bd, alive, p, d, cursor, hand, False, "namua",
                                 False, hand, s.takasia, pit, True)
            return bd, hands, alive, res, {"introduced": True}

        # mtaji stage
        if pit == HOUSE[p] and alive[p]:
            alive[p] = False
        hand = bd[pit]
        bd[pit] = 0
        d = side
        cursor = POS[p][d][pit]
        res = self._sow_loop(bd, alive, p, d, cursor, hand, False, "mtaji",
                             True, hand, s.takasia, pit, True)
        return bd, hands, alive, res, {"introduced": False}

    # -- legal moves ---------------------------------------------------------
    def legal_moves(self, s: BaoState) -> list:
        if s._moves is not None:
            return s._moves
        moves = self._legal_moves(s)
        s._moves = moves
        return moves

    def _legal_moves(self, s: BaoState) -> list:
        if s.winner is not None or s.draw:
            return []
        if s.pending is not None:
            return ["stop", "safari"]
        p = s.to_move
        bd = s.board
        if self._front_empty(bd, p):
            return []  # front row empty -> the player has lost
        if s.hands[p] > 0:
            # ---- namua stage ----
            markers = [i for i in FRONT[p] if bd[i] > 0 and bd[OPP[i]] > 0]
            if markers:  # captures are mandatory
                mvs = []
                for m in markers:
                    col = m % 8
                    if col in KIMBI_COLS_LEFT or col in KIMBI_COLS_RIGHT:
                        mvs.append(CELL(m))
                    else:
                        mvs.append(CELL(m) + "=L")
                        mvs.append(CELL(m) + "=R")
                return mvs
            occ = [i for i in FRONT[p] if bd[i] > 0]
            if self._functional_house(bd, s.alive, p):
                cands = [i for i in occ if i != HOUSE[p]] or [HOUSE[p]]
            else:
                ge2 = [i for i in occ if bd[i] >= 2]
                cands = ge2 or occ
        else:
            # ---- mtaji stage ----
            caps = []
            for src in ALL_PITS[p]:
                for d in ("L", "R"):
                    if self._first_lap_capture(bd, p, src, d) is not None:
                        caps.append(CELL(src) + "=" + d)
            if caps:
                return caps
            fr2 = [i for i in FRONT[p] if bd[i] >= 2]
            cands = fr2 or [i for i in BACK[p] if bd[i] >= 2]
            cands = [h for h in cands if h != s.takasia]
        # takasa / takata candidates: filter moves that would leave the
        # mover's front row empty at any point (never allowed).
        mvs = []
        for h in cands:
            for d in ("L", "R"):
                mv = CELL(h) + "=" + d
                _, _, _, res, _ = self._exec(s, mv, probe=True)
                if not res["violation"]:
                    mvs.append(mv)
        return mvs

    # -- apply ---------------------------------------------------------------
    def apply_move(self, s: BaoState, move: str, rng=None) -> BaoState:
        p = s.to_move
        bd, hands, alive, res, meta = self._exec(s, move, probe=False)
        ns = BaoState(board=bd, hands=hands, alive=alive, to_move=p,
                      variant=s.variant, pending=None, takasia=None,
                      winner=None, draw=False, loop_period=0,
                      ply=s.ply, quiet=s.quiet, last=res.get("last"))
        if res["outcome"] == "pending":
            # the mover must choose stop or safari; same player, turn open
            ns.pending = {"dir": res["dir"], "captured": res["captured"]}
            ns.takasia = s.takasia
            return ns
        if res["outcome"] == "infinite":
            # never-ending move: win if it already cleared the opponent's
            # front row, otherwise an honest draw
            ns.ply += 1
            if self._front_empty(bd, 1 - p):
                ns.winner = p
            else:
                ns.draw = True
                ns.loop_period = res["period"]
            return ns
        # normal end of turn
        ns.ply += 1
        if res["captured"] or meta["introduced"]:
            ns.quiet = 0
        else:
            ns.quiet = s.quiet + 1
        q = 1 - p
        # takasia: only in the mtaji stage (both hands empty), only after a
        # non-capturing (takata) move, kiswahili master rules only
        if (s.variant == "kiswahili" and not res["captured"]
                and hands[p] == 0 and hands[q] == 0):
            ns.takasia = self._compute_takasia(bd, alive, p)
        ns.to_move = q
        if self._front_empty(bd, q):
            ns.winner = p
        elif self._front_empty(bd, p):
            ns.winner = q
        elif ns.quiet >= QUIET_CAP or ns.ply >= PLY_CAP:
            ns.draw = True
        return ns

    def _compute_takasia(self, bd, alive, p):
        """After p's takata move: if exactly one of the opponent's front pits
        is under threat and the opponent has no capture, mark it."""
        q = 1 - p
        threats = set()
        for src in ALL_PITS[p]:
            for d in ("L", "R"):
                v = self._first_lap_capture(bd, p, src, d)
                if v is not None:
                    threats.add(v)
                    if len(threats) > 1:
                        return None
        if len(threats) != 1:
            return None
        for src in ALL_PITS[q]:
            for d in ("L", "R"):
                if self._first_lap_capture(bd, q, src, d) is not None:
                    return None  # the opponent can capture -> no takasia
        x = threats.pop()
        # exceptions: never the (functional) nyumba, never the only occupied
        # front pit, never the only front pit with more than one seed
        if x == HOUSE[q] and alive[q] and bd[x] >= 6:
            return None
        occ = [i for i in FRONT[q] if bd[i] > 0]
        if occ == [x]:
            return None
        ge2 = [i for i in FRONT[q] if bd[i] >= 2]
        if bd[x] >= 2 and ge2 == [x]:
            return None
        return x

    # -- terminal / returns --------------------------------------------------
    def is_terminal(self, s: BaoState) -> bool:
        if s.winner is not None or s.draw:
            return True
        return not self.legal_moves(s)

    def returns(self, s: BaoState) -> list:
        if s.winner is not None:
            r = [-1.0, -1.0]
            r[s.winner] = 1.0
            return r
        if s.draw:
            return [0.0, 0.0]
        # no legal moves: the player to move loses (empty front row or stuck)
        loser = s.to_move
        r = [0.0, 0.0]
        r[loser] = -1.0
        r[1 - loser] = 1.0
        return r

    # -- heuristic (bot eval): one payoff per seat ---------------------------
    def heuristic(self, s: BaoState) -> list:
        sc = []
        for p in (SOUTH, NORTH):
            front = sum(s.board[i] for i in FRONT[p])
            back = sum(s.board[i] for i in BACK[p])
            sc.append(2.0 * front + back + s.hands[p])
        v = math.tanh((sc[0] - sc[1]) / 24.0)
        return [v, -v]

    # -- serialize -----------------------------------------------------------
    def serialize(self, s: BaoState) -> dict:
        return {
            "board": list(s.board),
            "hands": list(s.hands),
            "alive": list(s.alive),
            "to_move": s.to_move,
            "variant": s.variant,
            "pending": dict(s.pending) if s.pending else None,
            "takasia": s.takasia,
            "winner": s.winner,
            "draw": s.draw,
            "loop_period": s.loop_period,
            "ply": s.ply,
            "quiet": s.quiet,
            "last": s.last,
        }

    def deserialize(self, d: dict) -> BaoState:
        return BaoState(
            board=list(d["board"]),
            hands=list(d["hands"]),
            alive=[bool(a) for a in d["alive"]],
            to_move=d["to_move"],
            variant=d.get("variant", "kiswahili"),
            pending=dict(d["pending"]) if d.get("pending") else None,
            takasia=d.get("takasia"),
            winner=d.get("winner"),
            draw=bool(d.get("draw", False)),
            loop_period=d.get("loop_period", 0),
            ply=d.get("ply", 0),
            quiet=d.get("quiet", 0),
            last=d.get("last"),
        )

    # -- render --------------------------------------------------------------
    def render(self, s: BaoState, perspective=None) -> dict:
        pieces = []
        for i, n in enumerate(s.board):
            r = i // 8
            owner = SOUTH if r <= 1 else NORTH
            pieces.append({"cell": CELL(i), "owner": owner, "label": str(n)})
        tints = {}
        for p in (SOUTH, NORTH):
            h = HOUSE[p]
            if s.variant == "kiswahili":
                if self._functional_house(s.board, s.alive, p):
                    tints[CELL(h)] = "#e0c068"   # functional house: gold
                elif s.alive[p]:
                    tints[CELL(h)] = "#ece0bc"   # alive but under 6 seeds
                else:
                    tints[CELL(h)] = "#c8c8c8"   # destroyed house
        highlights = []
        if s.last is not None:
            highlights.append({"cell": CELL(s.last), "kind": "last-move"})
        if self.is_terminal(s):
            rr = self.returns(s)
            if rr[SOUTH] > rr[NORTH]:
                caption = "South wins"
            elif rr[NORTH] > rr[SOUTH]:
                caption = "North wins"
            else:
                caption = "Draw"
                if s.loop_period:
                    caption += f" (never-ending move, period {s.loop_period})"
        else:
            who = SIDE_NAME[s.to_move]
            stage = "namua" if s.hands[s.to_move] > 0 else "mtaji"
            caption = f"{who} to move ({stage})"
            if s.pending is not None:
                caption = f"{who}: stop or safari (sow the nyumba)?"
        if s.variant == "kiswahili":
            caption += (f" — hands S:{s.hands[SOUTH]} N:{s.hands[NORTH]}")
        if s.takasia is not None:
            caption += f" — takasia on {CELL(s.takasia)}"
        return {
            "board": {"type": "square", "width": WIDTH, "height": 4,
                      "tints": tints},
            "pieces": pieces,
            "highlights": highlights,
            "choiceNames": {"L": "Left (kushoto)", "R": "Right (kulia)"},
            "caption": caption,
        }

    # -- move log ------------------------------------------------------------
    def describe_move(self, s: BaoState, move: str) -> str:
        """Classical Bao notation (de Voogt): hole A/B 1-8 from the owner's
        left, '*' = takasa. Letter conventions, matched against the published
        notated games (Mancala World Problems 1-3 + Game Cabinet #Notation):
        capture letters name the entry-kichwa side (owner's frame), takasa
        letters the sowing direction (owner's frame), and back-row letters the
        physical direction the seeds first travel (as printed in the
        sources)."""
        if move == "stop":
            return "stop (keep the nyumba)"
        if move == "safari":
            return "safari (sow the nyumba)"
        p = s.to_move
        pit, side = _parse(move)
        c, r = pit % 8, pit // 8
        swap = {"L": "R", "R": "L", None: None}
        if p == SOUTH:
            letter = "A" if r == FRONT_ROW[p] else "B"
            n = c + 1
        else:
            letter = "a" if r == FRONT_ROW[p] else "b"
            n = 8 - c
        if s.hands[p] > 0:
            # namua: placements are front-row; suffix = entry side (captures)
            # or travel direction (takasa), both screen-frame -> owner frame
            cap = s.board[OPP[pit]] > 0 if pit in FRONT_SET[p] else False
            subj = side if p == SOUTH else swap[side]
        else:
            cap = any(self._first_lap_capture(s.board, p, pit, d) is not None
                      for d in ((side,) if side else ("L", "R")))
            if pit not in FRONT_SET[p]:
                # back-row pit: the sources print the physical direction the
                # seeds first travel (MW puzzles "B2L"/"B4R"/"b3R"/"b2R",
                # GC diagram 23 "nine seeds to the right")
                subj = swap[side]
            elif cap and side:
                # front-row capture: entry-kichwa side, owner frame
                # (MW puzzle 2 "a4R"; GC notation "A5R>")
                land = CYCLE[p][side][(POS[p][side][pit] + s.board[pit]) & 15]
                col = land % 8
                if col in KIMBI_COLS_LEFT:
                    screen = "L"
                elif col in KIMBI_COLS_RIGHT:
                    screen = "R"
                else:
                    screen = "L" if side == "R" else "R"
                subj = screen if p == SOUTH else swap[screen]
            else:
                subj = side if p == SOUTH else swap[side]
        out = f"{letter}{n}"
        if subj:
            out += subj
        if not cap:
            out += "*"
        return out
