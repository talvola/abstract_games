# Necklace

**Mark Steere and Luis Bolaños Mures (March 2024).** A square-board connection
game with **orthogonal-only** chains, made drawless by two placement
restrictions: you may not create a **crosscut**, and you may never **strand a
group of empty points** away from the edge of the board. *(Rules as implemented
in this package.)*

## Board and goal

- Played on the points of an initially empty square grid (default **11×11**;
  this package also offers 7, 9, 13 and 19 — Steere's sheet says "any size").
- **The top and bottom edges are red; the left and right edges are blue.**
- **Red** (player 0, moves first) wins by forming a path of red stones —
  interconnected via **horizontal or vertical adjacencies only** — connecting
  the two red sides of the board. **Blue** (player 1) connects the two blue
  sides.
- **Diagonal adjacency does NOT connect.** The designers call Necklace an
  **OOSCG** — an *orthogonal only square connection game*.
- A corner point belongs to both of its edges.

## Playing a turn

Starting with **Red**, players alternate placing **one stone of their own
colour on any unoccupied point**, subject to the two restrictions below.
Nothing is ever moved, removed, flipped or captured.

**Passing is not allowed, but if you have no available placement your turn is
skipped** and your opponent plays again. (In this implementation the skip
happens automatically — you are never offered a "pass" button.)

**There is no pie rule.** The official sheet has none; its PLAY section says
only "starting with Red". (AbstractPlay's implementation carries a site-level
pie flag, which is a convention of that site rather than a rule of Necklace.)

## Restriction 1 — no crosscut

A **crosscut** is four stones, two of each colour, filling a 2×2 area, each
stone orthogonally adjacent to its two enemy stones. Equivalently: a full 2×2
whose two diagonals are each monochrome and of opposite colours. There are
exactly two such formations (the two diagonal orientations), and the rule
sheet's Figure 2 prints both:

```
 R B      B R
 B R      R B
```

**Your placement must not create a crosscut.** Concretely, you may not play on
an empty point if, in some 2×2 area containing it, the diagonally opposite
point holds one of **your** stones while **both** of the other two points hold
**enemy** stones.

Because no legal move ever creates one, a crosscut is never present on the
board.

## Restriction 2 — every empty group must reach an edge

**After your placement, any group of unoccupied points must include an edge
point.** An *empty group* (or region) is a maximal set of orthogonally
adjacent unoccupied points; an *edge point* is any point in the top row, the
bottom row, the leftmost column or the rightmost column.

This is the "no loop" rule the design notes describe, and it is what gives the
game its name: you may never close a **necklace** of stones around empty
territory. It applies to both players alike — it does not care whose stone you
are placing, nor which colours make up the encircling ring.

Three stones are enough to make a point illegal. On a 5×5 board:

```
. . . . .
. . . . .
. . . R .
. . R . B
. . . x .     x = an illegal placement, for EITHER colour
```

Playing `x` (a point on the bottom edge) would seal the point above it — its
four orthogonal neighbours would then all be occupied — leaving a one-point
empty group with no edge point. In the sheet's own Figure 3 the same thing
happens on a larger scale: the marked point sits on the bottom edge and filling
it cuts a **four**-point empty group off from every edge.

## Why there are no draws

1. **No point is ever blocked for both colours.** If placing *red* on a point
   would make a crosscut, some horizontal neighbour of that point is blue and
   some vertical neighbour is blue; if placing *blue* there would make a
   crosscut, some horizontal neighbour is red and some vertical neighbour is
   red. The two 2×2 areas must therefore be diagonally opposite, which forces
   **all four** orthogonal neighbours to be occupied — so that point is an
   empty region all by itself, and restriction 2 then requires it to be on the
   edge. But on the edge the two candidate 2×2 areas share their inward
   neighbour, which would have to be blue and red at once. Contradiction.
2. **Restriction 2 never blocks a whole region.** Take a spanning tree of an
   empty region rooted at one of its edge points; filling any leaf other than
   the root leaves the region connected and still holding that edge point. (If
   the region is a *single* point it is that edge point, and filling it deletes
   the region outright — so there is nothing left to strand either way.)
3. So **while any point is empty, at least one player can place**, and play
   only stops when the board is full.
4. **A full board with no crosscut has exactly one winner.** On a full board,
   two diagonally adjacent stones of one colour must have a friendly stone on
   one of the two points completing their 2×2 (otherwise it is a crosscut), so
   orthogonal and diagonal connectivity coincide; and on a fully coloured
   square board exactly one of "red joins top to bottom (8-connected)" and
   "blue joins left to right (4-connected)" holds.

Hence **every game ends in a win** — in fact it ends the moment the winning
stone is placed, before the board can fill. A double-stall is nevertheless
scored as an honest draw in code (`0, 0`) rather than by a fabricated
tiebreak; it has never been observed, in exhaustive game-tree solves of the
2×2 and 3×3 boards (both first-player wins), in an exhaustive enumeration of
all 65,536 occupancy patterns of the 4×4 board, or in 18,800 random games
spread over sizes 2–11.

(Steps 1 and 2 of the argument above are asserted on constructed inputs in
`selftest.py` — all 6,561 colourings of a point's eight neighbours for step 1,
and every legal non-full 4×4 position for step 2 — precisely because random
play can never reach the situations they rule out.)

## Termination

Every ply places one stone on a previously empty point and nothing is ever
removed, so the number of empty points strictly decreases and a game of size
*n* lasts at most *n²* plies. A skipped turn places no stone but is folded into
the placement before it, so it cannot extend that bound. **There is no ply cap
and no repetition rule.**

## Notation and the interface

- Click an empty point to place. Illegal points are simply not offered.
- The move log uses `a1`-style coordinates: file letters `a`… run left to
  right, rank numbers `1`… run **top to bottom**. `#` marks the winning
  placement.

## Bot strength

This package ships a `heuristic` for the bot's rollout cutoff: a 0-1 BFS "how
many more stones do I need to join my edges" evaluation (own stone free, empty
point costs one, enemy stone blocks), squashed with `tanh`. It ignores both
placement restrictions, so it is only a rough guide.

It was measured **through `MCTSBot`, the consumer that uses it**, against the
same bot with no evaluation, colours alternating. Two people measured it
independently; both runs are pooled below, and the intervals are **exact
(Clopper–Pearson)** — the normal approximation is not trustworthy at these
sample sizes and, at 17/24, wrongly excludes 0.5.

| setting | build | QA replication | pooled | exact 95% CI | p (two-sided) |
| --- | --- | --- | --- | --- | --- |
| 9×9, `max_rollout=50` (production shape) | 17 / 24 | 14 / 24 | **31 / 48** = 0.646 | 0.495 – 0.778 | 0.060 |
| `max_rollout=4` (cutoff forced on every rollout) | 9 / 9 | 19 / 30 | **28 / 39** = 0.718 | 0.551 – 0.850 | 0.010 |

Read this as: the evaluation **does** help when the rollout cutoff actually
fires — which is the job it exists to do — but at the production shape the
advantage is **not statistically established** (the interval still contains
0.5). "Somewhat better than nothing", not a strong bot.

## Source

Official rule sheet: `marksteeregames.com/Necklace_rules.pdf`
(md5 `43183b5648e896bbe07e168ae0fec4fd`, ModDate 2024-03-30 17:33:21 PDT). All
three of its figures are transcribed verbatim in `selftest.py` and all three
match this implementation exactly. Unlike several of its Steere siblings this
sheet has never been silently revised: the only Wayback capture
(2024-04-15) is byte-identical to the file served today.

## Related games in this collection

Necklace is the only game here that restricts placements by a **global
topological** condition (no enclosed empty region). Its square-board
connection siblings answer the crosscut problem differently: **Crossway** bans
crosscuts but connects **8-adjacently**; **Minefield** bans two partly-empty
stone glyphs; **Konobi**, **Rhode**, **Akimbo** and **Okimba** constrain or
consolidate diagonal links; **Cation** allows crosscuts and forces their
resolution through ko fights.
