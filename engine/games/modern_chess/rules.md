# Modern Chess (Ajedrez Moderno)

Gabriel Vicente Maura's enlarged chess (Puerto Rico, **1968**), played on a
**9×9 board** (9 files *a..i*, 9 ranks) with one extra compound piece and a ninth
pawn per side.

## Objective
Checkmate the opponent's king.

## Board & setup (9×9)
Back rank (files **a..i**), the same for both colours:

```
R N B M K Q B N R
```

- Rooks in the corners (**a**, **i**), then Knights, then Bishops — exactly as in
  orthodox chess on the three left and three right files.
- **King on the centre file e** (e1 for White, e9 for Black).
- **Queen on f** (to the *right* of the King).
- **Prime Minister (M) on d** (to the *left* of the King).
- **Nine pawns** on the **2nd** rank (White) and the **8th** rank (Black).

## The new piece
- **Prime Minister (M)** — also called the *Minister* or *princess*: moves as a
  **bishop + knight** (the same compound piece as Capablanca's Archbishop /
  Cardinal). There is exactly **one** per side.

All other pieces move exactly as in standard chess.

## Pawns
Pawns move and capture as in orthodox chess: a single step forward, an optional
**two-square** step from their starting rank, diagonal captures, and **en
passant**. A pawn reaching the far rank **promotes** and may become a
**Queen, Rook, Bishop, Knight, or Prime Minister**.

## Castling
The king starts on the **e-file** (the centre of the 9-wide board). The king
slides **two squares toward either rook**, and that rook jumps to the square the
king crossed:

- **Ministerside (0-M-0):** King **e1 → g1**, Rook **i1 → h1** (Black: e9→g9, i9→h9).
- **Queenside (0-Q-0):** King **e1 → c1**, Rook **a1 → d1** (Black: e9→c9, a9→d9).

(The name "ministerside" follows Maura's notation; it denotes castling toward the
i-file rook even though the Prime Minister itself sits on the queen's side of the
board.) The usual conditions apply: neither the king nor the chosen rook may have
moved, all squares between them must be empty, and the king may not be in check,
pass through an attacked square, or land on one. In the click-to-move UI, castling
is entered as the king's two-square move (e.g. `4,0>6,0`); the rook follows
automatically.

## Winning & draws
**Checkmate wins.** **Stalemate is a draw.** The game is also drawn by the
fifty-move rule, threefold repetition, and insufficient mating material. A hard
ply cap guarantees termination.

## Notes & interpretations
- The Prime Minister is treated as major (mating) material.
- **Source / ambiguity:** the back-rank arrangement, the King's centre-file start,
  the bishop+knight move of the Prime Minister, the two-square castling, and
  promotion to any of Q/R/B/N/M are all taken from the published descriptions
  (Wikipedia "Modern chess", The Chess Variant Pages). Maura also proposed an
  *optional* "bishop adjustment" rule (a never-moved bishop may swap with an
  adjacent never-moved piece, counting as a move) to escape the single-colour
  bishop problem on the 9×9 board; **that optional rule is NOT implemented here** —
  this package uses the base ruleset only.

Official source: <https://en.wikipedia.org/wiki/Modern_chess>
