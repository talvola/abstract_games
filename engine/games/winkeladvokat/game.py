"""Winkeladvokat ("L'avocat du diable" / Devil's Advocate) — Roland Siegers,
Schmidt Spiele 1986. Two-player version.

Sources (all consulted directly; the German sheet is the publisher original and
wins every conflict):

* GERMAN RULES — Schmidt Spiele's own "WINKELADVOKAT" instruction sheet, 3pp,
  http://www.spielanleitung.com/download.php4?id=2051 (filename Winkeladvokat.pdf).
  Quoted verbatim below; figures Abb. 1-3 pixel-read.
* FRENCH RULES — "Winkeladvokat - L'avocat du diable", the Schmidt French
  translation scanned by François Haffner, http://jeuxsoc.free.fr. Agrees with
  the German on every point; Figures 1-3 are the same drawings.
* BOARD VALUES — the 64 printed numbers are NOT in either rules sheet. They are
  transcribed from photographs of the physical board, three independent copies:
  BGG image pic4768412 "Game board" and pic431977 "gameboard"
  (https://boardgamegeek.com/boardgame/2473/winkeladvokat, image gallery), plus
  the front-cover photograph of *Abstract Games* issue 23 (Spring 2022).
  All three show the same grid: four concentric rings 2 / 4 / 8 / 16 outward-in,
  the four corners blank colour-coded start squares. (Several German review
  sites claim "2, 4, 8, 16 und 32"; there is no 32 on any photograph of the
  board — treated as a propagated error.)
* CORROBORATION — *Abstract Games* #23 (front-cover note by Kerry Handscomb,
  p. 1, and Don Kirkby's "Domino Runners", p. 46-47, a game derived from
  Winkeladvokat/Cabale). Used only where it agrees with the publisher sheet.

Rules as implemented
--------------------

Board: 8x8. "Bei 2 Spielern werden das blaue und das rote Ausgangsfeld benutzt;
jeder Spieler erhält 25 Paragraphensteine." The blue and red start squares are
diagonally opposite corners, so seat 0 starts on "0,0" and seat 1 on "7,7". Each
seat holds 25 Article (§) tokens.

Cell values: ``2 ** (1 + min(c, r, 7-c, 7-r))`` — 2 on the outer ring, 4, 8 and
16 on the central 2x2. The four corner start squares carry no number and are
worth 0.

WINKELZUG (the avocat's move, Abb. 1): "Dazu bewegt der Spieler ihn (senkrecht
oder waagerecht) zunächst um eine beliebige Anzahl an unbesetzten Feldern in
eine der vier Richtungen, um ihn dann anschließend im rechten Winkel (also 90°)
abbiegen zu lassen. Der Stein darf dann noch einmal um eine beliebige Anzahl
unbesetzter Felder fortbewegt werden." Both legs are at least one cell (Abb. 1
shows 2+2; the French sheet renders leg two as "d'une ou plusieurs cases"; AG#23
p. 1 "one Rook move followed by another Rook move perpendicular to the first";
Domino Runners "Each part must move at least one space across the board"). Every
cell of both legs, including the pivot and the landing cell, must be unoccupied
— articles AND the other avocat block. The pivot is the WINKELFELD.

ARTICLE PLACEMENT: "Während eines Winkelzuges *muß* der Spieler einen seiner
Paragraphensteine im Winkelfeld plazieren." Mandatory, so a player with an empty
hand cannot complete a Winkelzug (see END).

CAPTURE (Abb. 2): "Ein Spieler kann *anstelle der Bewegung seines
Advokatensteins* auch gegnerische Paragraphensteine schlagen." — INSTEAD OF
moving the avocat, i.e. a capture is a whole turn of its own, not an appendix to
a Winkelzug. (Counter-evidence, weighed and rejected: the numbered caption of
Abb. 2 in BOTH publisher sheets reads "(1) detour -> (2) article placed on the
Winkelfeld -> (3) that article has jumped the enemy article (4)", and AG#23 +
the derived Domino Runners chain them explicitly. The figure is a composite
illustration of both rules on one diagram and never says "in the same turn";
the body text is unambiguous, so the body text wins.) One of your articles —
ANY of them, not only a freshly placed one — jumps an ADJACENT opposing article
into the empty cell directly beyond ("wie im Damespiel"); Abb. 2 shows a
vertical jump, the printed board is a grid of OCTAGONS whose only shared edges
are orthogonal, and Domino Runners spells out "You may not jump diagonally", so
jumps are orthogonal only. "Auch Kettensprünge sind erlaubt" — chains are ALLOWED, not
compulsory, and there is no maximum-capture rule. Avocats neither capture nor
are captured, and they block both the jumped cell and the landing cell.

END: "Das Spiel endet, sobald ein Spieler nicht mehr mit seinem Advokatenstein
ziehen kann" (Abb. 3: an avocat hemmed in on all four orthogonal sides).

SCORING: "Jetzt addiert jeder Spieler die Punktwerte der Felder, die von seinen
Paragraphensteinen besetzt sind und fügt dieser Summe noch weitere Punkte
entsprechend der Anzahl der von ihm geschlagenen gegnerischen Paragraphensteine
hinzu." Most points wins; an equal total is an honest DRAW.

Interpretations (the rules are silent; see rules.md)
----------------------------------------------------
1. "sobald ein Spieler nicht mehr ... ziehen kann" is evaluated for the player
   TO MOVE at the start of their turn: you try to move your avocat, you cannot,
   the game is over. Captures do not keep the game alive — the sheet ties the
   end strictly to the avocat.
2. An empty hand therefore ends the game as well: placement is mandatory during
   a Winkelzug, so with no articles left you cannot move your avocat.
3. Jumped articles are removed immediately, so within one chain a stone cannot
   be jumped twice and a vacated cell may be landed on again.
4. The four corner start squares carry no printed number and score 0. Nothing
   forbids pivoting on a (vacated) corner, so it is allowed and scores 0.
5. A capture chain is modelled as several moves in ONE turn (the seat keeps the
   move): jump, then either jump on or play the ``done`` action. This keeps
   chains genuinely optional while staying clickable in the generic UI.

Termination is proved, not capped: every turn is either a Winkelzug (which
removes one article from the mover's hand, at most 25+25 = 50 in a game) or a
capture (which removes at least one article that some Winkelzug put there, so at
most 50 in a game), plus at most one ``done`` per capture turn — under 200 plies
in the worst case. PLY_CAP = 400 is an unreachable safety net.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from agp.game import Game

W = H = 8
N = W * H
HAND = 25                       # "jeder Spieler erhält 25 Paragraphensteine"
PLY_CAP = 400                   # unreachable safety net (see module docstring)

SEAT_NAMES = ("Red", "Blue")    # seat colours in web/src/colors.js
START = (0, 7 * W + 7)          # seat 0 -> "0,0", seat 1 -> "7,7" (opposite corners)

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
# The two 90-degree turns available after travelling in each direction.
PERP = {(1, 0): ((0, 1), (0, -1)), (-1, 0): ((0, 1), (0, -1)),
        (0, 1): ((1, 0), (-1, 0)), (0, -1): ((1, 0), (-1, 0))}

CORNERS = (0, W - 1, (H - 1) * W, (H - 1) * W + W - 1)


def _value(c: int, r: int) -> int:
    """Printed cell value: concentric rings 2/4/8/16, blank (0) on the corners."""
    if (c in (0, W - 1)) and (r in (0, H - 1)):
        return 0
    return 2 ** (1 + min(c, r, W - 1 - c, H - 1 - r))


VALUES = tuple(_value(i % W, i // W) for i in range(N))
BOARD_TOTAL = sum(VALUES)       # 288

# Ring tints, dark enough that the renderer's light cell labels stay readable.
_RING_TINT = {2: "#2e2b24", 4: "#3a3428", 8: "#473d29", 16: "#57492a"}
_START_TINT = ("#4a2020", "#1e2c4a")        # seat 0 / seat 1 home corner
_IDLE_TINT = "#2f2b25"                      # the two corners unused at 2 players

FILES = "abcdefgh"


def cid(i: int) -> str:
    return f"{i % W},{i // W}"


def _idx(text: str) -> int:
    c, r = text.split(",")
    return int(r) * W + int(c)


def _san(i: int) -> str:
    """Human-friendly cell name for the move log: a1 .. h8."""
    return f"{FILES[i % W]}{i // W + 1}"


@dataclass
class WState:
    board: tuple        # N entries: -1 empty, else the owning seat of an article
    avocat: tuple       # (cell of seat 0's avocat, cell of seat 1's avocat)
    hand: tuple         # articles still off-board, per seat
    taken: tuple        # opposing articles captured, per seat
    to_move: int
    chain: Optional[int]  # cell of the article part-way through a jump chain
    ply: int


class Winkeladvokat(Game):
    name = "Winkeladvokat"

    @property
    def num_players(self) -> int:
        return 2

    # ---- setup -----------------------------------------------------------
    def initial_state(self, options=None, rng=None) -> WState:
        return WState(board=(-1,) * N, avocat=START, hand=(HAND, HAND),
                      taken=(0, 0), to_move=0, chain=None, ply=0)

    def current_player(self, s: WState) -> int:
        return s.to_move

    # ---- geometry --------------------------------------------------------
    @staticmethod
    def _occupied(s: WState, i: int) -> bool:
        return s.board[i] != -1 or i == s.avocat[0] or i == s.avocat[1]

    def _detours(self, s: WState, seat: int) -> Iterator[str]:
        """Every legal Winkelzug for ``seat``: 'start>pivot>end'.

        Leg one runs at least one cell in one of the four directions over
        unoccupied cells; the pivot (Winkelfeld) is where it turns; leg two runs
        at least one cell perpendicular, again over unoccupied cells.
        """
        if s.hand[seat] <= 0:               # placement is mandatory -> no Winkelzug
            return
        start = s.avocat[seat]
        sc, sr = start % W, start // W
        for d1 in DIRS:
            c, r = sc, sr
            while True:
                c += d1[0]
                r += d1[1]
                if not (0 <= c < W and 0 <= r < H):
                    break
                pivot = r * W + c
                if self._occupied(s, pivot):
                    break
                for d2 in PERP[d1]:
                    cc, rr = c, r
                    while True:
                        cc += d2[0]
                        rr += d2[1]
                        if not (0 <= cc < W and 0 <= rr < H):
                            break
                        end = rr * W + cc
                        if self._occupied(s, end):
                            break
                        yield f"{sc},{sr}>{c},{r}>{cc},{rr}"

    def _clear_leg(self, s: WState, a: int, b: int) -> bool:
        """True if ``a`` -> ``b`` is a straight rook run of >= 1 cell whose every
        cell after ``a`` (the destination included) is unoccupied."""
        ac, ar, bc, br = a % W, a // W, b % W, b // W
        if (ac == bc) == (ar == br):        # exactly one axis must change
            return False
        dc = 0 if ac == bc else (1 if bc > ac else -1)
        dr = 0 if ar == br else (1 if br > ar else -1)
        c, r = ac, ar
        while (c, r) != (bc, br):
            c += dc
            r += dr
            if self._occupied(s, r * W + c):
                return False
        return True

    def _any_detour(self, s: WState, seat: int) -> bool:
        for _ in self._detours(s, seat):
            return True
        return False

    def _jumps(self, s: WState, seat: int, i: int) -> Iterator[tuple]:
        """(landing cell, jumped cell) for every orthogonal jump from ``i``."""
        c, r = i % W, i // W
        foe = 1 - seat
        for dc, dr in DIRS:
            lc, lr = c + 2 * dc, r + 2 * dr
            if not (0 <= lc < W and 0 <= lr < H):
                continue
            over = (r + dr) * W + (c + dc)
            land = lr * W + lc
            if s.board[over] != foe:        # only an OPPOSING article may be jumped
                continue
            if self._occupied(s, land):     # the cell beyond must be free
                continue
            yield land, over

    # ---- core loop -------------------------------------------------------
    def legal_moves(self, s: WState) -> list:
        if self.is_terminal(s):
            return []
        p = s.to_move
        if s.chain is not None:             # part-way through a chain of jumps
            out = [f"{cid(s.chain)}>{cid(l)}" for l, _ in self._jumps(s, p, s.chain)]
            return out + ["done"]
        moves = list(self._detours(s, p))
        for i in range(N):
            if s.board[i] == p:
                for land, _ in self._jumps(s, p, i):
                    moves.append(f"{cid(i)}>{cid(land)}")
        return moves

    def apply_move(self, s: WState, move: str, rng=None) -> WState:
        if move == "done":
            if s.chain is None:
                raise ValueError("no jump chain in progress")
            return WState(s.board, s.avocat, s.hand, s.taken,
                          1 - s.to_move, None, s.ply + 1)

        cells = [_idx(t) for t in move.split(">")]
        p = s.to_move

        if len(cells) == 3:                         # WINKELZUG
            start, pivot, end = cells
            if s.chain is not None or start != s.avocat[p] or s.hand[p] <= 0:
                raise ValueError(f"illegal avocat move {move!r}")
            # Each leg must be a straight rook run of at least one cell over
            # cells that are ALL unoccupied (pivot and landing cell included) ...
            if not self._clear_leg(s, start, pivot):
                raise ValueError(f"leg one is not a clear rook move: {move!r}")
            if not self._clear_leg(s, pivot, end):
                raise ValueError(f"leg two is not a clear rook move: {move!r}")
            # ... and leg two must turn 90 degrees (given both legs run on
            # exactly one axis, this is "leg one vertical <=> leg two horizontal")
            if (start % W == pivot % W) != (pivot // W == end // W):
                raise ValueError(f"leg two does not turn 90 degrees: {move!r}")
            board = list(s.board)
            board[pivot] = p                        # the mandatory article
            avocat = list(s.avocat)
            avocat[p] = end
            hand = list(s.hand)
            hand[p] -= 1
            return WState(tuple(board), tuple(avocat), tuple(hand), s.taken,
                          1 - p, None, s.ply + 1)

        if len(cells) == 2:                         # one jump of a capture
            src, land = cells
            if s.chain is not None and src != s.chain:
                raise ValueError(f"must continue the chain from {cid(s.chain)}")
            dc, dr = land % W - src % W, land // W - src // W
            if (dc, dr) not in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                raise ValueError(f"not an orthogonal jump: {move!r}")
            over = (src + land) // 2
            if s.board[src] != p or s.board[over] != 1 - p:
                raise ValueError(f"illegal capture {move!r}")
            if self._occupied(s, land):
                raise ValueError(f"the cell beyond is not free: {move!r}")
            board = list(s.board)
            board[src] = -1
            board[over] = -1                        # removed at once, cannot be re-jumped
            board[land] = p
            taken = list(s.taken)
            taken[p] += 1
            nxt = WState(tuple(board), s.avocat, s.hand, tuple(taken),
                         p, land, s.ply + 1)
            # Chains are optional but the turn only continues while one exists.
            for _ in self._jumps(nxt, p, land):
                return nxt
            return WState(nxt.board, nxt.avocat, nxt.hand, nxt.taken,
                          1 - p, None, nxt.ply)

        raise ValueError(f"unparseable move {move!r}")

    def is_terminal(self, s: WState) -> bool:
        if s.ply >= PLY_CAP:
            return True
        if s.chain is not None:
            return False
        return not self._any_detour(s, s.to_move)

    # ---- scoring ---------------------------------------------------------
    def score(self, s: WState, seat: int) -> int:
        total = sum(VALUES[i] for i in range(N) if s.board[i] == seat)
        return total + s.taken[seat]

    def returns(self, s: WState) -> list:
        if not self.is_terminal(s):
            return [0.0, 0.0]
        a, b = self.score(s, 0), self.score(s, 1)
        if a > b:
            return [1.0, -1.0]
        if b > a:
            return [-1.0, 1.0]
        return [0.0, 0.0]                   # a genuine tie is an honest DRAW

    def heuristic(self, s: WState) -> list:
        import math
        v = math.tanh((self.score(s, 0) - self.score(s, 1)) / 24.0)
        return [v, -v]

    # ---- persistence -----------------------------------------------------
    def serialize(self, s: WState) -> dict:
        return {"board": list(s.board), "avocat": list(s.avocat),
                "hand": list(s.hand), "taken": list(s.taken),
                "to_move": s.to_move, "chain": s.chain, "ply": s.ply}

    def deserialize(self, d: dict) -> WState:
        return WState(board=tuple(d["board"]), avocat=tuple(d["avocat"]),
                      hand=tuple(d["hand"]), taken=tuple(d["taken"]),
                      to_move=int(d["to_move"]),
                      chain=None if d["chain"] is None else int(d["chain"]),
                      ply=int(d["ply"]))

    # ---- presentation ----------------------------------------------------
    def describe_move(self, s: WState, move: str) -> str:
        if move == "done":
            return "§ stop"
        cells = [_idx(t) for t in move.split(">")]
        if len(cells) == 3:
            start, pivot, end = cells
            return (f"A {_san(start)}-{_san(pivot)}-{_san(end)}"
                    f" §{_san(pivot)}({VALUES[pivot]})")
        src, land = cells
        return f"§{_san(src)}x{_san((src + land) // 2)}-{_san(land)}"

    def render(self, s: WState, perspective=None) -> dict:
        labels, tints = {}, {}
        for i in range(N):
            if i in CORNERS:
                tints[cid(i)] = (_START_TINT[0] if i == START[0]
                                 else _START_TINT[1] if i == START[1] else _IDLE_TINT)
            else:
                labels[cid(i)] = str(VALUES[i])
                tints[cid(i)] = _RING_TINT[VALUES[i]]

        pieces = [{"cell": cid(i), "owner": s.board[i]}
                  for i in range(N) if s.board[i] != -1]
        for seat in (0, 1):
            pieces.append({"cell": cid(s.avocat[seat]), "owner": seat, "glyph": "A"})

        a, b = self.score(s, 0), self.score(s, 1)
        tally = (f"{SEAT_NAMES[0]} {a} — {SEAT_NAMES[1]} {b}"
                 f"  |  §  in hand {s.hand[0]}/{s.hand[1]}"
                 f"  |  taken {s.taken[0]}/{s.taken[1]}")
        if self.is_terminal(s):
            head = ("Draw" if a == b else
                    f"{SEAT_NAMES[0 if a > b else 1]} wins")
            caption = f"Game over — {head}. {tally}"
        elif s.chain is not None:
            caption = (f"{SEAT_NAMES[s.to_move]} may jump again from "
                       f"{_san(s.chain)} or stop. {tally}")
        else:
            caption = f"{SEAT_NAMES[s.to_move]} to move. {tally}"

        spec = {
            "board": {"type": "square", "width": W, "height": H,
                      "labels": labels, "tints": tints},
            "pieces": pieces,
            "caption": caption,
            "actionNames": {"done": "Stop capturing"},
        }
        if s.chain is not None:
            spec["highlights"] = [{"cell": cid(s.chain), "kind": "last-move"}]
        return spec
