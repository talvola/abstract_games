# 3D XYZ Chess

Rick Hewson's three-dimensional chess (developed 1988–2016; successor of his
*Exchequer*). Rules as implemented, from *Abstract Games* issue 24 (Winter
2022), pp. 30–34.

## Board and setup

A **4×4×4 cube** of 64 spaces, shown as four 4×4 levels side by side:
**A (leftmost, top of the cube) … D (rightmost, bottom)**. Within a level,
columns **a–d** run left to right and rows **1–4** bottom to top, so a cell is
named like `c2B`. White's home corner is **a1**, Black's is **d4** — the
players face each other from opposite *vertical* corners.

Each army is a standard 16-piece chess set filling its side's 2×2×4 corner
block. White (Black mirrors every piece at the same level, `a↔d`, `1↔4`):

- **Level A:** N a1A, R b1A, P a2A, P b2A
- **Level B:** K a1B, P b1B, B a2B, P b2B
- **Level C:** Q a1C, N b1C, P a2C, P b2C
- **Level D:** B a1D, P b1D, R a2D, P b2D

## Moves

White moves first. Capture is by replacement. No castling, no en passant.

- **Rook** — slides orthogonally: one coordinate changes (6 directions,
  including straight up/down between levels).
- **Bishop** — slides along *planar* diagonals: exactly two coordinates
  change together (12 directions — the regular chess diagonal taken in a
  horizontal **or vertical** plane). No space-diagonal.
- **Queen** — Rook + Bishop (18 directions). No space-diagonal.
- **King** — **one step orthogonally only** (up to 6 cells; deliberately no
  diagonal step, to keep mating nets possible in 3D).
- **Knight** — **one step "triagonally"**: all three coordinates change by
  one (up to 8 cells; it must change level). Each knight is confined to a
  16-cell quarter of the board; the four knights' quarters are disjoint and
  cover the whole cube, so opposing knights can never capture each other.
- **Pawn** — **can never change level.** It moves **one step orthogonally on
  its level towards its opposite corner** — White pawns toward `d4`, i.e.
  `+column` or `+row`; Black toward `a1` — and **captures exactly the same
  way it moves**.
  - **Edge pawns' initial two-space move:** a pawn still standing on one of
    its side's four *edge* starting squares (White `a2A, b1B, a2C, b1D`;
    Black `d3A, c4B, d3C, c4D` — the starting pawns on the outer ring of
    their level) may instead move **two spaces** in either of its directions,
    provided the first space is empty. Like every pawn move it may capture on
    the destination (the magazine's annotated game plays three such
    double-step captures). The central `b2`/`c3` pawns have no double move.
  - **Promotion:** on reaching the opposite corner **of its own level**
    (`d4` for White, `a1` for Black) a pawn promotes to a **Queen**.

## End of the game

- **Checkmate wins.** You may never move into or stay in check.
- **Stalemate is a draw** (explicit magazine rule).
- Draw conventions for termination (the article is silent): threefold
  repetition, 50 full moves without a capture or pawn move, or a 400-ply cap.

## Notation mapping

The magazine writes moves like `Nb1CxPc2B` (column a–d, row 1–4, level A=top
… D=bottom). This implementation's cell id is `"level,col,row"` with each
0-based and level 0 = A, so `c2B` = `1,2,1` and a move is
`from>to` (e.g. `2,0,1>2,0,3` = `Pa2C-a4C`). The move log shows magazine
notation. Implementation-verified anchor: the full 22-move Hewson–Mandoshkin
game (AG24) replays move for move, with every printed check and the final
mate reproduced.

## Interpretations (documented)

- *"Edge of the board"* for the double move is read as the outer ring of the
  pawn's level (one edge pawn per level per side, matching the magazine's
  diagram); the interior `b2`-type pawns get none.
- The double-step may capture: forced by the anchor game (e.g.
  `9.Pb1BxBd1B`), and its guard of a square is what makes the game's final
  position mate.
- Promotion is to Queen only, and automatic ("the Pawn promotes to a Queen").
