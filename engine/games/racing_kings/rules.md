# Racing Kings

A pawnless chess variant invented by **V. R. Parton** in 1961. Both kings race
to the far side of the board; the first king to reach the eighth rank wins.

## Board and pieces

- Standard 8x8 board, standard pieces, **no pawns**.
- Each side has a King, Queen, two Rooks, two Bishops and two Knights, all set up
  on the first two ranks. White starts on the right (king's) half, Black on the
  left (queen's) half. Both players view the board from the same side.
- Starting position (FEN): `8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1`.
- White (the lighter pieces, player 0) moves first.

## How pieces move

King, Queen, Rook, Bishop and Knight move **exactly as in orthodox chess**.
There are **no pawns**, and therefore no pawn moves, no promotion and no
en passant. There is **no castling**.

## Check is forbidden

This is the defining rule. Checks are *entirely* forbidden:

- You may not move your own king into check (as in normal chess), **and**
- You may not make any move that gives check to the opponent's king.

A move that would do either is simply illegal and is never offered. As a
consequence kings are never actually in check during play, and there is no such
thing as checkmate.

## Winning

- The goal is to get **your king onto the eighth rank** (the row farthest from
  White's start; row 7 internally). The first player to do so wins.
- **The compensation rule:** because White moves first, if **White** moves their
  king to the eighth rank, **Black is given one more move**. If Black can also
  bring their king to the eighth rank on that immediate reply, both kings are
  home and the game is a **draw**. If Black cannot, White wins.
- When **Black** moves their king to the eighth rank, Black wins immediately
  (White has already had the move that would have mattered).
- If both kings end up on the eighth rank, it is a draw.

## Draws

- White reaches the eighth rank and Black matches it on the very next move (the
  rule above) — draw.
- **Stalemate**: a player to move with no legal move draws. (Since no move may
  give or expose a check, there is no checkmate; a player simply stuck without a
  legal move ends the game as a draw.)
- **Threefold repetition** of the same position (same pieces, same player to
  move) — draw.
- A hard ply cap (600 plies) also forces a draw, purely as a safety net so the
  game always terminates; in practice the race ends long before this.

## Implementation notes / ruleset choices

This package implements the rules as used by lichess, python-chess and
Fairy-Stockfish:

- The starting position is the standard
  `8/8/8/8/8/8/krbnNBRK/qrbnNBRQ w - - 0 1`.
- *No* fifty-move or insufficient-material draw is applied: there are no pawns,
  material can legitimately be reduced to bare kings that still race to the
  eighth rank, so those orthodox-chess draw rules do not fit. Termination is
  guaranteed instead by threefold repetition plus the ply cap.
- Correctness is anchored to the **published Racing Kings opening perft**
  (move-generation node counts): from the start, 21 / 421 / 11264 / 296242
  positions exist at depths 1 / 2 / 3 / 4. These figures (which already account
  for the no-check rule) match shakmaty's `racingkings.perft` test data and the
  Fairy-Stockfish test suite, and are checked by this package's `selftest.py`.
