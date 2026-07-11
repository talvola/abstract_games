# Shogun Chess

A chess/shogi hybrid by **Couch Tomato** (2019–2020), played on
[pychess.org](https://www.pychess.org/variants/shogun). Standard 8×8 chess plus
shogi-style promotion and crazyhouse-style drops. These rules match the
Fairy-Stockfish `shogun` variant definition, our differential oracle.

## Setup and basic play

- The starting position is exactly the chess array. White moves first.
- All western chess rules apply: castling, pawn double step, en passant,
  check, and **checkmate wins**. Stalemate is a draw.
- The queen is special: she *starts as a promoted piece* — her unpromoted
  form is the **Duchess (F)**, which moves one square diagonally.

## Promotion (shogi-style)

- The **promotion zone** is the three ranks farthest from you (rows 6–8 from
  your side).
- A piece **may promote on any move that starts or ends in the zone**
  (moving in, out, or within it). Promotion is optional — pick the `=X`
  version of the move — except a pawn reaching the last rank **must**
  promote (it could never move again).
- The promotion map:
  1. **Pawn → Captain (C)** — moves like a king (non-royal).
  2. **Knight → General (G)** — knight + king moves.
  3. **Bishop → Archbishop (A)** — bishop + knight moves.
  4. **Rook → Mortar (M)** — rook + knight moves.
  5. **Duchess (F) → Queen (Q)**.
- **Only one of each major piece (Q, M, A, G) per side may be on the board
  at a time** — e.g. a bishop cannot promote while you already have an
  archbishop. Captains are unlimited. Since you start with a queen, your
  duchess can only promote after your queen has been captured.
- A pawn capturing **en passant may not promote** on that move.
- The king and queen never promote; promoted pieces do not promote further.

## Captures and drops (crazyhouse-style)

- Every piece you capture goes into your **hand**, switched to your colour
  and **demoted to its base form**: Q→F, M→R, A→B, G→N, C→P. (This is the
  only way a queen becomes a duchess.)
- Instead of moving, you may **drop** a piece from your hand onto any empty
  square **within your first five ranks** (i.e. anywhere outside the
  promotion zone).
- Unlike crazyhouse, **pawns may be dropped on your first rank**. There is
  no doubled-pawn restriction and no drop-mate restriction (a drop —
  even a pawn drop — may give mate).
- A pawn dropped on the first rank moves one step at a time until it
  reaches the second rank, from which the normal double step is available.
- A dropped rook cannot castle (castling rights are tied to the original
  rooks' home squares).

## Draws

- Stalemate, threefold repetition, or fifty moves without a capture or
  pawn move (any drop or promotion also resets the counter, as in
  Fairy-Stockfish).
- A hard cap of 600 plies ends an endless game as a draw (engine backstop).

## Notation in this app

- Moves are clicks; promotions show a piece picker (`=C`, `=G`, `=A`, `=M`,
  `=Q`). Your hand is the reserve tray above/below the board — click a
  piece, then a highlighted square, to drop (`L@square`).
