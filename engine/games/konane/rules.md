# Kōnane (Hawaiian Checkers)

Kōnane is the traditional Hawaiian stone-jumping game and a well-known
combinatorial-game-theory example. **Black** (player 0) moves first.

## Board & setup
An **N×N** board (size option: **6 / 8 / 10**, default **8**) starts
**completely filled** with stones in an alternating checkerboard pattern:

- A cell `(col, row)` holds a **black** stone when `col + row` is **even**.
- It holds a **white** stone when `col + row` is **odd**.

So the bottom-left corner `a1` is black, and the colors alternate from there.

## The opening (two removals)
Play begins by emptying two adjacent squares, one stone per player:

1. **Black removes one black stone** from a **corner** or from the board's
   **center**.
   - On an even-sized board (6/8/10) the "center" is the inner **2×2** block of
     four cells; the two of them that are black (even parity) are legal.
   - (On an odd board it would be the single middle cell.)
2. **White then removes one white stone that is orthogonally adjacent**
   (up/down/left/right) to the square Black just emptied.

After these two removals there are two adjacent empty squares, and normal play
begins with **Black** to move.

In the UI each opening removal is a **single click** on the stone to remove.

## Normal play — jumping
A move captures by **jumping orthogonally**:

- Pick one of your stones that sits **orthogonally next to an enemy stone**,
  with the square **immediately beyond that enemy empty**.
- Jump over the enemy stone into that empty square; the **jumped enemy stone is
  removed**.
- The **same stone may keep jumping in the *same* straight-line direction**
  over further enemy stones (each is removed), as long as each next enemy is
  adjacent and the square beyond is empty. **You may stop after any jump.**
- **No diagonal moves. No turning** during a multi-jump. **No promotion.**

Moves are written as the path of squares the stone visits, e.g. `c1>a1` (single
jump) or `g1>e1>c1` (double jump in a straight line).

## Winning
There are **no draws**: the **first player who cannot move loses** — equivalently,
the **last player able to make a capture wins** (the normal-play convention of
combinatorial game theory). A hard ply cap exists only as an engine safety net
and is not expected to trigger.

## Ruleset choices made by this package
- **Color/seat mapping:** Black = player 0 on even-parity cells, White =
  player 1 on odd-parity cells; Black moves first.
- **Opening:** the standard "remove from a corner or the center" rule. On even
  boards the center is the inner 2×2 block (the black cells of it are the legal
  Black removals); White's reply must be an orthogonally adjacent white stone.
- **Multi-jumps** are restricted to a single straight-line direction (no
  turning), per standard Kōnane, and may be stopped after any leg.
