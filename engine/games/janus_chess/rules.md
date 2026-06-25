# Janus Chess

**Janus-Schach**, invented by **Werner Schöndorf** (Bildstock, Germany, 1978),
played on a **10×8 board** (10 files *a..j*, 8 ranks). The variant is named after
the two-faced Roman god Janus, reflecting the new piece's dual (bishop + knight)
nature.

## Objective
Checkmate the opponent's king.

## Board & setup (10×8)
Back rank (files **a..j**), the same for both colours:

```
R J N B K Q B N J R
```

- Rooks in the corners (**a**, **j**).
- A **Janus (J)** flanks each knight, on the **b** and **i** files (two per side).
- **King on e**, **Queen on f** — *reversed* from orthodox chess (where the queen
  is on the d-file). This is the historical Janus setup.
- Pawns on the **2nd** rank (White) and **7th** rank (Black) — ten per side.

## The Janus
- **Janus (J)** moves as a **bishop + knight** (the compound also known as the
  *Archbishop* or *Cardinal*): it slides any distance along diagonals **and** can
  jump as a knight. It is worth roughly a rook + a minor — nearly as strong as a
  queen.

All other pieces (R, N, B, Q, K) and the pawns move exactly as in standard chess.

## Pawns
Pawns move and capture as in orthodox chess: a single step forward, an optional
**two-square** step from their starting rank, diagonal captures, and **en
passant**. A pawn reaching the far rank **promotes** and may become a
**Queen, Rook, Bishop, Knight, or Janus**.

## Castling
The king starts on the **e-file** and the rooks in the corners (**a**, **j**), so
on the wide board castling is **asymmetric** — the king ends on the b- or i-file
and the rook on the adjacent c- or h-file:

- **Queenside (O-O-O):** King **e1 → b1** (three squares), Rook **a1 → c1**
  (Black: e8→b8, a8→c8).
- **Kingside (O-O):** King **e1 → i1** (four squares), Rook **j1 → h1**
  (Black: e8→i8, j8→h8).

The usual conditions apply: neither the king nor the chosen rook may have moved,
all squares between them must be empty, and the king may not be in check, pass
through an attacked square, or land on one. In the click-to-move UI, castling is
entered as the king's multi-square move (e.g. `4,0>8,0` for kingside); the rook
follows automatically.

## Winning & draws
**Checkmate wins.** **Stalemate is a draw.** The game is also drawn by the
fifty-move rule, threefold repetition, and insufficient mating material. A hard
ply cap (`PLY_CAP`) guarantees termination.

## Notes
- The Janus is treated as major (mating) material.
- Letter legend: **R** rook, **N** knight, **B** bishop, **Q** queen, **K** king,
  **J** Janus (bishop + knight), **P** pawn.
- Source of the rules as implemented (setup, the King/Queen file swap, the
  asymmetric e→b / e→i castling, promotion to J): the Wikipedia "Janus Chess"
  article and the chessvariants.com Janus page.

Official source: <https://en.wikipedia.org/wiki/Janus_Chess>
