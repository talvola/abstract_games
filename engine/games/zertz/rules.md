# ZÈRTZ

ZÈRTZ is the second game of Kris Burm's GIPF project. It is played on a board of
rings that **shrinks** as the game goes on, with a **shared pool** of neutral
marbles. You don't own marbles on the board — you score by **capturing** them.

This page documents the rules *as implemented* in this package.

## Board and pool (verified)

- **Board:** 37 rings forming a hexagon, four rings to a side (a "hexhex" of
  side 4). Rings use axial coordinates `q,r`.
- **Shared marble pool:** **6 white, 8 grey, 10 black** marbles. Both players
  draw from this one common supply. Marbles on the board are neutral — not owned.

## A turn — exactly one of two kinds

A turn is either a **capture** or a **placement**. **Capturing is mandatory:** if
any capturing jump is available you *must* jump; you may not place a marble.

### Placement (when no capture is possible)

1. Take a marble of **any colour** from the pool and place it on **any vacant
   ring**.
2. Then **remove one "free" ring**.

A ring is **free** if it is vacant (no marble) and sits at the edge so it can be
slid off the board without disturbing the others. Concretely: a vacant ring is
free when it has **two consecutive empty/absent neighbour directions** (a gap, in
the cyclic order of the six hex directions, wide enough to slide it out the
edge). If no ring is free, you simply place the marble and the ring-removal step
is skipped.

This is modelled as a **two-step turn** (like Nine Men's Morris's
place-then-remove): the place move is `W@q,r` / `G@q,r` / `B@q,r`; the same
player then makes a follow-up `xq,r` move to remove a free ring.

### Capture (mandatory when available)

A marble **jumps** an orthogonally-adjacent marble — one of the six hex
directions — of **any colour**, landing on the vacant ring immediately beyond it.
The jumped marble is removed and added to the **jumping player's reserve**.

- Captures are **mandatory**: if a jump exists you must capture instead of place.
- Captures **chain**: after a jump, if the same marble can jump again it **must**
  keep jumping. When several continuations exist, the player chooses the path.

A capture is entered one jump at a time as the path of cell ids, e.g.
`q,r>q2,r2` then `q2,r2>q3,r3`.

## Isolation

When a group of rings is **completely cut off** from the rest of the board and
**every** ring in that isolated group carries a marble, all those marbles are
**captured by the player who just moved** and the rings are removed. (If any ring
in the cut-off group is still vacant, nothing is captured yet.)

Isolation is resolved at **two** moments:

- **After a ring removal** that cuts a fully-occupied group off from the board.
- **After a placement** that fills an isolated group's **last vacant ring** —
  the group is now fully occupied, so the mover claims it immediately. This
  matters when the placement completes the isolation and **no free ring is
  removable that turn**: the turn ends with no removal step, yet the cut-off,
  fully-occupied group is still claimed (and may complete a winning set).

## Winning

The first player whose **captured reserve** contains a **winning set** wins:

- **3 white + 3 grey + 3 black**, OR
- **4 white**, OR
- **5 grey**, OR
- **6 black**.

(These are the majorities n/2+1 of each colour, or three of each.)

## Draw / dead game

If the board and pool are exhausted with neither player at a winning set, the
game is a draw. A defensive ply cap (400 plies) also forces a draw, so the game
always terminates.

## Notation summary

| Move | Meaning |
|---|---|
| `W@q,r` / `G@q,r` / `B@q,r` | place a white/grey/black marble on ring `q,r` |
| `xq,r` | remove free ring `q,r` (the second step of a placement turn) |
| `q,r>q2,r2` | jump the marble between the two cells, capturing it (chains) |

## Implementation notes / ruleset choices

- All rule numbers above (37 rings, 6/8/10 pool, the four winning sets, mandatory
  chained jumps, isolation captured by the mover) are taken from the official
  Kris Burm / gipf.com and Rio Grande Games rules and corroborated by Wikipedia
  and BoardGameGeek.
- The "free ring" test is the standard computational encoding of "slidable off
  the edge": a vacant ring with two *consecutive* missing/empty neighbour
  directions. The very first removals (full board) are the outermost rings, as in
  the physical game.
- Larger tournament boards (40/43/44/48 rings) and "Blitz" pool variants exist;
  this package implements the standard 37-ring game with the 6/8/10 pool.
