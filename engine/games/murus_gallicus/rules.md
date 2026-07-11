# Murus Gallicus

Phil Leduc's 2009 two-player breakthrough game, named after the stone-and-timber
siege walls of Caesar's Gallic Wars. Rules as implemented here follow the
official nestorgames rulebook (rules © 2009 Phillip Leduc).

## Board and setup

- 8×7 board (8 columns, 7 rows).
- Each player has 16 stones, stacked as **eight towers of two stones** on their
  **home row** (the row nearest them). **Romans** (player 1, bottom) move first;
  the **Gauls** (player 2) own the top row.

## Pieces

- A **tower** is two stacked stones of one colour. Only towers act.
- A **wall** is a single stone. **Walls never move** — they block the opponent
  and can be built back into towers.
- The stacking limit is two; opposing stones never share a cell.

## On your turn (you must act — no passing)

Do exactly one of:

1. **Move a tower** — distribute its two stones onto the **two nearest cells in
   any one straight-line direction** (orthogonal or diagonal): one stone on the
   near cell, one on the far cell. **Each destination must be empty or hold a
   friendly wall** (the stone builds the wall into a tower). A friendly tower or
   any enemy stone on either cell blocks that direction; both cells must be on
   the board.
2. **Sacrifice** — remove one stone from a tower (it becomes a wall) to
   **demolish an adjacent enemy wall** (orthogonal or diagonal). Both stones
   leave the board. Enemy **towers cannot be sacrificed against**, and
   sacrificing is never forced.

## Winning

- **Reach the opponent's home row** with any of your stones, or
- **Stalemate the opponent**: if a player cannot move or sacrifice at the start
  of their turn, they **lose**.

## Draws (implementation backstops)

The published rules have no draw. As a safeguard against endless shuffling,
this implementation scores an honest **draw** on threefold repetition of a
position (same stones, same player to move) or at a hard cap of 500 plies.

## Notes

- Move entry: click a tower, then either the **far cell** of a distribution
  (two steps away — the near cell automatically gets the other stone) or an
  **adjacent enemy wall** to sacrifice against it.
- A later "advanced"/**Murus Gallicus MW** variant (Zillions id 3193) adds
  three-stone **catapults**; this package implements the base game only.
