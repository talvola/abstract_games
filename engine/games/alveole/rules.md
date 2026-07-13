# Alvéole

*Alvéole* ("honeycomb") is **Lines of Action played on a hexagonal board** — a
two-player game of movement and connection by Cédric Leclinche, published on
Board Game Arena. These rules describe the game **as implemented here**, matched
against the author's open-source reference implementation
(github.com/devoreve/alveole).

## Board & setup

- A **hexhex** board of **5 cells per side** — **61 hexagonal cells**.
- Each player has **9 pieces** (Red = player 1, moves first; Blue = player 2),
  placed on the **perimeter** of the board. Each side holds **3 alternating
  corners** of the hexagon plus **6 more edge cells**, arranged symmetrically.
- Cells use axial coordinates `q,r`. The exact opening layout (extracted from the
  reference and mapped from its doubled coordinates to axial):
  - **Red:** `(-4,1) (-4,4) (-3,-1) (-1,4) (0,-4) (1,3) (3,-4) (4,-3) (4,0)`
  - **Blue:** `(-4,0) (-4,3) (-3,4) (-1,-3) (0,4) (1,-4) (3,1) (4,-4) (4,-1)`

## Movement

On your turn you **must move one of your pieces**. A hex board has three line
axes (six directions). To move a piece in a given direction:

1. Look at the **whole line** through that piece along that axis — the cells in
   both directions, not just ahead.
2. Count **every piece on that line, of either colour, including the piece
   itself.** Call that count *N*.
3. The piece moves **exactly *N* cells** in the chosen direction.

Movement constraints:

- You **may jump over your own pieces** in the path.
- You **may not jump over an enemy piece** — an enemy anywhere strictly between
  the piece and its destination blocks the move.
- You **may not land on your own piece.**
- If you **land on an enemy piece, you capture it** (it is removed from the
  board).
- The destination must be on the board (moves that would leave the board are
  simply not available in that direction).

## Winning

The board is checked after every move. A group is a set of your pieces connected
by hex adjacency (6 neighbours). You win by gathering **all of your surviving
pieces into a single connected group** (a lone piece counts as connected).

- **If your move connects your pieces, you win** — even if the same move also
  connects the opponent. Simultaneous connection is a **win for the mover**.
- Because connection is checked for both sides, a **capture that leaves the
  OPPONENT in a single connected group makes the OPPONENT win** — including
  reducing them to a single piece. Capturing recklessly can lose you the game.
- If the **player to move has no legal move**, they **lose**.
- A hard **ply cap (300)** declares an honest **draw**, guaranteeing termination
  under random play. (Real games end long before this.)

## Move notation

A move is the string `q,r>q,r` — the piece's cell, `>`, and its destination. In
the move log a capture is shown with `x` (e.g. `0,0x0,2`), a quiet move with `-`.

## How this differs from **Lines of Action** (`lines_of_action`)

Alvéole is a genuine hexagonal reworking of Lines of Action, not a reskin:

| | Lines of Action | Alvéole |
|---|---|---|
| Board | 8×8 square, 64 cells | hexhex, 5/side, 61 cells |
| Axes / directions | 4 axes / 8 directions (orthogonal + diagonal) | 3 axes / 6 directions (hex) |
| Connectivity | 8-connectivity (king-move) | 6-connectivity (hex neighbours) |
| Pieces / player | 12 (two full edges) | 9 (3 alternating corners + 6 edge cells) |
| Simultaneous connection | draw by default (option for mover-win) | **always a win for the mover** |

The core Lines-of-Action engine is identical in spirit — move a line-count
distance, jump friends, capture on landing, win by uniting your group — but the
hexagonal topology changes every geometric detail, and Alvéole fixes the
simultaneous-connection tie as a mover win.
