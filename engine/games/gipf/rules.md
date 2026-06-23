# GIPF (basic game)

GIPF (Kris Burm, 1997) is the namesake game of the GIPF Project. Two players
introduce pieces onto a hexagonal board and shove them inward; lining up four or
more of your colour removes that row. You lose when you can no longer bring a
piece into play. This package implements the **basic game** (single pieces).

## Board

- **37 playing spots** form a hexagon: a radius-3 triangular grid of points, four
  points along each side, joined by lines in **three directions**.
- The spots are surrounded by a ring of **24 entry dots** (the radius-4 boundary
  of the same hex), one just outside each edge point. Dots are not playing spots;
  they are only used to introduce pieces.
- Internally, spots use **axial hex coordinates** `q,r` (centre `0,0`); the six
  corners are the extreme points, and the entry dots are the 24 cells one step
  beyond the board edge.

## Pieces and setup

- Each player has **15 pieces** in the basic game: **3 start on the board, 12 in
  reserve (in hand)**.
- The board starts with each player's **three pieces on the six corner spots**,
  the colours alternating around the hexagon. White is player 0 (bottom), Black
  is player 1 (top).

## A turn: introduce and shove

Each turn a player must bring **one** piece into play, in two linked steps:

1. Take a piece from your reserve and place it on an **entry dot**.
2. **Shove** it onto the first interior spot along that dot's line. If that spot
   is occupied, the piece there is pushed one spot further along the same line;
   if that spot is also occupied, it too moves on, and so on — the whole
   **contiguous run of pieces ahead** of your new piece slides one spot.

A shove is **illegal if the line is full all the way to the far edge** (there is
no empty spot on the line, so the front piece would be pushed off the board).

### Move notation

A move is encoded as `entryDot>firstSpot`, e.g. `-4,0>-3,0` — the dot you place
on, then the first interior spot you shove onto. This pair uniquely fixes the
line and the direction, and is directly clickable (click the dot, then the
spot). Row removals are follow-up sub-moves: the move is the run's lowest-numbered
cell id (one click), like a Nine Men's Morris mill removal.

## Rows of four or more (removal)

After the shove, any straight line of **four or more pieces of the same colour**
is removed — this is **compulsory**, and the pieces are taken **by the player who
owns that colour**, no matter who caused it.

When you remove a row you remove the four-(or-more)-in-a-row **plus the
contiguous extension**: keep going outward from the run, in both directions along
the line, taking every adjacent piece **until you hit an empty spot (a gap)**.
The extension may contain pieces of either colour:

- **Your own pieces** (the run and any own pieces in the extension) **return to
  your reserve**.
- **Opponent pieces** in the extension are **captured — removed from the game**
  (they do *not* go to anyone's reserve).

### Order when several rows form

The player who just moved resolves first: they remove **all rows of their own
colour** (if two such rows intersect, they choose which to take, then re-check),
then the **opponent removes any rows of the opponent's colour** that the shove
created. Removing pieces does not count as a separate turn — the whole
introduce-shove-remove sequence is one turn. This package resolves runs one at a
time, recomputing after each removal, mover's colour before opponent's colour.

## Winning / losing

The game ends when a player **must introduce a piece but has an empty reserve** —
that player **loses** (the opponent wins). A defensive cap of 400 introductions
forces a draw to guarantee termination; in practice random and real games end
well before it.

## Implemented interpretations / scope (flagged)

- **Entry geometry.** On the physical board each dot pushes along one fixed line.
  On an exact hex grid, the 6 corner dots have a single inward line (the long
  diagonals), but the 18 edge dots are each adjacent to **two** board spots, so a
  pure-grid model is ambiguous about which single line a mid-edge dot serves.
  This package resolves that cleanly by making the **move itself name the first
  interior spot** (`dot>firstSpot`): every physical-GIPF entry is representable,
  and where the grid leaves a choice the mover simply picks the spot. This is at
  most slightly more permissive than the physical board at the edge dots; the
  point counts (37 spots / 24 dots / 3 line directions) and all play mechanics
  match the official rules.
- **Basic game only.** The standard "GIPF pieces" variant (doubled pieces; 18
  pieces per player with 3 GIPF pieces starting on the board, and the extra
  loss-by-losing-all-GIPF-pieces condition) is **out of scope** for this package
  and is not implemented.

## Source

Official rules: gipf.com / Rio Grande Games rulebook; see also the BoardGameGeek
and Wikipedia "GIPF (game)" entries.
