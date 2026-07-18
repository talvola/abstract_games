# Onyx

Larry Back's connection game **with a capture rule** (invented 1995, published
in *Abstract Games* #4, Winter 2000). Two players: **Black** (first player)
connects the **top and bottom** edges; **White** connects the **left and
right** edges. The four corner points belong to both of their adjacent edges.

## Board

A 12×12 grid of points (columns a–l, rows 1–12) drawn as interlocking squares
and triangles (a snub-square lattice). In a checkerboard pattern, 60 of the
unit cells are **squares**, each subdivided by both diagonals with a new
playable **midpoint** at its centre; every other cell is split by a single
diagonal into two triangles. Stones are placed on points (204 in all) and are
connected along the drawn line segments — grid edges, triangle diagonals, and
the four half-diagonals joining a midpoint to its square's corners.

## Setup

* **Official** (default): Black starts on a6, a7, l6, l7 and White on f1, g1,
  f12, g12 — the two outside corners of the middle square along each of the
  opponent's sides.
* **Empty**: no pre-placed stones (the article mentions both).

## Moves

Players alternate; each turn you **must** place one stone of your colour on an
empty point. Restriction: a **midpoint** may only be taken while **all four
corner points of its square are empty**. Stones never move once placed.

**Pie rule**: Black places the first stone; the second player may then
**swap** (choose to be Black) instead of replying. Because the two goals run
in different directions, the swap is implemented by transposing the position
across the main diagonal and recolouring it (an exact mirror of "the second
player takes Black"); play then continues normally.

## Capture

If your placement on a **corner point** of a square results in **both players
occupying two diagonally-opposite corner pairs** of that square while the
square's **midpoint is unoccupied**, the two enemy stones on that square are
captured and removed (returned to their owner). One placement can complete
this crosscut on **two squares at once** — then all four enemy stones are
removed. Captures are automatic and mandatory. Placements on midpoints never
capture, and an occupied midpoint protects its square from capture forever.

## End of the game

The first player to link their two edges with an unbroken chain of their own
stones wins. Draws cannot occur in serious play; as an engine safeguard, a
player with no legal placement (every empty point a blocked midpoint) or a
game reaching 600 plies is scored an honest draw.

## Notation

The move log uses Back's official notation: points are letter+number ("F6"),
midpoints name their square's columns and rows ("DE910"), and each captured
pair appends an asterisk ("G7*", "E5**").
