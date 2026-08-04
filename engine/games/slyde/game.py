"""Slyde (Mike Zapawa, 2020).

A full checkerboard of pieces, every one of them MOBILE at the start.  On your
turn you swap one of your own mobile pieces with an orthogonally adjacent
mobile enemy piece; your piece then becomes FIXED forever, the opponent's stays
mobile.  When nobody can move any more, the player with the biggest group wins
-- and if the biggest groups tie, the second biggest are compared, then the
third, and so on ("the cascading biggest group goal", the designer's phrase).

Sources implemented here (see rules.md for the full provenance):
  * MindSports, https://mindsports.nl/index.php/the-pit/1019-slyde -- the
    designer's canonical page (12x12, and the anti-mirroring state-change rule).
  * Kanare Abstract's published rulebook Slyde_EN.pdf (2024-06-13) -- the same
    game reskinned as sliding black TILES over white EMPTY cells, 8x8 / 10x10.
    It is the explicit source for "an isolated tile/cell is also considered a
    group of size 1" and for "multiple groups of the same colour and size are
    taken as separate groups for comparison".

Both sheets agree move-for-move; the tile reskin maps onto the piece version as
  black tile   <-> Black piece      empty cell <-> White piece
  slide a tile <-> swap the two     the disc   <-> the FIXED marker
and its "White places a disc on the empty cell that just appeared / Black
places a disc on the tile that was just moved" is exactly "the swapping
player's own piece becomes fixed".
"""
import math
from dataclasses import dataclass, replace
from typing import List, Optional, Tuple

from agp.game import Game

# ---------------------------------------------------------------------------
# Seats.  Ground truth OUTSIDE this module: BOTH sheets say the White player
# moves first -- MindSports "White begins", Kanare "The White player moves
# first, then turns alternate".  Seat 0 is therefore White.  selftest.py pins
# this to the Kanare rulebook's GROUPS figure, whose printed caption names the
# owner of the size-18 group as the winner.
SEAT_NAMES = ("White", "Black")
WHITE, BLACK = 0, 1

SIZES = (4, 6, 8, 10, 12)
DEFAULT_SIZE = 12

# The termination backstop, in plies.  `cells` = size*size = the number of
# pieces, which is the game's OWN bound: every swap fixes exactly one
# previously-mobile piece and a fixed piece can never be swapped, so with the
# anti-mirroring rule OFF the number of mobile pieces strictly decreases and the
# game ends within `cells` plies -- the cap is then provably unreachable and
# provably not outcome-load-bearing.  With the anti-mirroring rule ON an
# "unfix" toggle can hand mobility back, so the monovariant is only
# non-increasing across a toggle+swap pair; the cap then allows the whole board
# to be recycled CAP_RECYCLES times over before the game simply ENDS and is
# scored by the normal cascade -- NOT a forced draw, so a capped game still
# reports the honest majority on the board.  See rules.md ("Termination") for
# what is proved and what is only measured.
CAP_RECYCLES = 4


def ply_cap(size: int) -> int:
    return CAP_RECYCLES * size * size


# --- geometry --------------------------------------------------------------

def cell_name(c: int, r: int) -> str:
    """The move-notation / RenderSpec id of column `c`, row `r` (both 0-based).

    Board.jsx draws row 0 at the BOTTOM, so r grows upwards on screen.
    """
    return f"{c},{r}"


def parse_cell(cid: str) -> Tuple[int, int]:
    c, r = cid.split(",")
    return int(c), int(r)


def algebraic(c: int, r: int) -> str:
    """Display-only chess-style name for the move log: file letter + rank."""
    return f"{chr(ord('a') + c)}{r + 1}"


def idx(c: int, r: int, size: int) -> int:
    return r * size + c


def neighbours(i: int, size: int) -> Tuple[int, ...]:
    """Orthogonal neighbours only.

    Both sheets are explicit and agree: MindSports scores groups by
    "orthogonal connectivity of like-colored pieces", Kanare says a group is
    "connected to each other vertically and horizontally" and a slide goes
    "horizontally or vertically to an adjacent empty space".  The same
    4-neighbourhood therefore serves both movement and grouping.
    """
    c, r = i % size, i // size
    out = []
    if c > 0:
        out.append(i - 1)
    if c < size - 1:
        out.append(i + 1)
    if r > 0:
        out.append(i - size)
    if r < size - 1:
        out.append(i + size)
    return tuple(out)


# --- state -----------------------------------------------------------------

@dataclass(frozen=True)
class SState:
    size: int
    colour: Tuple[int, ...]      # per cell: 0 = White piece, 1 = Black piece
    fixed: Tuple[int, ...]       # per cell: 1 = fixed (immobile) for ever
    to_move: int
    ply: int
    anti_mirror: bool
    last: Tuple[str, ...] = ()   # cells touched by the previous move (highlights)


# --- symmetry (the anti-mirroring rule) ------------------------------------

def is_symmetric(s: SState) -> bool:
    """Is the position "symmetric" for the anti-mirroring rule?

    The designer's sheet says only "if a symmetric position arises" and never
    defines it.  The reading implemented here -- a LEFT-RIGHT or TOP-BOTTOM
    mirror under which every cell's colour is the OPPOSITE of its image's and
    every cell's fixed/mobile state is the SAME -- is the one used by the
    AbstractPlay implementation, and it is the one the sheet's own worked
    example needs: after 1.f3-f4 f10-f9 2.k6-j6 k7-j7 the position is a
    top-bottom mirror with the colours exchanged.  (selftest.py replays that
    example move for move.)  See rules.md.
    """
    n, col, fx = s.size, s.colour, s.fixed
    for horizontal in (True, False):
        ok = True
        for r in range(n):
            for c in range(n):
                i = r * n + c
                j = r * n + (n - 1 - c) if horizontal else (n - 1 - r) * n + c
                if col[i] == col[j] or fx[i] != fx[j]:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return True
    return False


# --- scoring ---------------------------------------------------------------

def group_sizes(colour: Tuple[int, ...], size: int, player: int) -> List[int]:
    """Sizes of `player`'s orthogonally-connected groups, largest first.

    A lone piece IS a group of size 1 and is listed individually -- Kanare's
    rulebook says so twice ("Note that an isolated tile/cell is also considered
    a group of size 1"; "If there are multiple groups of the same color and
    size, they are taken as separate groups for comparison") and its GROUPS
    figure circles each lone piece on its own -- two separate "1"s for Black
    and two more for White.
    """
    seen = [False] * len(colour)
    out = []
    for start in range(len(colour)):
        if colour[start] != player or seen[start]:
            continue
        seen[start] = True
        stack = [start]
        n = 0
        while stack:
            i = stack.pop()
            n += 1
            for j in neighbours(i, size):
                if colour[j] == player and not seen[j]:
                    seen[j] = True
                    stack.append(j)
        out.append(n)
    out.sort(reverse=True)
    return out


def compare_scores(white: List[int], black: List[int]) -> int:
    """+1 White ahead, -1 Black ahead, 0 an exact tie.

    The cascading goal: compare biggest to biggest, then second biggest to
    second biggest, and so on.  A missing group counts as 0 -- but that padding
    is VACUOUS here and is only defensive: both players always hold exactly
    size*size/2 pieces (a swap exchanges one piece of each colour and a
    state-change toggle moves none), so the two lists always have the same sum,
    and a list whose entries all match a prefix of a longer list would have the
    smaller sum.  selftest.py asserts the padding never decides anything.
    """
    for i in range(max(len(white), len(black))):
        w = white[i] if i < len(white) else 0
        b = black[i] if i < len(black) else 0
        if w != b:
            return 1 if w > b else -1
    return 0


def tally_text(sizes: List[int], keep: int = 6) -> str:
    """Compact caption form of a cascade list.

    A Slyde board opens with EVERY piece a lone group, so the raw list is 72
    entries long at 12x12.  The lone pieces are therefore shown as a COUNT
    ("+62x1") -- a display abbreviation only; `compare_scores` always sees them
    one by one, which is exactly the distinction the rulebook insists on.
    """
    big = [g for g in sizes if g > 1]
    ones = len(sizes) - len(big)
    parts = ",".join(str(g) for g in big[:keep]) + ("…" if len(big) > keep else "")
    if ones:
        parts = (parts + " " if parts else "") + f"+{ones}×1"
    return parts or "—"


class Slyde(Game):
    """Slyde -- swap, freeze, and grow the biggest group."""

    # --- setup -------------------------------------------------------------
    @property
    def num_players(self) -> int:
        return 2

    def initial_state(self, options=None, rng=None) -> SState:
        opts = options or {}
        size = int(opts.get("size", DEFAULT_SIZE))
        if size < 2 or size % 2:
            raise ValueError("Slyde needs an even board size of at least 2")
        anti = str(opts.get("anti_mirror", "on")) == "on"
        # White on the cells of even (c+r) parity.  The opposite parity is the
        # SAME game with the colours exchanged (a left-right mirror carries one
        # setup to the other and is an automorphism of adjacency, of grouping
        # and of the mirror-symmetry test), so this choice is unobservable --
        # the sheets accordingly do not specify it.  selftest.py proves it.
        colour = tuple((c + r) % 2 for r in range(size) for c in range(size))
        return SState(
            size=size,
            colour=colour,
            fixed=(0,) * (size * size),
            to_move=WHITE,
            ply=0,
            anti_mirror=anti,
        )

    def current_player(self, s: SState) -> int:
        return s.to_move

    # --- moves -------------------------------------------------------------
    def _swaps(self, s: SState) -> List[str]:
        n, col, fx, me = s.size, s.colour, s.fixed, s.to_move
        out = []
        for i in range(n * n):
            if col[i] != me or fx[i]:
                continue
            for j in neighbours(i, n):
                if col[j] != me and not fx[j]:
                    out.append(f"{i % n},{i // n}>{j % n},{j // n}")
        return out

    def _toggles_available(self, s: SState) -> bool:
        # "If a symmetric position arises" -- the OPENING position is a mirror
        # of itself under both axes, but nothing has "arisen" yet and offering
        # White a free state change as move 1 would turn the anti-mirroring
        # rule into an opening advantage.  Excluding move 1 is what the
        # AbstractPlay implementation does and what BGG's description of the
        # game states ("if the board reaches a symmetric position (except on
        # the first move)").  See rules.md.
        return s.anti_mirror and s.ply > 0 and is_symmetric(s)

    def legal_moves(self, s: SState) -> List[str]:
        if s.ply >= ply_cap(s.size):
            return []
        moves = self._swaps(s)
        if self._toggles_available(s):
            n = s.size
            # A state change may target ANY piece "regardless of color", fixed
            # or mobile.  Encoded as a from==to path so the UI reads it as
            # "click the cell twice" rather than as an action button per cell.
            moves += [f"{i % n},{i // n}>{i % n},{i // n}" for i in range(n * n)]
        return moves

    def apply_move(self, s: SState, move: str, rng=None) -> SState:
        frm, to = move.split(">")
        fc, fr = parse_cell(frm)
        tc, tr = parse_cell(to)
        n = s.size
        i, j = idx(fc, fr, n), idx(tc, tr, n)
        fixed = list(s.fixed)
        colour = list(s.colour)
        if i == j:                       # anti-mirroring state change
            fixed[i] ^= 1
        else:                            # the standard swap
            colour[i], colour[j] = colour[j], colour[i]
            fixed[j] = 1                 # the swapping player's own piece
            fixed[i] = 0                 # the opponent's piece stays mobile
        return replace(
            s,
            colour=tuple(colour),
            fixed=tuple(fixed),
            to_move=1 - s.to_move,
            ply=s.ply + 1,
            last=(frm,) if i == j else (frm, to),
        )

    # --- end of game -------------------------------------------------------
    def is_terminal(self, s: SState) -> bool:
        return not self.legal_moves(s)

    def scores(self, s: SState) -> Tuple[List[int], List[int]]:
        return (group_sizes(s.colour, s.size, WHITE),
                group_sizes(s.colour, s.size, BLACK))

    def winner(self, s: SState) -> Optional[int]:
        w, b = self.scores(s)
        cmp = compare_scores(w, b)
        return None if cmp == 0 else (WHITE if cmp > 0 else BLACK)

    def returns(self, s: SState) -> List[float]:
        w = self.winner(s)
        if w is None:
            return [0.0, 0.0]
        return [1.0, -1.0] if w == WHITE else [-1.0, 1.0]

    # --- serialisation -----------------------------------------------------
    def serialize(self, s: SState) -> dict:
        return {
            "size": s.size,
            "colour": list(s.colour),
            "fixed": list(s.fixed),
            "to_move": s.to_move,
            "ply": s.ply,
            "anti_mirror": s.anti_mirror,
            "last": list(s.last),
        }

    def deserialize(self, d: dict) -> SState:
        return SState(
            size=int(d["size"]),
            colour=tuple(int(x) for x in d["colour"]),
            fixed=tuple(int(x) for x in d["fixed"]),
            to_move=int(d["to_move"]),
            ply=int(d["ply"]),
            anti_mirror=bool(d["anti_mirror"]),
            last=tuple(d["last"]),
        )

    # --- bot evaluation ----------------------------------------------------
    def heuristic(self, s: SState) -> List[float]:
        """Coalescence: the difference of the two players' sums of SQUARED
        group sizes, squashed to (-1, +1).

        The cascading goal is lexicographic and so has no gradient; the sum of
        squares is the natural continuous proxy, since it is minimal when every
        piece is a lone group (the opening position, where both sides score
        size*size/2) and maximal when an army is one solid block.

        MEASURED, not assumed, and measured through the CONSUMER: with the
        rollout cutoff forced (`max_rollout=4`) this scores 0.925 over 120
        head-to-head games on 6x6 against the same bot with no heuristic at
        all, next to a 0.533 none-vs-none control.

        Where it BITES: an eval is only consulted when a rollout is truncated.
        At the default `max_rollout=50` a rollout from the opening reaches the
        cutoff on 100% of iterations on the DEFAULT 12x12 board (random games
        run ~94 plies) but on 0% at 8x8 (~41 plies), where rollouts always
        reach a real terminal and this function is never called at all.
        Averaged over a WHOLE game the rate is lower, because rollouts started
        from deep nodes have less than 50 plies left to run: 46.8% at 12x12,
        24.1% at 10x10, 0.0% at 8x8 and below.  So it
        earns its place on the big boards and is simply inert on the small
        ones -- not a bad eval, an unused one.

        Returns one payoff PER SEAT, as `returns` does.
        """
        half = s.size * s.size / 2.0
        w = sum(g * g for g in group_sizes(s.colour, s.size, WHITE))
        b = sum(g * g for g in group_sizes(s.colour, s.size, BLACK))
        v = math.tanh(4.0 * (w - b) / (half * half))
        return [v, -v]

    # --- presentation ------------------------------------------------------
    def describe_move(self, s: SState, move: str) -> str:
        frm, to = move.split(">")
        fc, fr = parse_cell(frm)
        tc, tr = parse_cell(to)
        if (fc, fr) == (tc, tr):
            was = s.fixed[idx(fc, fr, s.size)]
            return f"{'unfix' if was else 'fix'} {algebraic(fc, fr)}"
        return f"{algebraic(fc, fr)}-{algebraic(tc, tr)}"

    def render(self, s: SState, perspective=None) -> dict:
        n = s.size
        pieces = []
        for i in range(n * n):
            p = {"cell": f"{i % n},{i // n}", "owner": s.colour[i]}
            if s.fixed[i]:
                # A fixed piece reads as a ring with its own colour inside --
                # the rulebook's grey disc sitting on the piece.
                p["shape"] = "ring"
                p["inner"] = s.colour[i]
            pieces.append(p)
        tally = " · ".join(f"{SEAT_NAMES[seat]} {tally_text(sizes)}"
                           for seat, sizes in zip((WHITE, BLACK), self.scores(s)))
        if self.is_terminal(s):
            win = self.winner(s)
            head = "Draw" if win is None else f"{SEAT_NAMES[win]} wins"
        else:
            head = f"{SEAT_NAMES[s.to_move]} to move"
            if self._toggles_available(s):
                head += " (symmetric: may click a piece twice to fix/unfix it)"
        return {
            "board": {"type": "square", "width": n, "height": n},
            "pieces": pieces,
            "highlights": [{"cell": c, "kind": "last-move"} for c in s.last],
            "caption": f"{head} — groups {tally}",
        }
