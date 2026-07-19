# Chigorin Chess

Ralph Betza, 2002 (chessvariants.com). A chess variant with **unequal armies**
on the standard 8×8 board, named for Mikhail Chigorin's supposed preference
for Knights over Bishops: a Knights army faces a Bishops army.

## Setup

- **White** (moves first): Rooks a1/h1, **four Knights** b1/c1/f1/g1, a
  **Chancellor** on d1, King e1, and eight Pawns on the second rank.
- **Black**: Rooks a8/h8, **four Bishops** b8/c8/f8/g8, an orthodox **Queen**
  on d8, King e8, and eight Pawns on the seventh rank.

White has no Bishops or Queen; Black has no Knights.

## Pieces

All pieces move as in orthodox chess. The one fairy piece is the
**Chancellor (C)**: it moves as **Rook + Knight** combined.

## Rules

All the standard FIDE rules apply:

- **Castling** on either wing for both sides (normal king-two-squares rules).
- **Pawns** move/capture as usual, with the initial double step and
  **en passant**.
- **Promotion** (mandatory on the last rank) is to a piece of the **owner's
  own army**: White promotes to **Chancellor, Rook or Knight**; Black promotes
  to **Queen, Rook or Bishop**. (Betza offers two readings of the FIDE
  promotion rule and states he prefers this own-army rule for this game; it is
  also exactly the Fairy-Stockfish `chigorin` ruleset this package is anchored
  to.)
- **Win** by checkmate; stalemate is a draw.
- **Draws**: fifty-move rule, threefold repetition, insufficient material,
  plus a 600-ply safety cap.

## Implementation notes

Verified move-for-move against Fairy-Stockfish's built-in `chigorin` variant
via pyffish: perft(1..4) from the opening position (26 / 416 / 11,408 /
229,973) plus promotion- and castling-position perfts, and 7,135 random-game
positions with identical full legal-move sets (`_diff_pyffish.py`).

## Sources

- Ralph Betza, [Chigorin Chess](https://www.chessvariants.com/diffsetup.dir/chigorin.html), chessvariants.com, 2002 (setup, own-army promotion, "other than that, the standard rules of FIDE Chess are used").
- Fairy-Stockfish built-in variant `chigorin` (identical ruleset; the differential anchor).
- John Vehre, "Chigorin Chess", *Abstract Games* issue 24 (Winter 2022), pp. 22–27 (history, strategy notes, and an annotated game; confirms both sides castle and the Chancellor is the only fairy piece).
