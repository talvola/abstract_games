# Hexapawn

A tiny two-player pawns game on a **3×3** board, invented by **Martin Gardner**
(*Scientific American*, March 1962) to illustrate a machine that learns to play
by trial and error (his matchbox "HER" / HEXAPAWN machine).

Player 0 is **White** (three pawns start on the bottom rank, row 1, and advance
upward); player 1 is **Black** (three pawns on the top rank, row 3, advancing
downward). The middle rank starts empty. Every pawn is identical.

## Moving

Pawns move exactly like chess pawns, with **no** double-step, **no** en passant
and **no** promotion. On your turn, move one pawn one square **forward**:

- **straight ahead** — only onto an **empty** square;
- **diagonally forward** — **only to capture** an enemy pawn standing on that
  square (a diagonal move onto an empty square is *not* allowed).

You may never move sideways or backward.

## Winning

You **win** if either:

1. one of your pawns reaches the **far rank** (row 3 for White, row 1 for
   Black); **or**
2. it becomes your opponent's turn and they have **no legal move** — the side to
   move with no move **loses**.

There are **no draws** in Hexapawn.

## Notes

- Because every move pushes a pawn one row forward (and captures also remove a
  pawn), play always makes progress — Hexapawn cannot cycle. A pure-safety ply
  cap exists in the implementation but is unreachable in real play.
- **Game-theoretic result:** with perfect play the **second player (Black)
  wins**. This package's selftest verifies that by exact minimax.
- Move notation is a clickable `from>to` cell path, e.g. `0,0>0,1` (a push) or
  `0,0>1,1` (a diagonal capture).
