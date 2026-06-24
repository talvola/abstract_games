# Hexxagon

**Hexxagon** is the hexagonal-board variant of **Ataxx** — a clone / jump /
infection game. Spread your colour across the board; whoever holds the most hexes
when no one can move (or the board fills) wins.

## Board

A **hexagon of hexagons** ("hexhex") of side length **5 = 61 cells**, with **3
blocked "holes"** near the center removed, leaving **58 playable hexes**.

- Cells use **axial coordinates** `q,r`. A cell is on the board when
  `max(|q|, |r|, |q+r|) <= 4`. Hex distance between two cells is
  `(|dq| + |dr| + |dq+dr|) / 2`.
- **Holes** are dark, blocked cells: you can never move onto one, no piece ever
  sits there, and they are *not* counted as neighbours for infection.

### Holes layout (interpretation)

The original Hexxagon shipped a board editor with many layouts, so the holes are
**not canonically fixed**. We use a clean, **3-fold rotationally-symmetric**
default: the 3 holes at `(1,0)`, `(-1,1)`, `(0,-1)` — three of the six cells
adjacent to the center, at alternating 120°-apart positions. This leaves the
center `(0,0)` playable and the board symmetric for both players. You can turn
holes off entirely with the **Center holes** option (`none` → all 61 hexes
playable).

## Pieces and start

Two players, **Red (moves first)** and **Blue**, each start with **3 pieces** on
**alternating corners** of the hexagon. The six corners, in cyclic order, are
`(0,-4), (4,-4), (4,0), (0,4), (-4,4), (-4,0)`. Going around the ring they are
assigned **Red, Blue, Red, Blue, Red, Blue**, so:

- **Red:** `(0,-4)`, `(4,0)`, `(-4,4)`
- **Blue:** `(4,-4)`, `(0,4)`, `(-4,0)`

Each player thus holds 3 non-adjacent corners, and every piece sits directly
opposite an enemy (nearest enemy at the maximum hex distance of 4).

## A turn

On your turn you **move one of your pieces onto an empty (non-hole) cell**, in one
of two ways, by hex distance from the source:

- **Grow / clone — hex distance 1** (one of the **6 adjacent hexes**): a **new**
  piece of your colour appears on the destination; the **source stays** (you go
  from *n* to *n+1* pieces).
- **Jump — hex distance exactly 2** (the **12-hex second ring**): the piece
  **relocates** — the source becomes empty, your piece count is unchanged.

Moves are written `src>dst`, e.g. `0,-4>1,-4` (a grow) or `0,-4>2,-4` (a jump).

### Infection

After your piece lands (grow or jump), **every opponent piece in the 6 hexes
adjacent to the destination flips to your colour.** Only the immediate
6-neighbourhood of the landing cell is affected — there is no chaining, and holes
are never neighbours.

### Passing

A player who has **at least one legal move must move.** A player with **no legal
move passes** (their turn is skipped).

## Ending and winner

The game ends when:

- the board is full (all 58 playable hexes occupied), **or**
- neither player can move, **or**
- a player is **eliminated**.

**Auto-fill on elimination:** when a move **wipes out the opponent** (they had
pieces before the move and none after — e.g. their last piece was infected away),
the surviving player's colour **automatically fills every remaining empty
(non-hole) cell**, ending the game immediately. This matters on a board with
holes, where an unreachable empty region would otherwise stay empty.

**Winner = most pieces.** Equal counts are a **draw** (a tie is genuinely
possible, since 58 playable cells is an even number).

## Termination

Every grow adds a piece (the board is bounded at 58), and jumps and infections
never reduce the total piece count, so play cannot cycle indefinitely. A
defensive hard ply cap also forces an end-and-count.

## Notes / interpretations

- This is the **hex Ataxx** variant; mechanics (clone, jump, infect, most-pieces
  wins, pass on no move, auto-fill on elimination) mirror Ataxx exactly, on a hex
  board with 3 holes and 3 starting pieces per side.
- The **holes layout** above is our documented interpretation (see *Holes
  layout*).
