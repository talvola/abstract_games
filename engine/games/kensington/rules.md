# Kensington

**Kensington**, by Brian Taylor & Peter Forbes (1979), is a two-player abstract
game named after the mosaic pavement in London's Kensington Gardens. It is played
on the **vertices** of a *rhombitrihexagonal* (3.4.6.4) tessellation.

## The board

Seven regular hexagons — **3 white** running down the vertical middle, **2 red**
on one side and **2 blue** on the other — joined by **30 squares** and
**24 triangles**, meeting at **72 vertices** (the points where counters live).
The lines of the tiling are the moves: two vertices are *adjacent* when a single
line segment joins them.

Players are **Red** and **Blue**, each with **15 counters**.

## Phase 1 — Placement

Players alternate placing one counter on any empty vertex until **both** have
placed all 15 counters. **Red places first.** (Placing *second* is widely held to
be a small edge — the second player makes the last, un-counterable placement,
balanced by the first player moving first in Phase 2.)

## Phase 2 — Movement

Once all 30 counters are on the board, players alternate **sliding one of their
own counters along a line to an adjacent empty vertex**. No vertex ever holds
more than one counter.

If the player to move has **no legal slide**, their opponent keeps moving until
the blocked player can move again (or the game ends).

## Mills — completing triangles and squares

Whenever your move (a placement **or** a slide) gives you **all the vertices of a
small face**, you earn a *relocation*:

- complete a **triangle** (3 vertices) → **relocate 1 enemy counter** to any
  vacant vertex;
- complete a **square** (4 vertices) → **relocate 2 enemy counters**.

You may relocate **at most two** enemy counters in a single turn, even if your
move completes several faces at once (e.g. a triangle *and* a square still gives
only two). A relocation moves an enemy counter to any empty vertex you choose —
the classic use is to build a "jail" far from the action.

Mills apply in **both** phases.

## How to win

You win the instant you **occupy all six vertices of a hexagon you are allowed to
claim**:

- **any white hexagon**, or
- **a hexagon of your own colour** (Red → the red hexagons, Blue → the blue ones).

A win can happen during placement or during movement.

## This implementation — moves & notation

- **Placement:** click an empty vertex — the move is its id, e.g. `v17`.
- **Slide:** click your counter, then an empty adjacent vertex — `from>to`,
  e.g. `v17>v25`.
- **Relocation:** after a move that completes a mill, the *same player* gets one
  follow-up turn per earned relocation; click the enemy counter, then any empty
  vertex — encoded `from>to` as well (the engine knows it is a relocation).

## Interpretations & house rules (as implemented)

- A mill triggers only when the **just-played** vertex *newly completes* a face
  the mover fully owns; standing in a face you already held does not re-trigger.
- Relocation targets are **any** vacant vertex (the enemy counter is *moved*, not
  removed — Kensington keeps all 30 counters on the board the whole game).
- **Termination:** the movement phase could shuffle forever, so after
  **60 movement plies with no placement and no mill** the game is a **draw**; a
  position in which neither side can slide is also a draw. (Documented cap — the
  base game has no formal draw rule.)
- Win is checked for the mover first; in the rare case a forced relocation hands
  the *opponent* a completed hexagon, the opponent wins.

Official rules summary: see the linked Wikipedia article.
