# Pex

**Pex** is a connection game invented by **David J. Bush** (an avid Hex player) in
2008, using a special pentagonal board designed by mathematician **Marjorie
Rice**. It is a member of the Hex family (Hex, Y, Havannah, Crossway, …): the
rules *are* Hex — the only thing that changes is the shape of the cells.

## The board

Instead of hexagons, Pex is played on a rhombus of **congruent convex
pentagons** — Marjorie Rice's **type-11** tiling, one of the 15 known monohedral
convex-pentagon tilings. Bush chose type 11 because it satisfies two conditions
that let Hex's theory carry over to pentagons:

1. **No vertex has more than three edges meeting at it** (the tiling is
   *trivalent*), so its dual is a triangulation. This is exactly the condition
   behind Hex's famous **no-draw theorem**: a completely filled board *always*
   has exactly one winner.
2. **It is topologically different from a hexagonal grid.** Not every interior
   cell has six neighbours — instead, **half the interior cells touch seven
   neighbours** (drawn **yellow**) and **half touch only five** (drawn
   **green**). Bush chose pattern 11 over the other qualifying pattern (14)
   because it made connecting the two colours feel about equally hard, so the
   pie rule yields a near-perfectly fair game.

The canonical igGameCenter board is **8×8 = 128 pentagons** (64 yellow + 64
green). The four sides of the rhombus are coloured in pairs:

- **Red** owns the **top** and **bottom** edges.
- **Blue** owns the **left** and **right** edges.

## How to play

- The board starts empty. **Red (Player 1)** moves first.
- On your turn, place **one stone of your colour on any empty cell**.
- **Red wins** by forming an unbroken chain of red stones connecting the **top**
  edge to the **bottom** edge. **Blue wins** by connecting the **left** edge to
  the **right** edge.
- **There are no draws.** Once the board is full, exactly one player has
  connected their edges — so the game always ends with a winner.

### Pie rule (swap)

Because moving first is an advantage, Pex uses the **pie rule**. After Red's
first placement, Blue may — instead of placing a stone — choose **"swap"**. This
hands the strong opening to the second player: the mover takes over Red (and the
lone first stone), the opener continues as Blue, and play proceeds. Swap is only
offered on the second player's very first turn.

## Notation

A move is a single **cell id**: a column letter **A–H**, a row number **1–8**,
and a suffix — **Y** for a yellow (7-neighbour) cell or **G** for a green
(5-neighbour) cell — e.g. `D4Y`. The pie-rule move is the literal `swap`.

## About this implementation

This package reconstructs the **exact 8×8 board used on igGameCenter**: the 128
pentagon polygons, their adjacency graph, and the four coloured edges were
extracted directly from the official board image, then verified — the interior
degree structure is exactly the type-11 signature (cells of degree 5 and 7), the
adjacency graph is symmetric, and a fuzz test confirms that every possible
filled board has exactly one winner (the no-draw property). Only the canonical
8×8 board is provided.

**Credits:** game by David J. Bush; pentagonal tiling by Marjorie Rice (who
"deserves equal credit in the creation of Pex"). Official rules and board:
[igGameCenter](https://www.iggamecenter.com/en/rules/pex).
