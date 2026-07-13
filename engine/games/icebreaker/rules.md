# Icebreaker

By **Mark Steere** (November 2021). A two-player capture game on a hexagonal
grid. Official one-page rules: <https://marksteeregames.com/Icebreaker.pdf>.

*Rules as implemented in this package.*

## Board and setup

- A hexagonal (**hexhex**) board. Default **size 5** — 61 cells, drawn as a
  hexagon 5 cells to a side. Any size works; a `size` option offers 4, 5, 6.
- **Six ships** start at the six corners of the board, alternating colour
  around the ring: **3 red** and **3 black** (Fig. 1). Red takes the top-left,
  right, and bottom-left corners; Black takes the top-right, bottom-right, and
  left corners.
- **Every other cell holds a white iceberg.** On size 5 that is 55 icebergs.

## Play

- **Red moves first**, then players alternate. **Passing is not allowed.**
- **Move:** move one of your ships to an **adjacent** cell that does **not**
  contain another ship. Moving onto a cell that contains an iceberg
  **captures** it — the iceberg is removed and your score increases by 1.

## Move direction (the key rule)

- The ship you move **must move closer to its own closest iceberg.**
- **Distance** is the number of cells along the **shortest path of cells**
  connecting the ship to an iceberg, **going around the other ships.** In this
  implementation it is a breadth-first search over on-board cells: empty cells
  and icebergs are passable, the other five ships are blockers, and any iceberg
  is a valid endpoint (so the nearest one determines the distance).
- A legal destination for a chosen ship is an adjacent, non-ship cell whose own
  distance-to-nearest-iceberg is **exactly one less** than the ship's current
  distance.
- Consequently, **if a ship has an iceberg adjacent to it, its only legal
  destinations are icebergs** — "you must capture one of them." When several
  shortest paths (or several equally-near icebergs) exist, every step that
  reduces the distance is legal, and you may choose.
- A ship that cannot reach any iceberg (walled off by other ships) has no legal
  moves; you must move a different ship.

## Object of the game

- **Capture the majority of the icebergs.** In general that is
  `floor(total / 2) + 1`. On the size-5 board there are 55 icebergs, so
  **28 captures win** (size 4: 16 of 31; size 6: 43 of 85).

## Termination and edge cases

- Each non-capturing move strictly reduces the moving ship's distance to its
  nearest iceberg, and captures drain a finite supply of icebergs, so play
  converges. A generous **hard ply-cap draw** is kept purely as a defensive
  backstop.
- **No legal move:** because passing is illegal, if the player to move has no
  legal move (all of their ships are walled off from every iceberg by the other
  ships) the game ends and is scored by icebergs captured — **more captures
  wins; an equal count is an honest draw.** A genuine tie is never turned into
  a fabricated winner. (This position is rare in practice.)
