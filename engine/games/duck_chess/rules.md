# Duck Chess

Tim Paulden, 2016. Standard chess plus a shared rubber duck that both players
move. Rules as implemented here, following the designer's rules
([duckchess.com](https://duckchess.com)) and Fairy-Stockfish's `duck` variant.

## The turn

Every turn has **two parts**, both by the same player:

1. **A normal chess move** (standard 8×8 board and starting position).
2. **Move the duck** to any *empty* square **different** from where it stands.
   Moving the duck is mandatory — it may not stay put. The duck starts off the
   board; after White's first chess move it may be placed on any empty square.

## The duck

- The duck belongs to no one and can never be captured.
- **No piece may land on or slide through the duck's square.** Knights jump
  over it as they jump over anything (but may not land on it).
- Pawns are blocked by it (a duck directly ahead stops the pawn; a duck on
  either square of a double step blocks the double step; a duck on the
  en-passant square makes that capture impossible).

## No check — win by capturing the king

- There is **no check, checkmate or "illegal because of check"**: a king may
  move to an attacked square, and you are never forced to answer a threat.
- **You win by actually capturing the enemy king.** The game ends immediately
  (no duck move follows the capture).

## Stalemate — "fowling"

If the player to move has **no possible chess move at all** (every piece
completely blocked), that player is *fowled* and **wins immediately**
(designer's rule; Fairy-Stockfish implements the same, `stalemateValue = win`).

## Castling, en passant, promotion

- **Castling:** king and rook unmoved, all squares between them empty (the
  duck counts as an occupant and blocks). Because there is no check, you may
  castle out of, through, or into attacked squares.
- **En passant** and **promotion** (to Q/R/B/N) work as in normal chess,
  subject to the duck's blocking.

## Draws

The designer's rules don't discuss draws; as in orthodox chess we apply:
threefold repetition of the same position (including the duck's square and
whose sub-move it is), 50 chess moves by each side without a capture or pawn
move, and a hard 300-turn cap. All are honest draws.

## Notation

A chess move is played by clicking the piece then its destination; the duck
move is a single click on the target square (shown in the log as `duck→e4`).
