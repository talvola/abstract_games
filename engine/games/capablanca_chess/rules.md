# Capablanca Chess

José Raúl Capablanca's enlarged chess (c. 1920), played on a **10×8 board**
(10 files *a..j*, 8 ranks) with two extra compound pieces.

## Objective
Checkmate the opponent's king.

## Board & setup (10×8)
Back rank (files **a..j**):

```
R N A B Q K B C N R
```

- Rooks in the corners (**a**, **j**).
- **Archbishop (A)** next to the queen's bishop; **Chancellor (C)** next to the
  king's bishop.
- Queen on **e**, King on **f**.
- Pawns on the **2nd** rank (White) and **7th** rank (Black).

## The new pieces
- **Archbishop (A)** — also called the *Cardinal*: moves as a **bishop + knight**.
- **Chancellor (C)** — also called the *Marshall* or *Empress*: moves as a
  **rook + knight**.

All other pieces move exactly as in standard chess.

## Pawns
Pawns move and capture as in orthodox chess: a single step forward, an optional
**two-square** step from their starting rank, diagonal captures, and **en
passant**. A pawn reaching the far rank **promotes** and may become a
**Queen, Rook, Bishop, Knight, Archbishop, or Chancellor**.

## Castling (ruleset choice)
This package uses **Capablanca's own three-square castling**: the king moves
**three squares toward the rook**, and that rook jumps to the square the king
crossed.

- **Kingside (O-O):** King **f1 → i1**, Rook **j1 → h1** (Black: f8→i8, j8→h8).
- **Queenside (O-O-O):** King **f1 → c1**, Rook **a1 → d1** (Black: f8→c8, a8→d8).

The usual conditions apply: neither the king nor the chosen rook may have moved,
all squares between them must be empty, and the king may not be in check, pass
through an attacked square, or land on one. In the click-to-move UI, castling is
entered as the king's three-square move (e.g. `5,0>8,0`); the rook follows
automatically.

## Winning & draws
**Checkmate wins.** **Stalemate is a draw.** The game is also drawn by the
fifty-move rule, threefold repetition, and insufficient mating material. A hard
ply cap (`PLY_CAP`) guarantees termination.

## Notes
- The Archbishop and Chancellor are treated as major (mating) material.
- Several historical variants differ on the exact castling distance and on the
  promotion set; the choices above (three-square castling, promotion to any of
  Q/R/B/N/A/C) are the rules **as implemented here**.

Official source: <https://www.chessvariants.com/large.dir/capablanca.html>
