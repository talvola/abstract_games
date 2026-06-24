# Dots and Boxes

A classic paper-and-pencil game invented by **Édouard Lucas** in 1889 (as *La
Pipopipette*). Rules here are as **implemented** in this package; see the
[Wikipedia article](https://en.wikipedia.org/wiki/Dots_and_Boxes) for the
general game.

## Board

The board is an **m × n grid of boxes**, bounded by **(m+1) × (n+1) dots**. The
default is **5 × 5 boxes** (a 6 × 6 dot lattice, 60 edges, 25 boxes). Other sizes
are available via the **Board size** option (3×3, 4×4, 5×5, 6×6, 5×4).

A *line* (edge) joins two orthogonally-adjacent dots — either **horizontal** or
**vertical**. The total number of edges on an m × n box grid is
`m·(n+1) + n·(m+1)` (e.g. 60 for 5×5).

## Play

Players alternate turns. On your turn you **draw exactly one undrawn line**.

- **Completing a box.** When your line completes the **fourth side** of one (or
  two) boxes, you **claim** each completed box — it is marked with your colour and
  initial — **and you immediately move again.**
- **Chaining / the double line.** A single line can complete **two** boxes at once
  (when it is the last missing side of the boxes on *both* sides of it). You score
  **both** boxes, but you still take exactly **one** extra move — completing boxes
  grants "move again", not "one move per box". On that extra move you may of course
  complete and chain further boxes, each granting another move, and so on.
- **No box completed.** If your line completes no box, your turn **ends** and play
  passes to your opponent.

There is no passing and no other action: every legal move is a single line.

## End and scoring

The game ends when **every line has been drawn** (all boxes are necessarily
claimed). The player who claimed **the most boxes wins**. If both players claimed
the **same** number of boxes, the game is a **draw** (possible on grids with an
even number of boxes, e.g. 5×4 = 20 boxes; the default 5×5 = 25 boxes cannot tie).

## Move encoding (for reference)

Each edge is identified by a kind, a column `c`, and a row `r`:

- **Horizontal** edge between dots `(c, r)` and `(c+1, r)`: `H{c},{r}`
  with `c` in `0..m-1`, `r` in `0..n`.
- **Vertical** edge between dots `(c, r)` and `(c, r+1)`: `V{c},{r}`
  with `c` in `0..m`, `r` in `0..n-1`.

In the web UI each undrawn edge is its own clickable slot — click it to draw the
line. Claimed boxes are shaded in the owner's colour and marked **1** / **2**.
