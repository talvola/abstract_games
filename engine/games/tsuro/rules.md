# Tsuro

*Tom McMurchie / Calliope Games, 2004.* Ride your path tiles across the board and
be the last marker standing. This package implements a clean **2-player** version
of the 2–8 player game.

## The board

A **6×6** grid of square cells. Each cell has **8 edge-notches** at the third-points
of its four sides, numbered clockwise from the cell's top-left:

- `0,1` = **top** side (left, right)
- `2,3` = **right** side (top, bottom)
- `4,5` = **bottom** side (right, left)
- `6,7` = **left** side (bottom, top)

## The tiles

A **path tile** is a square whose 8 notches are joined in **4 pairs** — a perfect
matching of `{0…7}`. There are exactly **35** distinct tiles up to rotation, and
the deck is those 35 tiles.

**Rotation** turns a tile 90° clockwise by mapping every notch `n → (n+2) mod 8`
on all four pairs. The 35-tile deck is the set of distinct matchings up to that
rotation (105 perfect matchings collapse to 35 rotation classes).

At setup the deck is **shuffled** and each player is dealt a **hand of 3 tiles**
(the rest form the draw pile). The shuffle/deal use the engine's RNG and are
**stored in the state** — there is no separate chance node (`has_randomness: true`).

## Markers and start

Each player has **one marker**. A marker rests on a notch at the edge of an empty,
on-board cell, facing inward (the notch's cross-neighbour is off the board, i.e. it
lies on the board's outer boundary):

- **Player 1** starts on cell **`0,1`**, notch **6** (left edge).
- **Player 2** starts on cell **`5,4`**, notch **3** (right edge).

Player 1 moves first.

## A turn

The current player **must place a tile on the cell their marker rests on** (that
cell is forced — it is the only legal placement). They choose **which** of their 3
hand tiles and **which** of its 4 rotations.

After the tile is placed, the marker **follows the painted path**:

1. It enters the tile at its current notch and rides the arc to the **other notch
   of that pair** (the tile's exit).
2. It **crosses** to the neighbouring cell via the fixed cross-cell mapping (below),
   entering that neighbour at the matching notch.
3. If the neighbour already has a placed tile, repeat from step 1; otherwise the
   marker **stops** there, on the edge of that (empty) cell.

If the path carries the marker **off the board edge**, it is **eliminated**.

After moving, the player **draws** back up to 3 tiles (if the deck has tiles), and
play passes to the other player.

### Cross-cell notch mapping

A marker leaving a cell through an exit notch enters the neighbour at the matching
notch:

| exit | neighbour | enters at |
|------|-----------|-----------|
| 0 (top)    | (c, r+1) | 5 |
| 1 (top)    | (c, r+1) | 4 |
| 2 (right)  | (c+1, r) | 7 |
| 3 (right)  | (c+1, r) | 6 |
| 4 (bottom) | (c, r−1) | 1 |
| 5 (bottom) | (c, r−1) | 0 |
| 6 (left)   | (c−1, r) | 3 |
| 7 (left)   | (c−1, r) | 2 |

(So the board's **+row** direction is the visual "top".) A notch whose neighbour
cell is off the 6×6 board is the board's outer boundary.

## No suicide unless forced

A player **may not** choose a placement that sends **their own** marker off the
board **if any** of their legal (tile, rotation) choices keeps it on. Only when
**every** option is self-eliminating may a self-eliminating placement be played.

## Elimination, collision, win, draw

- A marker carried **off the board edge** is eliminated.
- If two markers come to rest on the **same notch** (a collision), **both** are
  eliminated.
- The **last marker on the board wins**.
- If the final placement eliminates the last remaining markers **simultaneously**
  (e.g. a mutual collision, or the move was forced and both die), the game is a
  **draw**.

## Deck / dragon (simplified)

In the full game an empty deck hands a "dragon tile" to the next player who needs a
tile, and tiles return when eliminated players' hands come back. In this 2-player
implementation: when a player is eliminated, **their hand returns to the deck**, and
the mover refills to 3 from the deck (drawing nothing if the deck is empty). With
35 tiles and only two markers the deck effectively never runs out before the game
ends; a **400-ply safety cap** declares a draw in the (unreachable in practice)
event of non-termination.

## Move encoding

A move is the forced target cell id plus a `=CHOICE` suffix naming
`<hand-tile index>.<rotation>`, e.g. **`2,3=0.1`** = place hand tile 0, rotated
90° clockwise once, on cell `2,3`. The web UI's `=CHOICE` picker (titled "Place a
path tile") lists each legal choice with a friendly label such as **"Tile 1 ⟳90"**.
The current player's three hand tiles are also shown as path-pattern cards.
