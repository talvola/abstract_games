# Gess

**Gess** is a Go+chess hybrid invented by **The Archimedeans** (the Cambridge
University mathematics society) in **1994**. It is played with Go stones, but
unlike Go the stones move. The name is a portmanteau of *Go* and *chess*. Two
players, **Black** (player 0) and **White** (player 1), play; **Black moves
first**.

This page describes the rules **as implemented** in this package.

## The board

Internally the board is a **20×20 grid of cells**, coordinates `(c, r)` with
`c` = file 0..19 and `r` = row 0..19 (cell strings are `"c,r"`).

- The **inner 18×18** (c, r in **1..18**) is the **playable area**.
- The **outer ring** (c in {0,19} or r in {0,19}) is the **border / kill-zone**:
  no stone lives there — stones pushed onto a border cell vanish. It is tinted in
  the renderer so you can see the twilight zone.

Black starts at the **bottom** (low rows), White at the **top**. Files are
lettered a..t (a=0 … t=19) and rows are shown 1-based, so the cell `(11, 2)` is
**l3**.

## A piece is a footprint (chosen fresh each turn)

There are **no fixed pieces**. On your turn you choose **any 3×3 block of cells**,
identified by its **center cell**, subject to **all** of:

1. the **center is an inner cell** (c, r in 1..18);
2. the 3×3 contains **only your own stones** — zero enemy stones (the center
   itself may be empty or hold your stone);
3. **at least one of the 8 cells around the center** holds your stone.

The same stone can belong to many candidate footprints; you re-choose every move.

## Directions and range

Each **occupied outer cell** of the 3×3 enables movement in **that cell's compass
direction** relative to the center:

- a **corner** stone → the **diagonal** (NW/NE/SW/SE);
- an **edge** (orthogonal-neighbor) stone → the **orthogonal** (N/S/E/W).

An **empty** outer cell does **not** enable its direction.

**Range** depends on the center:

- center **occupied** (your stone there) → **unlimited** distance;
- center **empty** → at most **3** cells.

## Sliding, collision and capture

The whole 3×3 translates as a **rigid unit**, one cell at a time, in an enabled
direction. The carried stones are first lifted off the board; then the footprint
advances. It may keep advancing while the footprint contains **no non-carried
stone** (your own *or* enemy stones both block). It **stops** at the first step
where the footprint covers any non-carried stone, but it may also legally stop
**earlier** on any clear square (distance ≥ 1). The **center must remain on the
inner board** — the footprint can never leave entirely, though its outer cells
may hang over the border.

When the piece stops, **all non-carried stones in the destination 3×3 are
removed** (captured) — **including your own** non-carried stones (**self-capture**
is legal and is sometimes forced). The carried stones are then placed at the
destination in their original relative offsets.

### Border kill

After placing, any carried stone that landed on a **border cell** is **removed**
(it has been shoved off the edge). This is the only way stones leave the board
other than capture.

## Rings and winning

A **ring** is a 3×3 whose **8 outer cells all hold your stones** and whose
**center is empty**. You may own several rings and freely make or break them
during play.

**Win condition (multi-ring rule).** After a move fully resolves (including
border kill), rings are re-evaluated, **the mover first**:

- if the **mover** now has **zero rings**, the **mover loses** — even if the same
  move also removed the opponent's last ring (**mutual-ringless ⇒ the mover
  loses**);
- otherwise, if the **opponent** has **zero rings**, the **opponent loses** (the
  mover wins).

Only being ringless **at the end of your turn** loses; passing through zero rings
mid-resolution is not possible since rings are only checked once the move ends.

## Starting position

Each side has **43 stones**, arranged to emulate chess pieces on a 6×6 field
(R–B–Q–K–B–R back ranks plus pawns). The opening is **vertically
mirror-symmetric** (White is Black reflected across the midline, r → 19−r, same
files — like a chess setup, queen faces queen) with exactly **one ring per side** (Black's ring center **l3 = (11,2)**, White's
**l18 = (11,17)**).

- **Black** (bottom):
  - row 2 (r=1): files c, e, g, h, i, j, k, l, m, n, p, r
  - row 3 (r=2): files b, c, d, f, h, i, j, k, m, o, q, r, s
  - row 4 (r=3): files c, e, g, h, i, j, k, l, m, n, p, r
  - row 7 (r=6): files c, f, i, l, o, r
- **White** (top): the vertical mirror of Black (row 2↔19, 3↔18, 4↔17, 7↔14).

## Moves

A move is the string **`"cx,cy>dx,dy"`** = the footprint **center's source
cell → destination cell**. The eight directions and the distance are implied by
the vector `(dx−cx, dy−cy)`, which is always a pure compass ray. In the web UI
this is a two-click move: click the footprint center, then the destination. The
move log shows file-letter notation, e.g. `l3-l6` (a slide) or `l3xl6` (a
capture).

## Deviations from original Gess (flagged)

- **Multi-ring / mutual-ringless tie-break.** Sources state plainly: *"when, at
  the end of any turn, a player has no ring pieces on the board, that player loses
  the game."* This package evaluates the **mover first**, so a move that strands
  the mover ringless **loses for the mover** even if it simultaneously removes the
  opponent's last ring. This is the standard reading; it is documented here
  because casual rule summaries do not spell out the simultaneous case.
- **Termination safeguard (NOT part of original Gess).** Gess has no native draw
  or repetition rule and can cycle, but the platform's conformance harness plays
  random games to a terminal state. This package therefore adds a **no-progress
  draw** (60 plies with no capture) **and a hard ply cap** (400 plies) → **draw**.
  These are tuned so real games essentially never reach them while random play
  always terminates; they are **not** part of the original ruleset.
