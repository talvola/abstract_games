# Kalah

Kalah is the Mancala most people have played — the commercial two-row sowing game.
This package implements the standard **Kalah(6,4)**: six pits a side, four seeds in
each. These are the rules **as implemented** here.

## The board

Each player has a row of **six pits** and a **store** (the larger hollow to their
right). South is Player 1 (bottom row), North is Player 2 (top row). South moves
first. The stores start empty; the 48 seeds start four to a pit.

## Sowing

On your turn, scoop up **all** the seeds from one of **your own** non-empty pits
and drop them one at a time into each hollow that follows, going
**counter-clockwise** — including **your own store**, but **skipping your
opponent's store**.

## The two bonus rules

- **Land the last seed in your own store** → you **take another turn**.
- **Land the last seed in one of your own pits that was empty**, *and* the
  opposite pit (your opponent's, directly across) holds seeds → you **capture**:
  that last seed *and* all the seeds in the opposite pit go to your store, leaving
  both pits empty. (No capture if the opposite pit is empty, or if the pit you
  landed in already had seeds.)

## Ending and winning

The game ends as soon as **one player's six pits are all empty**. The other player
then **sweeps the seeds remaining in their own pits into their store**. Whoever has
**more seeds in their store** wins; 24–24 is a draw.

## Notation

A move names the pit sown, e.g. `South c (4)` — South's third pit, holding 4 seeds.
Each pit shows its seed count; the two store totals are shown in the caption
("South 10 — North 9").
