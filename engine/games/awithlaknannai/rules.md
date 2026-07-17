# Awithlaknannai Mosona

Awithlaknannai Mosona is a two-player capture game of the Zuni people of New
Mexico — one of the *Awithlaknannai* ("fighting serpents") games in the
Alquerque family. These are the rules **as implemented** here.

## The board

The board is the elongated **serpent lattice**: three parallel rows of points
joined into a long strip of triangles (lozenges).

- The **middle row has 9 points**; the **top and bottom rows have 8 points
  each** — **25 points** in total.
- The nine middle points are joined to each other by a straight horizontal line.
- Each of the 16 outer points sits *between* two middle points and is joined to
  both of them by a diagonal line. The outer rows are **not** connected to each
  other directly — only through the middle row.

This triangulation makes the strip out of 8 lozenges side by side. A piece moves
and captures **only along these drawn lines**. (The drawn lines are supplied as
cosmetic `board.lines`; the move/capture adjacency lives in code so it follows
exactly the lines shown.)

The three lines a piece can travel are therefore: along the middle row
(middle → middle → middle), and the two diagonal directions
(outer ↔ middle), which chain across the strip as middle → outer and
top-outer → middle → bottom-outer.

## Setup

Each player has **12 men** (one White, one Black). White fills the whole bottom
row (8) plus the **left half** of the middle row (4); Black fills the whole top
row (8) plus the **right half** of the middle row (4). The **single centre point
of the middle row starts empty** — that is the only vacancy. White moves first.

## Moving and capturing

- **Step:** move one of your men one point along a line to an adjacent **empty**
  point.
- **Capture:** jump one of your men over an **adjacent enemy** man, along a
  straight line, to the **empty point immediately beyond** — removing the jumped
  man (a draughts/Alquerque-style short jump). A jump may run along the middle
  row or along a diagonal; the landing point must be the next point on the same
  line and must be empty.

**Capturing is compulsory:** if any capture is available you must capture. A
**multi-jump** is played to its end as a single move — keep jumping with the same
man as long as it can, and you **may change direction** at each enemy. When
several captures are possible you may choose which one to begin.

## Winning and draws

You win by **capturing all of the opponent's men**, or by **leaving the opponent
with no legal move** on their turn. To guarantee termination, the game is drawn
after 50 plies with no capture, by threefold repetition of a position, or at a
hard ply cap.

## The 49-point board — Kolowis Awithlaknannai

The **Board** option selects the long serpent, *Kolowis Awithlaknannai*
("fighting serpents", after the mythical serpent Kolowis), described by Stewart
Culin in *Games of the North American Indians* (1907):

- **17 middle points, 16 outer points per row — 49 points** in total, the same
  triangulated lattice as above, just longer.
- Each player has **23 men**: the whole of their outer row (16) plus **seven**
  points of their half of the middle row. **Three points start empty**: the
  centre of the middle row **and both end points of the middle row** (unlike the
  25-point game, where the ends are occupied and only the centre is empty).
- All movement, capture, winning and draw rules are identical; the hard ply cap
  is doubled for the bigger board.

## Notation

A move is a `>`-separated path of points, shown as `a-b` for a step and
`a x b x c…` for a jump chain. Points are named by their `x,y` render coordinate.

## Ruleset notes / choices made

- **Board size.** Awithlaknannai Mosona is the **12-piece, 25-point** member of
  the serpent family; its larger sibling *Kolowis Awithlaknannai* (49 points,
  23 pieces) is available via the **Board** option. Sources agree on
  9 middle + 8 + 8 = 25 points and 12 men a side with only the centre empty;
  that is what is implemented.
- **End "curve" lines.** Some diagrams draw a curved line wrapping each end of
  the board. In this triangulated topology the end middle point is already joined
  to both of its outer neighbours, so no extra adjacency is needed and none is
  added; the ends behave as ordinary points.
- **Outer-row horizontal lines.** Two board variants exist (one with extra lines
  directly between adjacent outer points, one without). This package implements
  the **standard triangulated board without outer-row horizontal lines** — outer
  points connect only diagonally to the middle row.
- **Mandatory capture** is the standard Alquerque-family rule and is enforced
  here; multi-jumps are allowed and may change direction.
