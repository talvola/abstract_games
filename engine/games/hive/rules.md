# Hive

By John Yianni (Gen42 Games, 2001). Base game, no expansions. Two players,
**White (0)** and **Black (1)**. White moves first.

Hive has **no board** — the insect tiles themselves *are* the board, a single
growing cluster of hexagons (the *hive*). The goal is to completely **surround
the opponent's Queen Bee**.

## Your pieces (11 each)

| Letter | Piece | Count |
|---|---|---|
| Q | Queen Bee | 1 |
| S | Spider | 2 |
| B | Beetle | 2 |
| G | Grasshopper | 3 |
| A | Soldier Ant | 3 |

On your turn you either **place** a new piece from your hand or **move** a piece
already in the hive. (If you can do neither, you must **pass**.)

## Placing a piece

- The **first** piece of the game is placed at the origin. The **second** piece
  (the opponent's first) is placed adjacent to it — this is the only placement
  allowed to touch an enemy piece.
- From then on, a newly placed piece must touch the hive and may touch **only
  your own** pieces — never an enemy piece.
- **Queen by the 4th piece:** you must place your Queen Bee on or before your
  4th placement. If your Queen is still in hand when you go to place your 4th
  piece, the Queen is the *only* piece you may place.
- You may **not move any piece** until your Queen Bee has been placed.

## Two rules that constrain every move

- **One-Hive rule:** the hive must stay a single connected group at all times. A
  piece may not move if picking it up would split the hive in two (it is an
  *articulation point*). A piece that has another piece stacked on top of it is
  not removed when its top piece moves, so it never splits the hive.
- **Freedom to Move (the gap rule):** when a piece *slides* one hex from X to an
  adjacent empty hex Y, exactly **one** of the two hexes common to X and Y must
  be occupied — there must be room to physically slide (you cannot squeeze
  through a one-hex gap) while staying in contact with the hive. Grasshoppers
  (which jump) and a Beetle climbing up/over are exempt from the squeeze rule.

## How each bug moves

- **Queen Bee** — slides exactly **1** hex.
- **Soldier Ant** — slides **any number** of hexes around the outside of the
  hive (any cell reachable by a chain of legal slides).
- **Spider** — slides **exactly 3** hexes, never revisiting a hex it touched
  during this move (no backtracking); every intermediate step must be a legal
  slide.
- **Grasshopper** — **jumps** in a straight hex line over one or more
  **contiguous** occupied hexes, landing on the first empty hex beyond. It cannot
  jump over a gap, and must jump over at least one piece.
- **Beetle** — moves exactly **1** hex, and may **climb on top** of an adjacent
  piece, forming a stack. A piece underneath a beetle is **frozen** (cannot
  move). A beetle on top moves one step in any direction — onto the hive or back
  down to the ground. While at height, a beetle is blocked from a step only if
  both of the two gates between its source and destination are stacks *taller*
  than the level it is moving at (you can't slip between two taller walls). A
  beetle on top of the enemy Queen counts toward surrounding it.

## Winning

A player whose **Queen Bee is surrounded on all 6 sides** (by friendly or enemy
pieces/stacks) **loses**. If a single move surrounds **both** Queens at once, the
game is a **draw**.

## Passing

If you have no legal placement and no legal move, you must **pass** (the only
legal move that turn).

## Render / move encoding (this implementation)

- The board is drawn as a `polygons` hex cluster: every occupied hex plus every
  empty hex that is a legal target this turn (so legal placements and move
  destinations light up). Cell id = the axial hex coordinate `"q,r"`.
- Your hand is shown as a per-seat **reserve** tray. A **placement** is the drop
  move `"<bug>@q,r"` (e.g. `A@0,0`) — click a bug chip, then a highlighted cell.
- A **move** of a placed piece is `"from>to"`, e.g. `"1,0>0,1"` — click the
  piece, then a highlighted destination.
- A stack (beetle on top) draws as a tower with a height badge; its label is the
  top bug's letter.
- A forced **pass** appears as a `pass` action button.

## Termination

Hive can in principle cycle. For the engine's automated play this implementation
adds two safety draws: a hard cap of **300 plies**, and a no-progress cap of
**60 plies with no new piece placed**. Neither is reachable in normal human play.
