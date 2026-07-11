# Zola

Mark Steere, February 2021. Two players: **Red** (moves first) and **Blue**.
Official rules: [marksteeregames.com/Zola.pdf](https://www.marksteeregames.com/Zola.pdf).

## Board & setup

A 6x6 checkerboard (8x8 and 10x10 available as options), initially **filled
completely** with a checkered pattern of red and blue checkers (the rule
sheet's Figure 1) — 18 checkers each on 6x6.

## Moving

Players take turns moving **one** of their own checkers, starting with Red.
**If you have a move available, you must make one.** If you have no moves
available, you must sit the game out (press **pass** — it is your only legal
move) and wait until you do have a move available.

All moves are measured against the **center point of the board** (the point
where the four central squares meet; squares are compared by straight-line
distance from their centers to that point).

- **Non-capturing move** — a king-like step to an adjacent (horizontal,
  vertical, or diagonal) **unoccupied** square that is **strictly farther**
  from the center than the starting square.
- **Capturing move** — a queen-like move along a straight (horizontal,
  vertical, or diagonal) line of **zero or more unoccupied** squares ending on
  an **enemy** checker, which is removed and replaced by the capturing
  checker. A capture must land **at the same distance or closer** to the
  center than the starting square.

Captures are **never compulsory** — any legal move may be chosen.

## Object of the game

**Capture all enemy checkers.**

## Notes

- On the 6x6 board the squares fall into exactly 6 "levels" of distance from
  the center (the rule sheet's sidebar): quiet moves climb strictly outward
  through the levels; captures may stay on the same level or dive inward.
- **Draws cannot occur** (per the rule sheet): captures are finite, quiet
  moves strictly increase the total outward spread (so play can never cycle),
  and at least one of the two players always has a move available. The
  implementation carries an engine-mandated backstop that scores a position
  where *neither* player can move as a draw; no such position is believed to
  exist (an exhaustive small-position search found none).
