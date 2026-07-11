# Oxono

Tom Delahaye (Cosmoludo, 2024). A double-natured four-in-a-row: every token you
place is steered by two **shared totems**, and lines can be won by **colour**
or by **symbol**.

## Board and material

- 6×6 board. The two central *dot* squares (the diagonal centre cells) hold the
  two shared totems — one marked **X**, one marked **O** — assigned to the two
  dots at random at the start.
- Each player has 16 tokens of their colour: **8 marked X and 8 marked O**.
  Player 1 (red here; pink in the physical game) moves first.
- Remaining tokens are shown in the trays above/below the board.

## Your turn (two clicks)

1. **Move a totem.** Pick the X or the O totem — you may only pick a symbol you
   still have tokens of — and move it like a **rook**: any number of squares
   (at least 1) horizontally or vertically, over **empty squares only**. It may
   not pass over or land on tokens or the other totem.
2. **Place a token.** Put one of your tokens **of the same symbol** as the
   moved totem on a **free square orthogonally adjacent** to the totem's new
   position.

## Surrounded totems (special cases)

- **A — Jump.** If every orthogonal neighbour of a totem is occupied (by tokens
  or the other totem; board edges count as walls), the totem moves by
  **jumping**: in each orthogonal direction it leaps the contiguous occupied
  squares and lands on the **first free square** of that row or column.
  *(Interpretation: the jumped series may include the other totem — the
  rulebook's "fully trapped" case below triggers only when the entire row and
  column are occupied, so any free square in the row is reachable.)*
- **B — Enclosed landing.** If the totem's new square has **no free orthogonal
  neighbour** (only possible after a jump or a case-C flight), place your token
  on **any free square** of the board.
- **C — Fully trapped.** If a surrounded totem's whole row **and** column are
  occupied (no jump landing exists), move it to **any free square** of the
  board, then place your token normally (or per case B if it landed enclosed).

## Winning

Placing a token that completes a **horizontal or vertical** line of **4** (or
more) tokens that are either

- all of **your colour** (symbols mixed freely), or
- all of **one symbol** (colours mixed freely)

wins immediately. **Whoever places the 4th token of a same-symbol line wins
it**, even if the opponent owns more tokens in the line. Diagonals never count,
and the totems never count in a line (they block lines instead).

## Draw

If both players place all 16 of their tokens and no line of 4 exists, the game
is a **draw**.

## Notation

- Totem move: `from>to` (click the totem, then its destination).
- Token placement: a single cell (click it). The move log shows totem moves as
  `X-totem c3-c5` and placements as `Xd5`.

*Source: the official Cosmoludo digital rulebook (linked from BGG), cross-checked
against Board Game Arena's rules summary.*
