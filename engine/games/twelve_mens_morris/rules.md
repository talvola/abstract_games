# Twelve Men's Morris

Twelve Men's Morris is the classic mill game played on the **same 24-point board**
as Nine Men's Morris — three concentric squares joined by spokes at the middle of
each side — **plus four diagonal lines** that join the corners of the rings. The
rules **as implemented** here follow Nine Men's Morris, with twelve men per side.

## The board

The 24 points sit on the corners and side-midpoints of the three squares. Two
points are **adjacent** when a line joins them directly:

- along the **edges** of each square;
- along the four **mid-side spokes** that connect the middle squares to the points
  just inside and outside them;
- along the four **corner diagonals** — a new line at each of the four corners,
  joining the outer, middle and inner corner (e.g. `0,0 — 1,1 — 2,2` at the
  top-left). These give each of the eight corner points an extra adjacency across
  the rings.

The centre is not a point.

A **mill** is three of your men in a row along one of the **20 lines**: four edges
on each of the three squares (12), the four mid-side spokes (4), and the four new
corner diagonals (4). Because of the diagonals, every point now lies on **two or
three** mills (the corner points lie on three), which is why this variant is
famously prone to draws.

## Phase 1 — placing

Each player has **twelve men**. Players alternate **placing** one man on any empty
point (White/red first). Whenever you complete a mill — in this phase or the next —
you immediately **remove one of the opponent's men** from the board.

(With twelve men per side, 24 of the 24 points are filled by the end of placement
if no man has been captured; in practice mills during placement free up points.)

## Phase 2 — moving

Once all men have been placed, players alternate **moving** one man along a line to
an **adjacent empty point** (the corner diagonals are valid lines to move along).
Completing a mill again removes an enemy man.

**Flying:** when you are reduced to exactly **three men**, you may move a man to
*any* empty point, not just an adjacent one. This is the standard rule and the
default; it can be turned off with the *Flying* option, in which case you must
always move to an adjacent point.

## Removing a man

When you form a mill you remove one enemy man of your choice, with one restriction:
**you may not take a man that is part of a mill, unless every enemy man is in a
mill** (then any may be taken). Forming **two mills at once** still removes only
**one** man.

## Winning and drawing

You **win** when the opponent is reduced to **two men** (too few to form a mill),
or when the opponent has **no legal move** on their turn. These loss conditions
apply only once the placing phase is over.

The game is a **draw** by repetition (the same position, with the same player to
move, occurring a third time) or if **50 plies** pass with no mill formed and no
man placed (a no-progress rule that also guarantees the game ends).

There is one more draw unique to the twelve-man board: because 12 + 12 men exactly
fill all 24 points, if **neither side forms a mill during placement the board ends
up completely full** and nobody can slide. This *full-board deadlock* is scored as
a **draw**, not a loss for the player to move — this is the traditional rule and
the reason Twelve Men's Morris is famously more drawish than the nine-man game.
(A player who is blocked with empty points still on the board does lose, as
above; only the genuinely full board is the draw.)

## Notation

During placing, a move is a single point like `3,0` (shown as `@3,0` in the log).
During moving, it is `from>to`, e.g. `3,0>3,1` (shown as `3,0-3,1`). When you form
a mill, your next click removes an enemy man (shown as `x3,2`). Points are named by
their `x,y` coordinate on the board diagram.

## Ruleset choices

- **Diagonals only at the corners.** The four added lines are the corner spokes
  `outer-corner — middle-corner — inner-corner` for each of the four corners,
  matching the standard Twelve Men's Morris / Morabaraba board. No diagonals are
  added through the centre, and no extra ring-edge lines are introduced.
- **Twelve men per side**, otherwise identical to the Nine Men's Morris
  implementation in this repository (the ring/spoke core, mill detection, removal
  restriction, flying, and the draw clock are shared logic, just extended with the
  diagonal adjacencies and mills).
- **Flying** defaults to allowed, with a manifest option to disable it (exactly as
  Nine Men's Morris).
