# Poly-Y

**Poly-Y** is Craige Schensted & Charles Titus's polygonal generalisation of the
connection game **Y** (described in their book *Mudcrack Y & Poly-Y*, 1975). It is
played on a board shaped like a polygon with an **odd number of sides** — this
package uses the smallest classic shape, a **pentagon** with **5 sides and 5
corners**.

## The board

The pentagon is a tiling of **hexagonal cells** built as five triangular sectors
meeting at a single central cell (the "mudcrack" pie construction). The board has
full 5-fold symmetry. For the default side parameter `n = 4` it has **101 cells**;
each of the 5 sides has `2n+1 = 9` boundary cells (sharing the corner cells with
its neighbours).

- The **5 corners** are the outer tips where two sides meet (shown in gold).
- The **5 sides** are the runs of boundary cells between consecutive corners
  (each tinted its own colour).
- A **corner cell counts as part of both sides that meet there** — exactly as in
  the parent game Y.

## How to play

- **Black** moves first. Players **alternately place one stone** of their colour
  on any empty cell.
- Stones **never move** and are **never captured**.
- **Pie (swap) rule** (on by default): on the second player's first turn they may
  play **swap** instead of placing — adopting the lone opening stone as their own
  and handing the move back. This balances the first-move advantage.
- Play continues until the **board is full**.

## Winning — corner ownership

When the board is full, every corner is awarded to exactly one player.

> **Corner k is owned by the player whose single connected group touches the two
> sides adjacent to that corner AND at least one other (non-adjacent) side** —
> i.e. a player makes a **"Y"** that links the corner's two sides to a third side
> of the board.

Equivalently, split the pentagon's boundary into three arcs — the two sides
meeting at the corner, and the remaining three sides taken together — and the
corner goes to whoever connects all three arcs with one group.

**The player owning a majority of the 5 corners (3 or more) wins.** Because there
is an **odd** number of corners, and the Hex/Y disk theorem guarantees that on a
full board each corner is connected by exactly one player, **Poly-Y can never end
in a draw**.

## Board size

The **Board side** option (`n = 3, 4, 5`) sets the number of cells along each
spoke from the centre to a corner; larger `n` gives a bigger, deeper board.

## Sources

- Craige Schensted & Charles Titus, *Mudcrack Y & Poly-Y* (1975).
- Dr Eric Silverman, "Connection Games II: Y, Poly-Y, Star and \*Star".
- [Y (game) — Wikipedia](https://en.wikipedia.org/wiki/Y_(game)),
  [Poly-Y on BoardGameGeek](https://boardgamegeek.com/boardgame/179816/poly-y).
