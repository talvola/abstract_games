# Yoxii

*Jeremy Partinico — Cosmoludo, 2022. Two players. Rules as implemented.*

Encircle the neutral **Totem** so that, when it can no longer move, more points'
worth of **your** pieces surround it than your opponent's.

## Board

The board is a **37-square octagon**: a 7×7 grid with a three-square triangular
notch cut from each of the four corners, giving rows of width **3, 5, 7, 7, 7,
5, 3**. Squares are addressed `col,row` with `col`/`row` from 0 (top-left) to 6.
The removed corner squares are `(0,0) (1,0) (0,1)`, `(5,0) (6,0) (6,1)`,
`(0,5) (0,6) (1,6)`, and `(6,5) (5,6) (6,6)`. The **Totem** starts on the centre
square `(3,3)`.

## Pieces

Each player has **18 pieces** with printed point values:

| Symbol | Value | Count |
|--------|-------|-------|
| O  | 1 | 5 |
| II | 2 | 5 |
| Y  | 3 | 5 |
| X  | 4 | 3 |

Seat 0 = **White**, plays first. Seat 1 = **Red**.

## A turn (two sub-moves by the same player)

**1. Move the Totem.** Either:

- **Step** it one square in any of the **8 directions** (orthogonal or diagonal)
  to a **free** (empty, on-board) square; **or**
- **Jump** it in a straight line over a **continuous run of one or more of YOUR
  OWN pieces** and land on the **first free square just beyond** the run. You may
  **never** jump over an opponent's piece, and the landing square must be free.

**2. Place a piece.** Put **one of your pieces of any value** (from your remaining
stock) on a **free square among the (up to 8) squares directly around** the
Totem's new position. **Special case:** if every square around the Totem is
occupied, place your piece on **any other free square** of the board.

The value you place each turn is your free choice — this is the core of the
strategy.

## End of the game

The game ends when the player to move **can no longer move the Totem** — it is
encircled/immobilised (no free adjacent square **and** no legal jump). Each
player then sums the **values** of **their** pieces on the (up to 8) squares
around the Totem:

- Higher sum **wins**.
- Tie → the player with **more of their pieces** around the Totem wins.
- Still tied → an honest **DRAW**.

Because every turn permanently places one piece on a previously empty square and
there are only 36 non-Totem squares, a game lasts at most 36 turns (72 plies); a
generous ply cap is a defensive backstop.

## Notation

- Totem move: `c1,r1>c2,r2` (the source is always the Totem's square).
- Piece placement: `c,r=V`, where `V` is the value `1`/`2`/`3`/`4`; the web UI
  shows a value picker on the clicked square.
