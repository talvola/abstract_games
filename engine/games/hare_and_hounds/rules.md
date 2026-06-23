# Hare and Hounds

Also known as the **Soldier's Game**, **Le Jeu Militaire** and the **French
Military Game**. A classic asymmetric *hunt*: three Hounds try to corner a lone
Hare on the standard 11-point board.

- **Seat 0 — Hounds** (three pieces).
- **Seat 1 — Hare** (one piece).

The **Hounds move first**, then play alternates.

## The board (11 points)

A 3x3 grid of points with one extra point off the **left-middle** (the left
apex) and one off the **right-middle** (the right apex) — a horizontally
stretched cross / two-ended spearhead. Coordinates are `x,y` (x increases to the
right, y increases downward):

```
         1,0   2,0   3,0
    0,1  1,1   2,1   3,1  4,1
         1,2   2,2   3,2
```

### Lines (how points connect)

- **Three horizontal rows.** The long middle row runs through both apexes:
  `0,1 – 1,1 – 2,1 – 3,1 – 4,1`. The top row is `1,0 – 2,0 – 3,0` and the bottom
  row is `1,2 – 2,2 – 3,2`.
- **Three vertical columns:** `x,0 – x,1 – x,2` for `x = 1, 2, 3`.
- **The central X:** the centre point `2,1` is joined by a diagonal to each of
  the four grid corners (`1,0`, `3,0`, `1,2`, `3,2`).

There are **no diagonals in the outer cells** — only the four through the
centre. This is the standard board used for the Soldier's Game / French Military
Game (the same graph used by computational sources such as Berkeley's
GamesCrafters and Ludii).

## Setup

- **Hounds** start on the three left-most grid points: `1,0`, `1,1`, `1,2` (the
  closed left end).
- **Hare** starts at the **right apex** `4,1` (the open right end).

## Movement

A piece moves **one step along a board line** to an adjacent **empty** point.
There are no captures.

- **Hounds** may move **forward** (toward the Hare's / open right end — to a
  point with greater `x`) or **sideways** (vertically, same `x`). They may
  **never move back toward their own starting (left) end** (no point with a
  smaller `x`). This *no-retreat* rule is what makes the hunt finite.
- **The Hare** may move **one step along any line in any direction**, including
  backward.

## Winning

- **The Hounds win** by **trapping** the Hare so that, on the Hare's turn, it
  has **no legal move** (every line out of its point leads to an occupied or
  off-board position).
- **The Hare wins** by **reaching the Hounds' starting end** — the **left apex
  `0,1`** — i.e. slipping past all the Hounds.
- **The Hare also wins by the stalling rule:** if the Hounds make **10
  consecutive non-advancing Hound moves** (sideways/vertical shuffles — a Hound
  move that does not increase its `x`), they are deemed to be stalling and the
  Hare wins. The count is over **consecutive Hound moves across the turn
  alternation**: the Hare's intervening moves do **not** reset it. Any
  **advancing** (forward, `x`-increasing) Hound move resets the counter to 0.

A defensive edge case: if the **Hounds** are ever themselves left with **no
legal move**, the **Hare wins** (the Hounds have failed). With perfect play the
Hounds win; the Hare's chances rest on a Hound mistake.

## Implementation notes / ruleset choices

- **Board & lines.** Sources agree the board is the 11-point two-ended
  spearhead with orthogonal lines plus diagonals through the centre, but few
  spell out the *exact* diagonal set. This package implements the most common
  documented version: the four diagonals form a single **central X** (corners to
  centre), with no diagonals in the outer cells. This matches the boards shown by
  Cyningstan, Clubhouse Games, bead.game and the common printable models.
- **Turn order.** Sources differ on who moves first; this package has the
  **Hounds move first** (the traditional "hunter moves, then prey" order for the
  Soldier's Game). The opening player does not change the theory of the game.
- **Stalling rule.** Implemented as the widely-cited rule: **10 consecutive
  non-advancing Hound moves** = a Hare win. "Advancing" means a Hound increased
  its `x` (moved toward the open right / Hare's end — the same forward direction
  the no-retreat rule uses); a move that keeps `x` the same is a non-advancing
  shuffle and increments the counter. The counter tracks **consecutive Hound
  moves** and is **not** reset by the Hare's intervening turns, so it genuinely
  accumulates in normal alternating play. (Some sources instead use position
  repetition; the 10-move count is the most commonly stated version and serves
  the same anti-dawdle purpose.)
- **Escape goal.** The Hare's "past the hounds" win is concretised as reaching
  the left apex `0,1`, the single point at the Hounds' starting end. Because the
  Hounds can never retreat, once the Hare is behind every Hound it can always
  reach this point unobstructed.
- A hard ply cap (400) guards random self-play from looping; it should never bind
  in real play and, if reached, is scored for the Hare (the Hounds dawdled).
