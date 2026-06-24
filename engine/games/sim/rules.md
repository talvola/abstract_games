# Sim

**Sim** (Gustavus Simmons, 1969) is a two-player *misère* graph game played on the
complete graph **K6** — 6 dots (vertices) with a line (edge) between every pair, so
**15 edges** in all. The 6 vertices are laid out as a regular hexagon.

## How to play

- Two players: **Red** (player 1) and **Blue** (player 2). Red moves first.
- On your turn, **color one uncolored edge** with your own colour.
- Play alternates until the game ends.

## How to win (avoidance / misère)

You are trying **not** to build a triangle in your own colour.

- A **triangle** is three edges of one colour joining some 3 of the 6 vertices.
- The moment you color an edge that **completes a triangle of your own colour**,
  **you LOSE** — and your opponent wins.
- You only ever color your *own* edges, so you can only ever be made to lose by a
  triangle in *your* colour (never the opponent's).

## No draws — ever

By **Ramsey's theorem**, the Ramsey number R(3,3) = 6: *any* two-coloring of the
edges of K6 must contain a monochromatic triangle. So the game can **never end in a
draw** — a decisive result always arrives within at most **15 plies** (one player is
forced to complete a same-colour triangle). With perfect play, the **second player
(Blue) wins**.

## Move encoding

Each edge is a clickable bar between two vertices. A move is the edge id
`"e{i}-{j}"` for vertices i < j (vertices numbered 0–5), e.g. `e0-3`, `e2-5`. Click
an uncolored edge to color it in your colour.
