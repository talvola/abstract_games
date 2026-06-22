# Focus (a.k.a. Domination)

Sid Sackson's 1964 stacking classic, as implemented here (2-player game).

## The board

An **8×8 grid with the three corner cells removed at each of the four corners**,
leaving a **52-cell octagon**: a 6×6 core with a 1×4 arm protruding from each side.

In `c,r` coordinates (column, row; both 0–7) the **12 removed corner cells** are:

```
(0,0) (1,0) (0,1)      (7,0) (6,0) (7,1)
(0,7) (1,7) (0,6)      (7,7) (6,7) (7,6)
```

Only the other 52 cells exist; the renderer supplies exactly those.

## Starting layout

Each player owns **18 pieces**. They fill the central **6×6 area** (columns 1–6,
rows 1–6), **one piece per cell**, in 2-wide colour stripes; the four arms start
empty (16 empty cells). With **R = Red (player 0)** and **G = Green (player 1)**,
reading the central 6×6 left-to-right, top (row 1) to bottom (row 6):

```
row 1:  R R G G R R
row 2:  G G R R G G
row 3:  R R G G R R
row 4:  G G R R G G
row 5:  R R G G R R
row 6:  G G R R G G
```

That is exactly 18 Red and 18 Green single pieces. Red moves first.

## A stack and who controls it

A cell holds a vertical **stack** of pieces (an ordered column, bottom → top).
**You control a stack if, and only if, your piece is on top.** Only the
controlling player may move that stack, and only the top piece's ownership
matters for control.

## Your turn — do exactly ONE of:

### (A) Move a stack you control

1. Pick a stack whose **top** piece is yours.
2. Choose how many pieces to lift: **`k` = 1 … the stack's height**. You lift the
   **top `k` pieces** (their internal order is preserved).
3. Slide them in one **orthogonal** direction (up/down/left/right) **exactly `k`
   cells**. The number of pieces lifted equals the distance travelled — lift more
   pieces to move farther, up to the full stack height. The destination must be an
   on-board cell.
4. The lifted sub-stack is placed **on top** of whatever already occupies the
   destination cell (which may be empty, your stack, or an enemy stack).

So a height-1 piece moves 1 cell; a height-3 stack can move the top 1 piece 1
cell, the top 2 pieces 2 cells, or all 3 pieces 3 cells.

### (B) Drop a reserve piece

If you have at least one piece **in reserve**, you may instead **drop one reserve
piece onto any cell** — empty or occupied — placing it **on top** of whatever is
there. A drop is your **entire turn** (you don't also move).

## Stack cap — the over-5 rule

A stack may temporarily be built taller than 5 by a move or drop. **Immediately
after** the placement, if the destination stack is **taller than 5**, remove
pieces from the **BOTTOM** until **exactly 5** remain. For each removed piece:

- if it is **yours** (the player who just moved/dropped), it goes to **your
  reserve** (to be dropped later via move (B));
- if it is an **enemy** piece, it is **captured** — permanently out of play.

(Only the bottom pieces below the top 5 are shed; the top 5 stay put, in order.)

## Winning

**The last player able to move wins.** Concretely: on your turn, if you can
neither move any stack you control **nor** drop a reserve piece, **you lose** (your
opponent wins). Equivalently, you win by controlling every stack on the board
while your opponent has no reserve piece to drop — leaving them with no legal
action.

A defensive ply cap (1000 plies) declares a draw if play somehow never ends; in
normal play Focus terminates well before then.

## Move notation

- **Stack move:** `src>dst=k` — e.g. `3,3>3,5=2` lifts the top 2 pieces of the
  stack on `3,3` and moves them 2 cells to `3,5`, landing on top there.
- **Reserve drop:** `P@c,r` — e.g. `P@3,4` drops one reserve piece onto `3,4`.

## Implementation notes / choices

- This package implements the **classic Sackson move-up-to-stack-height** rule
  (distance = pieces lifted), not the simplified Milton-Bradley "Domination"
  variant where every move is a single space.
- The "last player able to move wins" condition is taken straight from the
  standard rules (a stuck player loses). The alternate "first to capture 6"
  fast-game win is **not** implemented.
- Reserve pieces are shared as a single count per player (all your pieces are
  identical), dropped with the letter `P`.
