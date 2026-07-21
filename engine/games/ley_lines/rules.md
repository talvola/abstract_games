# Ley Lines

*Eric Solomon, 2019. Published in* Abstract Games *magazine, Issue 17 (Autumn
2019), pp. 43–45. Rules below are as implemented in this package.*

Ley Lines is a route-finding capture game. White "Go stones" are scattered at
random across a large hex field; each player drives a single ring around the
board and, whenever the ring surrounds a stone, jumps along a straight **ley
line** to gobble up the stones on it. The player who captures the most stones —
counting completed lines double — wins.

## Board and setup

- The board is a **rectangular 18×18 array of pointy-top hexagons**. Cells are
  `"c,r"` (column 0–17, row 0–17); odd rows are shifted right by half a hex.
- The board is divided into nine **6×6 zones** (a 3×3 arrangement), shown as
  alternating blue/green tints. Zones matter **only** at setup.
- **Deal (random, stored in state).** White stones are scattered so that every
  zone holds **at least six** stones. The total is a game option — **54**
  (default, the recommended minimum), 63 (the magazine's worked example) or 72.
  More stones make a longer game. The deal is done once in `initial_state`; the
  layout is stored, so there is no chance node during play.
- **Ring placement.** After the deal each player places their ring on any
  **vacant** cell (no stone, no ring). Placement order is Player 2 first, then
  Player 1; **the last player to place moves first**, so Player 1 takes the
  first movement turn. (This mirrors the article: "The LAST player to place his
  ring takes the FIRST movement turn.")

## Movement — two kinds of turn

On your turn you make **exactly one** of:

1. **Single step.** Move your ring one hex in any of the six directions to an
   adjacent cell. You may not land on the opponent's ring, but you *may* step
   onto a cell holding a stone (your ring then "surrounds" it). **No stone is
   captured by a step.** Stepping onto a stone is how you set up a jump — and,
   crucially, it is the *preceding single step* that lets a completed line score
   double (see scoring).

2. **Jump.** Only if your ring currently surrounds a stone (of either colour).
   Jump along one of the three **principal directions** (the two board diagonals
   or the horizontal row) to the **next stone** along that direction, flying
   over empty cells. After the first jump you may keep jumping — but only in the
   **same direction**, and never onto the opponent's ring. Every **white** stone
   your ring starts on or reaches is **captured** and replaced by a **black**
   stone (black stones you pass onto are not re-captured).

3. **Pass.** You may always pass. When **both players pass in succession** the
   game ends.

A ring on a stone renders as a ring around a small `○` (white stone) or `●`
(black stone). The jump-vs-step choice for a one-hop move is disambiguated in
the move string (jumps carry a `=J` suffix; the UI labels it "Jump (capture)").

## Scoring

Captured stones go into two piles:

- **Pile 1 — complete lines (count double).** A single jumping turn that visits
  **every** stone on a principal line, with **no black stone visited**, *and*
  whose **preceding move was a single step**. Each such stone counts as two.
- **Pile 2 — everything else.** Stones "mopped up" from partially-traversed
  lines, or captured when the preceding move was not a single step.

When the game ends, each player's score is `pile1 × 2 + pile2`. **Highest score
wins; an equal score is an honest draw.**

### Worked example (the magazine's "Sample position")

Player 1 steps to **a**, Player 2 steps to **f**. Player 1 then jumps
**a→b→c→d→e**, capturing all 5 stones on that line — a complete line preceded by
a step, so **pile 1 = 5, scoring 10**. Player 2 jumps **f→g→h**; he *could* have
continued to **i** to take all 4 stones in that line, but stopping short leaves
a partial line: **pile 2 = 3**. (Reconstructed exactly in `selftest.py`.)

## Implementation notes (interpretations of an under-specified ruleset)

The magazine text leaves a few points to the reader; this package resolves them
as follows.

- **"A line"** for the complete-line bonus is the **entire principal line** — in
  cube coordinates, all stones sharing the invariant coordinate (same row, or
  the same value on one of the two diagonals). To score pile 1 the jump must
  visit *all* of them, which means starting on the stone at one end of the line.
- **Jumps fly over empty cells** to the next stone ("jump directly to the next
  stone… along one of the principal directions").
- **Black stones may be landed on** mid-chain (the next stone "of any colour"),
  but visiting one disqualifies the complete-line bonus for that turn.
- **Stepping onto a stone is legal and does not capture**; it is the standard way
  to reach a line's end before sweeping it.
- **Vacant** (for ring placement) means a cell with no stone and no ring.
- **Termination backstop.** Beyond the double-pass end, a hard ply cap (1000)
  forces the game to a scored finish so random/exhaustive play always
  terminates.

Players: the designer allows any number "but not recommended for four or more";
this package implements the **2-player** game (as in the worked example).
