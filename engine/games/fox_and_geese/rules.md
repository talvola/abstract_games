# Fox and Geese

An asymmetric "tafl"-descended **hunt game**: a single **Fox** is chased by a
flock of **Geese**. These are the rules *as implemented* in this package.

## Board

The cross- (plus-) shaped board of **33 points**: a 3×3 square in the centre with
a 2×3 arm on each of its four faces. The points sit on a 7×7 grid `(col, row)`
with `col, row` in `0..6`; the four 2×2 corner blocks are off the board.

Points are joined by **horizontal and vertical lines everywhere**, plus
**diagonal lines at the "strong" points** — those where `(col + row)` is even.
This is the classic **alquerque** pattern (the same "X-in-every-other-cell"
diagonals seen on the standard Fox-and-Geese / solitaire cross board). The centre
point `3,3` therefore has 8 neighbours; a "weak" edge point has 3–4.

Two pieces are *adjacent* when a marked line directly joins them. A move/jump may
only follow a marked line.

## Pieces & setup

- **Geese (seat 0):** 15 geese. They occupy the whole bottom arm (the six points
  `c,r` for `c∈{2,3,4}`, `r∈{5,6}`), the full row directly in front of it
  (`row 4`, seven points), and the two endpoints of the central row (`0,3` and
  `6,3`).
- **Fox (seat 1):** one fox, starting on the **centre point `3,3`**.

**The Geese move first.**

## Movement

- **Geese** move one piece one step along a line to an adjacent empty point, but
  only **forward, sideways, or diagonally forward** — toward the fox's half (here:
  toward **decreasing row**). A goose may **never** move backward or diagonally
  backward. Geese **never capture**.
- **Fox** moves one step along a line to an adjacent empty point **in any
  direction**, OR **captures** by **jumping**.

## Capturing (Fox only)

If a goose sits on a point adjacent to the fox along a marked line, and the point
*directly beyond* it on that same line is empty, the fox may **jump over the
goose** to that empty point, **removing the jumped goose** (as in draughts).

- **Multi-jumps chain:** immediately after landing, the fox may jump again (along
  any line), removing another goose, and so on.
- **Captures are NOT mandatory.** The fox may instead make a plain step, and a
  jumping fox may stop after any jump even if a further jump is available.

In move notation, a single step or single jump is `from>to`; a multi-jump is the
full landing chain, e.g. `3,3>3,5>5,5`.

## Winning

- **Geese win** by **trapping the fox** — on the fox's turn it has no legal move
  (no empty adjacent point and no available jump).
- **Fox wins** by **capturing enough geese to make trapping impossible** —
  implemented as **reducing the geese to 2 or fewer**.

## Termination (draws)

Geese can shuffle sideways/forward without capturing, so two guards force a draw:

- **No-progress:** 60 plies pass with no capture → draw.
- **Hard ply cap:** 400 plies total → draw.

## Interpretations & source notes

Sources broadly agree on the game but differ in details; the choices above follow
the most-documented **modern standard** (Masters of Games, Cyningstan,
bead.game), with these explicit decisions:

- **Geese count = 15.** The earliest (Gloucester Cathedral) form used 13 geese on
  a diagonals-only board; the traditional 13-geese game is known to favour the
  fox, so the better-balanced modern standard uses 15 (variants exist with 17/18
  or two foxes). We implement the documented 15-geese cross board.
- **Diagonals = alquerque pattern** (`(col+row)` even). The board "has diagonal
  lines in certain places"; this is the standard cross board's X-marked layout.
  (An orthogonal-only board is a known balancing house variant; not implemented.)
- **Geese cannot move backward** (forward / sideways / diagonally-forward only),
  per Masters of Games and Wikipedia.
- **Multi-jumps allowed, captures not mandatory** (Wikipedia / bead.game — this
  is the "Fox and Geese", distinct from Halatafl where capture is compulsory).
- **Fox win threshold = 2 geese** (Masters of Games: "a player loses … by being
  reduced to two pieces").
- **Geese move first** (Masters of Games / Cyningstan; some sources roll for it).

Official source: <https://en.wikipedia.org/wiki/Fox_games>
