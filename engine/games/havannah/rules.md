# Havannah

Havannah is a connection game invented by **Christian Freeling** in 1979. It is
played on a **hexagonal board of hexagons** (a "hexhex") of side length *N*
(this package offers N = 6, 8, or 10; 8 and 10 are the most common competitive
sizes). The board starts empty.

## Play

- Two players, **Red** (player 0) and **Blue** (player 1), alternate turns.
- On your turn you **place one stone of your colour on any empty cell.**
- **Stones never move and are never captured.** Once placed, a stone stays for
  the rest of the game.

## Goal — win by completing any ONE structure

You win **immediately** when your stones complete any one of these three
structures. (Connection always means orthogonal hex adjacency — each cell has up
to 6 neighbours.)

1. **Ring** — a loop of connected friendly stones that surrounds **at least one
   cell**. The surrounded cell(s) may be empty, your own, or your opponent's — a
   ring counts no matter what is inside it. (A ring needs at least 6 stones.)

2. **Bridge** — a connected chain of friendly stones that joins **any two of the
   six corner cells** of the hexagon.

3. **Fork** — a connected chain of friendly stones that joins **any three of the
   six edges** of the hexagon. Corner cells do **not** count as belonging to any
   edge for the purposes of a fork (see definitions below).

If the board fills completely with no structure made, the game is scored as a
**draw**. In real play this essentially never happens; the rule exists only so
the engine is guaranteed to terminate.

## Corner and edge definitions

Cells use **axial coordinates** `(q, r)`; the implied third cube coordinate is
`s = -q - r`. A cell is on the board iff `max(|q|, |r|, |s|) <= N - 1`.

- The **six corners** are the cells where two of the three cube coordinates are
  at their extreme value `±(N-1)`:
  `(N-1, 0)`, `(N-1, -(N-1))`, `(0, -(N-1))`, `(-(N-1), 0)`, `(-(N-1), N-1)`,
  `(0, N-1)`.

- The **six edges** are the six side segments between consecutive corners,
  **excluding the corners themselves**. A non-corner border cell belongs to the
  one side where exactly one cube coordinate equals `+(N-1)` or `-(N-1)`. A
  corner pins two coordinates at the extreme, which is precisely why corners are
  not part of any edge.

So a **bridge** connects two corner cells, while a **fork** connects three of
the six (corner-free) edge segments. A chain that runs corner-to-corner along
the boundary is a bridge, not a fork, because the corner cells are excluded from
the edges.

## Pie (swap) rule

To offset first-move advantage, the **pie rule** (option, on by default) lets the
second player, on their first turn only, choose the action **swap** instead of
placing: they take over the opening stone as their own colour and hand the move
back. With the option off, no swap is offered.

## Ruleset choices made in this implementation

- **Ring interior is unrestricted:** any non-empty enclosed region counts,
  whatever colour (or emptiness) it contains. This matches Freeling's standard
  rules. Ring detection works by flood-filling the board from the outside
  through every non-ring cell; if any on-board cell cannot be reached from the
  outside, the friendly group encloses it and a ring is formed.
- **Win is checked only for the player who just moved**, against the connected
  group containing the stone they just placed — placing a stone can only create a
  structure for the mover, and only one touching the new stone.
- **No draw by agreement / no resignation** at the engine level; the only
  terminal states are a completed structure or a completely full board.
