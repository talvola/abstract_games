# Five Field Kono (오밭고누)

A traditional two-player **racing** game from Korea. The name *kono* (고누)
refers to a family of Korean board games; the "five field" version is played on a
grid of **five points by five points** (hence "five field"). The object is a
**race to swap home territories** — there is no fighting.

## Board

A **5×5 grid of points** (25 cells), addressed as `c,r` with column `c` and row
`r` both running `0..4`. (Physically the game is drawn as a 4×4 grid of squares
with pieces on the line intersections; the 5×5 array of intersections is what we
model as cells.)

## Starting position

Each player has **7 pieces**.

- **Player 0 (Bottom):** the entire bottom row `r=0` — `0,0 1,0 2,0 3,0 4,0` —
  **plus** the two **outer** points of the second row: `0,1` and `4,1`.
- **Player 1 (Top):** the mirror image — the entire top row `r=4` —
  `0,4 1,4 2,4 3,4 4,4` — **plus** `0,3` and `4,3`.

This is the standard documented layout: *the whole back row of five, plus the two
end points of the second row.* The two middle points of each second row (`1,1`,
`2,1`, `3,1` and `1,3`, `2,3`, `3,3`) and the entire middle row `r=2` start
empty.

## Movement

On your turn you move **one** of your pieces **one step diagonally** to an
**adjacent empty point**. All **four** diagonal directions are allowed (forward
*and* backward). A piece may not move onto an occupied point, and it may not jump.

There are **no captures of any kind** — pieces never leave the board.

(Some descriptions emphasize "diagonally forward or backward"; all consulted
sources agree that ordinary diagonal movement in any of the four directions to an
empty point is the rule, with no forward-only restriction. This package
implements **any diagonal direction**.)

## Winning

You win the instant **all seven** of your pieces occupy the **exact set of points
your opponent started on** — i.e. you have completely traded places with the
enemy's home. For Bottom that target is Top's seven start points
(`0,4 1,4 2,4 3,4 4,4 0,3 4,3`); for Top it is Bottom's seven
(`0,0 1,0 2,0 3,0 4,0 0,1 4,1`).

The race is feasible for both sides: the two home sets contain the same pattern
of diagonal "colours" (cell parities), so each piece can in principle reach a
distinct target square by diagonal steps.

## Draws / termination

Because pieces may move backward as well as forward, play could in theory cycle.
To guarantee the game always ends, this package applies a **hard ply cap**: if
neither player has won after a large number of plies, the game is a **draw**.
Likewise, if the player to move has **no legal move**, they **pass**; a mutual
deadlock therefore also ends in a draw via the ply cap. (Skilled play normally
reaches a win well before the cap; the cap exists only to forbid infinite games.)

## Implementation notes / choices

- **Board model:** 5×5 array of intersection cells, `c,r` ∈ `0..4`.
- **Start layout:** back row (5) + the two outer second-row points (2) = 7, the
  most widely documented standard setup, flagged here as the choice made.
- **Movement:** any of the four diagonals to an empty point; **no** forward-only
  restriction (sources do not require one).
- **Win:** occupy the opponent's exact 7 starting points.
- **Draw:** ply-cap draw + pass-on-no-move (added for guaranteed termination; not
  part of the historical ruleset, which simply assumes someone wins).
