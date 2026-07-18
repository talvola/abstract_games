# Crazy 38's

A chess/shogi hybrid by **Ben Good (1998)**, created as an entry in Hans
Bodlaender's "38 square challenge" and now a Recognized Chess Variant on
chessvariants.com. It is played on a knotted **38-square** board, *with drops*.

This page documents the rules **as implemented**. The official rules are linked
from the "official source" button.

## The board

The board is a Celtic-knot arrangement of 38 diamond cells. Rows are lettered
**a-h** down one side and numbered **1-8** up the other; each square is a
`letter+number` pair, and **only 38 of the 64 combinations exist**:

```
a: a3 a5 a6 a8
b: b5 b6
c: c1 c3 c4 c5 c6 c7 c8
d: d3 d4 d5 d6 d7 d8
e: e1 e2 e3 e4 e5 e6
f: f1 f2 f3 f4 f5 f6 f8
g: g3 g4
h: h1 h3 h4 h6
```

The six **tip** cells (a8, a3, f8, c1, h6, h1) are the curved cells that turn the
corners of the knot. Each bridges a one-square gap, so for example **a6 and a8
are orthogonally adjacent** even though a7 is not a square. This gives the board
its **loop-effect**: files and ranks are long curved lines, and a Rook slides
straight through the bridged gaps. Otherwise all pieces move by ordinary chess
geometry — *orthogonal* = along a file (same letter) or rank (same number),
*diagonal* = one step in both.

`King on h1` (White) and `King on a8` (Black) mark each player's **Home Square**.

## The pieces

Each side has: 4 **Pawns**, 1 **Silver General**, 1 **Gold General**,
1 **Knight**, 1 **Bishop**, 1 **Rook**, 1 **King**.

- **Pawn (P)** — moves one square in *either* orthogonal direction that heads
  away from its own side (two possible forward squares). It captures the same
  way it moves. Reaching the **opponent's Home Square** promotes it to a
  **Queen** (Rook + Bishop). A captured Queen is demoted to a Pawn before it can
  be dropped again.
- **Silver General (S)** — steps to any adjacent square **except the squares
  diagonally straight-ahead and straight-behind** (4 orthogonal + 2 side
  diagonals). *Not* the shogi silver.
- **Gold General (G)** — steps to any adjacent square **except the two side
  diagonals** (4 orthogonal + the ahead/behind diagonals). *Not* the shogi gold.
- **Knight (N)** — "one square diagonally, then one square orthogonally away."
  Unblockable. Because the board is a **knot**, this L-shaped leap follows the
  board's *curved* files and ranks, so near the six tip cells it is **not** the
  flat chess leap: e.g. a Knight on a8 reaches b5, c6, d7, and a Knight on f3
  reaches d4, e1, e5, h4 **and h1** (an over-the-tip leap). Deep in the interior,
  where no tip is within reach, it is exactly the ordinary chess knight. The
  target set for each of the 38 squares is derived from the geometry (two steps
  along one curved line plus one along the crossing line, in every interleaving)
  and is symmetric.
- **Bishop (B)** — slides any distance diagonally. It **may also make a single
  non-capturing step to an orthogonally-adjacent empty square, but only while it
  is orthogonally adjacent to a friendly piece** (this lets it switch square
  colours with support).
- **Rook (R)** — slides any distance orthogonally along a rank or file, following
  the board's curves through tip-bridged gaps.
- **King (K)** — steps to any adjacent square; may not move into check (except
  the winning move below).

## Drops

Like shogi, a captured piece changes ownership and enters the capturing player's
**reserve**; on your turn you may instead **drop** a reserved piece onto any
empty square (unpromoted). Restrictions:

- A Pawn may **not** be dropped onto the opponent's Home Square.
- A Pawn may **not** be dropped so that it **immediately checkmates** the
  opponent's King.

(There is no two-pawns-per-file restriction.)

## Object of the game

Win by **checkmating** the opponent's King, **or** by moving your **own King onto
the opponent's Home Square**. The king-to-home move wins immediately if it is a
legal king step onto that square.

## Draws & termination

- **Stalemate** (no legal move while not in check) is a draw.
- **Four-fold repetition** of the position is a draw.
- A hard move-cap (300 plies) is a draw, to guarantee the game ends despite the
  material recycling that drops allow.

## Documented interpretations

The 1998 rules are terse (the author noted the game was unplaytested), so a few
points are resolved here:

- **Sliding through the loop.** A Rook (and the Queen's rook component) slides
  along a rank/file through the tip-bridged gaps and stops at the end of that
  line; it does not turn the corner within a single move. This is the natural
  reading of "moves orthogonally" and gives the intended loop-effect.
- **Bishop's quiet step** requires an *orthogonally* adjacent friendly piece and
  goes to an *orthogonally* adjacent empty square (never a capture).
- **King-to-home win** is allowed as a king step onto the enemy Home Square even
  out of/into attack, since reaching the goal ends the game at once (the enemy
  King, if still on its Home Square, of course blocks it).
- **Repetition** is scored as an honest draw (no perpetual-check loss rule).
