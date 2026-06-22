# Crazyhouse

Crazyhouse is chess with one extra idea: **captured pieces are not removed from
the game.** When you capture, the piece changes colour and joins your *reserve*,
and on a later turn you may drop it back onto the board as your own.

These are the rules **as implemented** in this package.

## Standard chess applies

The board, the starting position, and all ordinary chess rules are unchanged:

- Pieces move and capture exactly as in chess.
- **Castling**, **en passant**, and the pawn **double-step** all work normally.
- A pawn reaching the far rank must **promote** to a Queen, Rook, Bishop, or
  Knight.
- You may never make a move that leaves your own king in check. **Checkmate**
  wins; **stalemate** is a draw.

## The reserve and drops

- Every piece you capture is **flipped to your colour** and added to your
  reserve.
- On your turn, instead of moving a piece on the board you may **drop** a piece
  from your reserve onto any **empty** square. A drop counts as your whole move.
- **Pawns may not be dropped on the first or last rank** (ranks 1 and 8). All
  other pieces may be dropped on any empty square.
- A drop is legal as long as it does not leave your own king in check — so a
  drop may **block a check** or even **deliver checkmate** ("a mate in hand").

## Promoted pieces revert

A pawn that promotes is marked as a promoted piece. If that piece is later
captured, it returns to the opponent's reserve as a **pawn**, not as the piece it
had become. (A Queen made by promotion is captured back as a pawn.)

## Draws

Because captured material can always re-enter the board, there is **no draw by
insufficient material**. Draws occur by:

- **Threefold repetition** — the same position (including both reserves and whose
  turn it is) occurring three times.
- **The fifty-move rule** — 100 half-moves with no capture and no pawn move.
  (Drops do not reset this counter.)
- **Stalemate** — the side to move has no legal move *and* no legal drop, and is
  not in check.

A hard ply cap also forces a draw in the rare event a game runs extremely long.

## Notation

A normal move is written as a path, e.g. `e2-e4`; a drop is written `N@c4`
("drop a knight on c4"). In the app you make a drop by clicking a piece in your
reserve tray and then clicking the empty square to place it on.
