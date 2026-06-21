# Dou Shou Qi (Jungle / Animal Chess)

**Dou Shou Qi** (鬥獸棋, "Game of Fighting Animals"), also called **Jungle**,
**The Jungle Game**, or **Animal Chess**, is a traditional two-player Chinese
capture game. You win by marching one of your animals into the opponent's *den*.

## The board

A grid of **7 columns × 9 rows**. Cells are written `col,row` with columns
`0..6` (left to right) and rows `0..8`. Red (player 0) starts at the row-0 end;
Blue (player 1) starts at the row-8 end.

Three kinds of special terrain:

- **River (water)** — two 2-column × 3-row pools in the middle of the board:
  rows 3, 4, 5 of columns **{1, 2}** and columns **{4, 5}** (12 water squares in
  total). Columns 0, 3 and 6 are dry "land bridges" across the river.
- **Den** — each side's home square, at the back-centre: Red's den is `3,0`,
  Blue's den is `3,8`.
- **Traps** — the three squares immediately around each den. Red's traps are
  `2,0`, `4,0`, `3,1`; Blue's traps are `2,8`, `4,8`, `3,7`.

## The animals (ranks)

Each side has eight pieces. From highest rank to lowest:

| Rank | Animal   | Label |
|-----:|----------|:-----:|
| 8 | Elephant | E |
| 7 | Lion     | L |
| 6 | Tiger    | T |
| 5 | Leopard  | P |
| 4 | Wolf     | W |
| 3 | Dog      | D |
| 2 | Cat      | C |
| 1 | Rat      | R |

### Starting position (as implemented)

Red (player 0):

- Lion `0,0`, Tiger `6,0`
- Dog `1,1`, Cat `5,1`
- Rat `0,2`, Leopard `2,2`, Wolf `4,2`, Elephant `6,2`

Blue (player 1) is the point-mirror of Red through the centre of the board:

- Lion `6,8`, Tiger `0,8`
- Dog `5,7`, Cat `1,7`
- Rat `6,6`, Leopard `4,6`, Wolf `2,6`, Elephant `0,6`

This is the standard Jungle opening setup: the two strongest jumpers (Lion and
Tiger) sit in the back corners, the Dog and Cat flank just in front of the den,
and the Rat / Leopard / Wolf / Elephant stand on the third rank.

## Movement

All pieces move **one square orthogonally** (up, down, left, or right — never
diagonally) to an empty square or onto a capturable enemy.

A piece may **never enter its own den**.

### Capturing (rank rule)

A piece may capture an enemy piece whose rank is **equal to or lower than** its
own, with one exception:

- The **Rat (1) captures the Elephant (8)**, and the **Elephant may not capture
  the Rat**.

All other matchups go by rank: e.g. Lion (7) beats Tiger (6) and everything
below it, equal ranks capture each other, etc.

### The river

- **Only the Rat may enter the water.** Every other animal must go around (via
  the land bridges or by jumping — see below).
- A **Rat in the water cannot capture a piece on land**, and a **land piece
  cannot capture a Rat that is in the water.** Capture across the bank is
  forbidden; only a water-Rat may capture another water-Rat (when adjacent in
  the river). In particular, a Rat in the water **cannot capture the Elephant**
  standing on the land.

### Lion / Tiger river jump

The **Lion** and the **Tiger** may **leap straight across a river pool**,
horizontally or vertically, landing on the first dry square beyond the water.
The jump is **blocked if any Rat (of either colour) occupies a water square in
the leap path.** If an enemy piece stands on the landing square, the jump
captures it (subject to the normal rank rule).

In this layout a vertical jump clears a 3-row pool and a horizontal jump clears
a 2-column pool.

### Traps

When an enemy piece stands on **one of your trap squares**, its rank is treated
as **0** for as long as it is there, so **any** of your pieces may capture it,
regardless of rank. (A piece on its *own* trap is unaffected.)

## Winning

You **win immediately** when you move any piece into the **enemy's den**. You
also win if your opponent has **no legal move** on their turn.

### Draws / termination

To guarantee the engine always terminates, a hard **ply cap of 400** is applied:
if neither side has won after 400 plies, the game is scored a **draw**. (In
practice a normal game ends in a den capture long before this.)

## Notes on this implementation

- This package uses the most common modern ruleset. Some traditional variants
  differ on edge cases (e.g. whether a Rat must be *outside* the water to attack,
  or precise river-jump blocking) — the choices made here are stated above and
  are the authoritative description of what this package does.
- The river-jump block rule used here is: a jump is blocked only by a Rat
  actually standing **on a water square in the path**. A Rat sitting on a dry
  land bridge does not block a jump.
- Trapped pieces are demoted to rank 0 only while standing on the trap; moving
  off the trap restores the normal rank.
