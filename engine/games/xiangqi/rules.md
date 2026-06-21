# Xiangqi (Chinese Chess)

A two-player game on a **9-file × 10-rank** board. Player 0 is **Red** (uppercase
pieces, home rows 1–5) and moves first; player 1 is **Black** (lowercase, rows
6–10). Pieces rest on the points of the grid; the **river** runs across the middle
and each side has a 3×3 **palace**.

> Rendering note: the board is drawn as a 9×10 grid of cells with lettered pieces.
> This is functionally identical to the traditional intersection board (same
> adjacency; the palace and river are enforced in the rules). The decorative river
> gap and palace diagonals are not yet drawn — a cosmetic enhancement for later.

## The pieces

| Letter | Piece | Moves |
|---|---|---|
| **G/g** | General | One point orthogonally, **confined to the palace**. |
| **A/a** | Advisor | One point diagonally, **confined to the palace**. |
| **E/e** | Elephant | Exactly two points diagonally; **may not cross the river**; blocked if the midpoint (the "elephant's eye") is occupied. |
| **H/h** | Horse | A knight's move, but **lame**: blocked if the orthogonal point it steps through (the "horse's leg") is occupied. |
| **R/r** | Chariot | Like a rook — any distance orthogonally, no jumping. |
| **C/c** | Cannon | Moves like a rook to an **empty** square; to **capture** it must jump **exactly one** piece (a "screen", of either colour) and land on an enemy beyond it. |
| **S/s** | Soldier | One point **forward**; after crossing the river it may also step **sideways**. Never backward; no promotion. |

## Check, the flying general, and winning

- Your move may not leave **your own general in check**.
- **Flying-general rule:** the two generals may never face each other along an
  **open file** (one with no pieces between them). An enemy general therefore
  "attacks" down an open file like a chariot, so a move exposing this is illegal.
- A player with **no legal move loses** — in Xiangqi both **checkmate** and
  **stalemate** are losses (unlike Western chess, where stalemate is a draw).

## Draws and termination

Real tournament rules make perpetual check or perpetual chase a **loss** for the
offender; that nuance is **simplified here** to a draw by **threefold repetition**.
A game with **120 plies without a capture** also draws, and a hard ply cap bounds
the rare runaway game. (These guarantee the game always terminates.)

## Correctness

The move generator is verified against the published Xiangqi **perft** node counts
from the opening position: 44, 1920, 79666 at depths 1–3.
