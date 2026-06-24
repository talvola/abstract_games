# Cylinder Chess

Standard chess on a board that is a **vertical cylinder**: the a-file and the
h-file are joined, so pieces can slide or leap off one side edge and reappear on
the other. Everything else is ordinary FIDE chess.

## Objective
Checkmate the opponent's king.

## Board & setup
The usual 8×8 array (pawns on the second rank, R N B Q K B N R behind them).
White is player 1 and moves first; Black is player 2. The **left and right edges
are connected** — file h is adjacent to file a. The top and bottom edges (the
1st and 8th ranks) are **not** connected: ranks do not wrap.

## Play
Pieces move exactly as in standard chess, but the file coordinate wraps modulo 8
while the rank stays on the board:

- A **rook** or **queen** moving along a rank can run off the a-file and continue
  from the h-file (and vice versa). On an otherwise empty rank a rook reaches each
  of the other seven files once.
- A **bishop** or **queen** wraps along its diagonals: a bishop leaving the a-file
  reappears on the h-file one rank up/down, continuing the diagonal.
- A **knight**'s file offset wraps, so a knight on the a-file can leap to the
  h-file.
- A **pawn** advances straight (never wrapping); its diagonal captures wrap, so an
  a-file pawn can capture a piece on the h-file one rank ahead, and vice versa.
- Pieces still **cannot pass through** an occupied square — wrapping never bypasses
  a blocker, and a slider stops at (and may capture) the first piece it meets.
- A sliding ray visits each square at most once and can never loop all the way
  around the board back onto its own square, so a rook does not attack or block
  itself through the wrap.

Because attacks use the same wrapped geometry, **a rook or bishop can give check
around the cylinder**, and the king may not castle through or into a square that
is attacked via the wrap.

The usual special rules all apply:
- **Castling**, king- and queen-side. This implementation uses **standard
  castling only** (the king's two-square move e1→g1 / e1→c1, rook follows). Some
  cylinder-chess descriptions note the king could in principle "castle the other
  way around the board," but the common ruleset (chessvariants.com) keeps ordinary
  castling, which is what we implement.
- **En passant** capture (the en-passant square also wraps with the capturing
  pawn's diagonal).
- **Pawn double-step** from the starting rank and **promotion** to Q/R/B/N on the
  last rank.

## Winning & draws
- **Checkmate** wins. **Stalemate** is a draw.
- Also drawn by the **fifty-move rule**, **threefold repetition**, and
  **insufficient material**.

## In this implementation
- Castling is entered as the king's two-square move; the rook follows
  automatically. Promotion shows a Q/R/B/N picker.
- The opening move count is the same 20 as standard chess (in the starting array
  the back rank is full, so nothing actually wraps onto a new square yet); the
  wrap changes the game as soon as files open up.
