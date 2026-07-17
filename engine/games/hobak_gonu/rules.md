# Hobak Gonu (호박고누, "pumpkin gonu")

A traditional Korean two-player blockade game on an 11-point "pumpkin" board.
No captures: you win by leaving your opponent with no legal move.

## Board

Eleven points, fourteen lines: a circle with an internal cross (four ring
points + centre), and a three-point **home row** for each player, joined to
the circle by a short neck at the row's middle point.

```
    tL ---- tM ---- tR        White's home row
             |
             n                 (circle)
           / | \
         w - c - e
           \ | /
             s
             |
    bL ---- bM ---- bR        Black's home row
```

The four "diagonals" are the circle arcs `n-w`, `n-e`, `s-w`, `s-e`; the
centre `c` connects to all four ring points by the cross. Each home row has
its two internal lines (`L-M`, `M-R`), and each middle (`bM`/`tM`) connects
to the nearest ring point (`s`/`n`).

## Play

- Each player has **3 pieces**, starting on their home row. Black (bottom)
  moves first.
- A move slides one of your pieces along a line to an **adjacent empty
  point**. No captures, no jumping.
- **Home rows are one-way funnels:**
  - No move may ever end on a home-row **endpoint** (`bL`/`bR`/`tL`/`tR`)
    — those four points can only be left, never entered.
  - A home-row **middle** may only be entered from its own row's endpoints
    (the funnel move `L>M` / `R>M`). In particular, a piece that has
    reached the circle can never step back into its own home row.
  - Consequence (this is the rule most casual descriptions miss, but the
    traditional win diagrams require it): a piece sitting on a home row
    whose exit is corked counts as **blocked**, even if the empty endpoint
    beside it looks free.
- **The five circle points are free**: move to any adjacent empty circle
  point.
- **Opponent's home row** — the game option *"Opponent's home row"*:
  - **Closed** (default): your pieces may never enter the opponent's home
    row at all.
  - **One-way trap**: a piece may step from the circle onto the
    *opponent's* home middle, and may then shuffle within the opponent's
    row (middle and endpoints), but can never leave it. Invading corks the
    opponent's exit forever at the cost of the piece's freedom.
- **Win**: if the player to move has no legal move, they lose (blockade).
- **Draw**: the first repetition of a position (same occupancy, same player
  to move) ends the game immediately as a draw. (A 200-ply hard cap is a
  conformance backstop; the solved max forced-win length is 22 plies, so it
  never bites under sensible play.)

## Solved game value

The full game graph was solved (retrograde win/loss analysis; cycle-bound
positions are draws, matching the repetition rule; re-run by this package's
`selftest.py` in seconds):

- **Closed** (default): 2,278 reachable positions, 6,518 move edges —
  1,062 wins / 726 losses (for the side to move) / 490 cycle-bound draws.
  **The starting position is a DRAW**; max forced-win depth 20 plies.
- **Trap**: 15,972 reachable positions, 52,878 move edges — 1,608 wins /
  1,134 losses / 13,230 draws. **The starting position is a DRAW**; max
  forced-win depth 22 plies.

So under perfect play neither side can force a blockade in either variant —
which agrees with the Korean folk literature (namu.wiki: like umul-gonu,
"no winning method exists unless the opponent blunders; without mistakes
the game continues forever"). Wins come from real blunders: the fastest
possible blockade is 13 plies (closed) / 8 plies (trap — a mutual-invasion
race).

## Sources & interpretations

- Board graph: Ludii's **"Ho-Bag Gonu.lud"** (ludii.games, game id 573) —
  11 vertices / 14 edges, decoded from the generator source and confirmed
  against the board figures of Ludii's cited source (nol2i.com, archived).
- Rules: consensus of **nol2i.com** (호박고누 놀이 방법, archived; Ludii's
  cited source), **namu.wiki 호박고누**, and D. Flank's English writeup
  (lflank.wordpress.com, 2023). BGG lists the game as **Pat Gonu**
  (id 411418, "often referred to as Hobak Gonu"), whose rules sheet agrees.
- Interpretation points (documented because sources conflict):
  1. **Endpoints exit-only / funnel homes**: Ludii's implementation allows
     free sliding within a home row, but nol2i's own winning diagram (its
     figure 2) is only a valid blockade if the home middle piece cannot
     slide to the empty endpoints, and namu.wiki's footnote states
     explicitly that pieces on the start line with an open start-line point
     beside them still count as surrounded. lflank states the endpoint
     one-way rule directly. We implement the funnel (endpoints feed the
     middle, nothing re-enters an endpoint); it is fully positional, so no
     move history is needed.
  2. **Opponent's home row**: nol2i rule ④ ("a piece that has entered the
     other's home cannot come back out") and Ludii allow one-way invasion;
     namu.wiki and lflank forbid entering at all. Both are attested, so it
     is a game option; the majority/consensus **closed** is the default.
     Both are solved draws.
  3. First player is not specified in the sources; Black (bottom) moves
     first here.
- The repetition-draw rule is our termination backstop (the folk game
  simply "continues forever" — namu.wiki); it is consistent with the
  cycle-as-draw semantics of the solve.
