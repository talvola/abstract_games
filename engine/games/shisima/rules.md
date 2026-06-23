# Shisima

**Shisima** is a traditional two-player three-in-a-row sliding game from Kenya.
The word *shisima* means "body of water" — the name of the central point — and
the playing pieces are called *imbalavali*, "water bugs". It belongs to the same
family as tic-tac-toe and Three Men's Morris (Tapatan): pieces are moved, not
captured, to make a line.

## The board

The board has **9 points**:

* **8 rim points** at the corners of an **octagon**, indexed `0`–`7` clockwise
  from the top;
* **1 central point**, the *shisima* (`c`), the "body of water".

The lines drawn on the board are:

1. the **octagon rim** — each rim point joined to its two neighbours around the
   ring; and
2. four **diametrical lines** — each rim point joined *through the centre* to the
   diametrically opposite rim point (0–4, 1–5, 2–6, 3–7).

### Adjacency (movement)

You may slide a piece only to an **adjacent** empty point — adjacency is defined
by those marked lines:

* each **rim point** is adjacent to its **two ring-neighbours** (mod 8) and to
  the **centre** (the centre is the next point along its diameter);
* the **centre** is adjacent to **all 8 rim points**;
* a rim point is **not** adjacent to the opposite rim point — the centre lies
  between them on the diameter, so you cannot jump across.

## Pieces and setup

Each player has **three** pieces. They start on three successive rim points, with
the two sets directly opposite each other:

* **Player 1 (Black):** rim points `0, 1, 2`;
* **Player 2 (White):** rim points `4, 5, 6`.

Rim points `3` and `7` and the centre `c` start empty. (Each player's set of
three has a vacant rim point at both ends, matching the traditional setup.)

## Playing a turn

Players alternate, Black first. On your turn you **slide one of your pieces along
a marked line to an adjacent empty point**. There are **no captures** and **no
placement phase** — the pieces are on the board from the start and never leave it.

## Winning

You **win** the instant your three pieces form a **straight line through the
centre** — that is, one of the four diametrical lines:

`{rim i, centre, rim i+4}` for i = 0..3 — namely `{0,c,4}`, `{1,c,5}`,
`{2,c,6}`, `{3,c,7}`.

Such a line is *centre + two opposite rim points*. On this board these are the
only sets of three collinear points, so "three-in-a-row" and "three-in-a-row
through the centre" are the same thing — a winning line **always** occupies the
shisima.

## Draws / termination

Sliding could in principle repeat forever. To guarantee the game ends, this
implementation declares a **draw** after a hard cap of `120` plies with no win.
(Traditionally a draw is agreed, or called when a position repeats; the ply cap
is a generous, never-reached safety net that also keeps automated play finite.)

## Ruleset notes (choices made here)

* **Adjacency.** Authoritative sources (Wikipedia and several
  math-education write-ups) describe the marked lines as the octagon rim plus
  four diameters meeting at the centre. This package implements exactly that:
  rim↔ring-neighbour and rim↔centre, with the centre adjacent to all rim points.
  No "long" rim↔opposite-rim adjacency exists (the centre is in the way).
* **Starting position.** Sources state each player's three pieces sit on three
  *successive* rim points, opposite each other, with a vacant point at each end
  of a set. `0,1,2` vs `4,5,6` is one such symmetric arrangement (any rotation is
  equivalent); the centre starts empty.
* **Winning line.** "A three-in-a-row along a diametrical line" — i.e. through
  the centre. There is no ambiguity here: the four diameters are the only lines
  of three points on the board.

## Source

Wikipedia: <https://en.wikipedia.org/wiki/Shisima>
