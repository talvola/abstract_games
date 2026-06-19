# Pente

Five-in-a-row with **custodial pair captures** (Gary Gabrel, 1977), on a square
grid (**13×13**, **15×15**, or **19×19** via the board-size option). Player 0 is
**Black** and moves first; player 1 is **White**.

## How to play

- On your turn, place one stone on any **empty** cell.
- **Capturing a pair:** if your placed stone forms the pattern
  **you – enemy – enemy – you** in a straight line (orthogonal or diagonal), the
  two bracketed enemy stones are **removed** and count as one captured pair.
  - Only an **exact pair** is taken — never a single stone, and never three or
    more in a row.
  - Capture is **active**: it is safe to place your *own* two stones between two
    enemy stones; nothing is captured unless the bracketing stone is just placed.

## Winning

You win by either:

- forming an unbroken line of **five or more** of your stones (any direction), or
- capturing **five pairs** (ten enemy stones).

The captured-pair tally (Black–White) is shown in the caption.

## Notes

- This implementation uses **free placement** (no first-move centre restriction).
  Overlines (six or more) also win. A full board, or a hard ply cap on a rare
  capture-cycle, draws.
