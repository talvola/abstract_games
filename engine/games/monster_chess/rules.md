# Monster Chess

**Monster Chess** is an asymmetric chess variant. **White** has only a **King and
four pawns**, but plays **two moves every turn**; **Black** has the **full standard
army** and plays **one move per turn**. The game is decided by **capturing the
enemy king**.

## Setup

- **White:** King on **e1**, pawns on **c2, d2, e2, f2**.
- **Black:** the complete standard chess army (back rank R N B Q K B N R on rank 8,
  eight pawns on rank 7).
- **White moves first.**

## Moving

- **White makes two moves per turn.** The two moves may be with the same piece
  (move it twice) or with two different pieces. White's turn only ends after the
  second move; then Black replies.
- **Black makes one move per turn**, exactly as in ordinary chess.
- Pawns move and capture as in standard chess, including the initial two-square
  advance and **en passant**. A pawn reaching the far rank **promotes** to Q, R, B
  or N. (En passant created by White's *first* move is not available to White's own
  *second* move, and, being a full turn old by the time Black replies, is not
  available to Black either; en passant created by White's *second* move is
  available to Black's immediate reply.)

## Winning: capture the king

There is **no abstract checkmate**. A side wins the moment it **captures the
opponent's king**:

- **White wins** by capturing the Black king (which White may do across its two
  moves).
- **Black wins** by capturing the White king.

### King safety (the important, asymmetric part)

Because Black only replies *after* White's whole two-move turn, "safe" means
different things for the two sides:

- **White's king may move through — or into — an attacked square.** White may put
  its king on an attacked square with the first move and step it away (or remove
  the attacker) with the second. White's moves are therefore unrestricted: White
  may even sacrifice freely, because grabbing the Black king ends the game at once.
- **Black may never leave its king where White could capture it within White's
  next two moves.** After a legal Black move, White must *not* have any one-move or
  two-move sequence that lands on the Black king. (A Black move that itself captures
  the White king is always allowed — it wins immediately.)

This makes "checkmate" implicit: **Black is lost exactly when every move it could
make would leave its king capturable by White in two moves** (and it cannot capture
the White king). Queening a White pawn usually lets White force this quickly.

## Draws and termination

- **Fifty-move rule** (100 half-moves without a pawn move or capture) → draw.
- **Threefold repetition** of the position (same board, side to move, and
  White's remaining-move count) → draw.
- A hard ply cap is enforced as a safety net so play always terminates.

## Interpretations / deviations from some sources

- **Win is modelled literally as king capture** (an event stored in the game
  state), which is equivalent to the usual "checkmate" phrasing: Black is
  checkmated precisely when it cannot keep its king out of White's two-move reach.
- **Castling is omitted for both sides.** White has no rook, and Black castling
  under the redefined two-move "check" rule is left out for simplicity.
- Some sources offer variants where White starts with **all eight pawns** or with
  **only two**; this package implements the standard **four-pawn** setup.

See the official source linked from the Rules dialog for background.
