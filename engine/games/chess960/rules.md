# Chess960 (Fischer Random Chess)

Ordinary chess on an 8×8 board, but the pieces on the back rank start in a
**randomized order** — one of the 960 legal Chess960 positions. Invented by Bobby
Fischer (1996) to reduce the role of memorized opening theory.

## Objective
Checkmate the opponent's king, exactly as in standard chess.

## Setup
Pawns sit on the second rank as usual. The **back rank** is randomized, subject to
three constraints:

- The two **bishops** stand on squares of **opposite colours**.
- The **king** stands **strictly between the two rooks**.
- **Black mirrors White**: both players use the same arrangement of files (White on
  rank 1, Black on rank 8).

Each of the 960 positions has a number. **Standard chess (R N B Q K B N R) is
position #518.** This implementation picks the back rank at random with the match's
RNG and stores it in the game state, so the position replays deterministically. The
"Starting position" option can force #518 (ordinary chess) for testing.

## Play
All pieces move exactly as in standard chess: king, queen, rook, bishop, knight, and
pawn (single/double step, diagonal capture, **en passant**). A pawn reaching the last
rank **promotes** to Q/R/B/N.

## Castling — by final squares
Castling exists in Chess960 but is generalized: it is defined by the **final**
squares of the king and rook, regardless of where they started.

- **Kingside (O-O):** king ends on **g1/g8**, rook ends on **f1/f8**.
- **Queenside (O-O-O):** king ends on **c1/c8**, rook ends on **d1/d8**.

Conditions (all must hold):

- Neither the king nor that rook has moved.
- Every square between the king's start and end, **and** between the rook's start and
  end, is empty — except for the castling king and rook themselves (so a rook already
  on its target file, or king and rook adjacent, are fine).
- The king does **not** start in, pass through, or land on a square attacked by the
  enemy.

Because a Chess960 king can begin next to its destination, a "king moves two squares"
test is unreliable. So in this implementation a castling move is entered as the
**king moving onto its own rook's square** (the standard FIDE Chess960 "king captures
rook" notation): click the **king**, then click the **rook** you want to castle with.
The king and rook then jump to their final squares.

## Winning & draws
- **Checkmate** wins; **stalemate** is a draw.
- Also drawn by the **fifty-move rule**, **threefold repetition**, and **insufficient
  material** — as in standard chess.

White is player 1 and moves first.
