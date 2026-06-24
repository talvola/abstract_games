# Meridians

**Designer:** Kanare Kato (2021). 2 players. A "line-of-sight" placement and
annihilation game with a territorial flavour. Winner of *Best Combinatorial
2-Player Game of 2021* (BoardGameGeek Abstract Games Forum).

These are the rules **as implemented** here, matching the official rules PDF
(*Meridians_EN.pdf*, © 2023 Kanare Kato). The official source link is on the
"Rules" dialog (BGG page).

## The board

A hexagon of grid **intersections** tessellated with triangles, with **two short
sides and four long sides**. Stones are placed on the intersections (as in Go).
The board is **centerless** (asymmetric — there is no single central point).

Sizes (long side / short side intersection counts):

- **Standard 6/7** — 114 intersections (default).
- **Beginner 5/6** — 80 intersections.
- **Expert 7/8** — 154 intersections.

Each interior intersection has **6 neighbours** and lies on **3 straight-line
families** (the "meridians"): the three axes of the triangular grid.

## Definitions

- **Group** — like-coloured stones adjacent to each other (edge adjacency). A
  single stone is a group of size 1.
- **Line of sight** — two same-coloured stones "see" each other if they lie on
  one of the three grid lines with **no enemy stone strictly between them**
  (friendly stones in between are fine — adjacency also counts as seeing).
- **Path** — an empty point, or an uninterrupted straight line of empty points,
  with a pair of like-coloured stones on both ends **that belong to different
  groups**. Such a pair is said to have a path. (So a path is a *clear* line of
  sight, over empty points only, from one friendly group to a *different*
  friendly group.)
- **Dead group** — a group in which **no** stone has a path. If *any* stone of a
  group has a path, the whole group is alive (line of sight is shared across the
  group).

## Play

Light (player 0) goes first, then players alternate. A turn is, **in order**:

1. **Capture** — remove **all** of the opponent's dead groups from the board.
   (Skipped while the opponent has taken fewer than two turns.)
2. **Place** — put one stone of your colour on an empty point.
   - On your **first** turn: any empty point.
   - From your **second** turn onward: an empty point that is on a straight line
     with at least one existing friendly stone, with no enemy stone in between
     (i.e. an empty point your stones can "see"). On the second turn this is
     exactly the rule "place so that your two stones have a path."

**Passing** is not allowed unless you have no legal placement (then you pass and
only the capture step happens).

## Winning

After the second turn, a player who has **no stones of their colour on the board
at the beginning of their turn** loses (all of their stones were captured). The
object is to **annihilate** the opponent. Because the opening board is empty, the
win is stored as an explicit event in the game state, not inferred from the
board.

In over-the-board play a second, faster ending is used: once both players have
sealed off territory the opponent cannot safely enter, the winner is decided by
counting how many stones each can still place without losing a group. **This
package does not implement that count-and-concede shortcut** — games here always
play to actual annihilation (or are resolved by resignation in the app).

## Interpretations / implementation notes

- **"No enemy stone in between" for placement** vs **"empty points only" for a
  path.** These are two different relations. *Placement* sight is blocked only by
  enemy stones (you may sight past your own stones). A *path* (which keeps a
  group alive) requires the connecting line to be entirely **empty** and to end
  at a *different* friendly group. Both are implemented exactly as written in the
  PDF.
- **Capture timing.** Each turn removes the opponent's dead groups *before*
  placing, so a group only ever dies on the opponent's turn. The "no stones at
  the start of your turn" loss is detected at exactly that moment.
- **Overlooked dead groups.** The PDF's optional "treat an overlooked dead group
  as alive until the next turn" courtesy rule is **not** modelled — captures are
  always resolved exactly and automatically.
- **Pie rule.** The PDF's optional pie rule (one player sets one stone of each
  colour, the other chooses a colour) is **not** implemented in this port; both
  players just play normally.
- **Termination safeguard (non-original).** The published game has no draw. To
  guarantee the engine always terminates under random self-play, a hard
  **ply cap** ends the game as a draw if it is somehow reached. It is far beyond
  any real game and never triggers in practice.
