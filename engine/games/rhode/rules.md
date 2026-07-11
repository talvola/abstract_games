# Rhode

Luis Bolaños Mures (June 2016). A drawless square-board connection game in
which **diagonal links must be consolidated, and doing so costs a whole
turn** — the designer's "most straightforward" answer to the square-grid
crosscut problem.

## Board and goal

- Played on the points of an initially empty square grid (default 11×11; the
  designer's Zillions version offers 3×3 up to 19×19).
- **Black** owns the **top and bottom** edges, **White** the **left and
  right** edges.
- You win by completing a chain of **orthogonally adjacent** stones of your
  colour touching your two opposite edges. Diagonal adjacency does *not*
  connect.
- Black moves first. **Pie rule**: on White's first turn only, White may play
  `swap` to take over Black's opening instead of placing — the lone stone is
  reflected across the main diagonal and recoloured White (Rhode is symmetric
  under transpose + colour swap, so White inherits a position exactly as
  strong as Black's was).

## Definitions

- A **weak pair** is a set of two like-coloured, diagonally adjacent stones
  such that there is **no like-coloured stone orthogonally adjacent to both**
  (the two points adjacent to both are the other two corners of their 2×2
  square).
- A **crosscut** is a 2×2 pattern of stones consisting of two diagonally
  adjacent black stones and two diagonally adjacent white stones.

## Playing a turn

1. **If you have any friendly weak pairs on the board**, you must place a
   stone of your colour on an **empty point orthogonally adjacent to both
   stones of one of those pairs** (consolidating the diagonal link). If there
   are no friendly weak pairs, you place a stone of your colour on **any
   empty point**.
2. **After placing**, you must **remove all *other* friendly stones that are
   part of any crosscuts**. The stone you just placed is never removed;
   opponent stones are never removed.
3. The winning connection is checked **after** the removal step — a removal
   can break the chain your placement just completed (see below).

## Moves in this implementation

- Placement: click an empty point (when you have weak pairs, only the legal
  consolidation points are offered).
- `swap` (pie rule) appears as a button on White's first turn.

## Interpretations / edge cases (resolved against the designer's Zillions file)

- **Forced placements as a move priority.** The Zillions implementation
  (submission 2501, `Rhode.zrf`) generates the weak-pair consolidations as a
  higher-priority move type (`move-priorities fix-diagonal normal`): when any
  exist, they are the only legal moves; when none generate, any empty point
  is legal. This module mirrors that, including the fallback: if weak pairs
  exist but every consolidation point is occupied, you place freely. (That
  situation is unreachable in real play — see the next point — but the
  fallback matters for analysis positions.)
- **Crosscuts never survive a turn.** Every crosscut created by a placement
  contains the placed stone and exactly one other friendly stone, which the
  removal step deletes — so the board is crosscut-free at the start of every
  turn. Consequently every friendly weak pair always has at least one empty
  consolidation point (if both its 2×2 corners were enemy stones, the square
  would be a crosscut), and the obligation is always satisfiable: no pass
  rule is needed.
- **Win-check timing.** The `.zrf` performs the removals inside the move and
  Zillions tests its win conditions afterwards, so the chain test runs on the
  post-removal board. This is not academic: positions exist (one is anchored
  in `selftest.py`) where a forced consolidation joins your two edges *and*
  creates a crosscut whose removal cuts the new chain — the move does not win.
- **Removal scope.** The `.zrf` only removes the diagonal partners of
  crosscuts through the placed stone; because boards are crosscut-free at
  turn start this equals the prose rule ("all other friendly stones that are
  part of any crosscuts"), which is what this module implements literally.
- **Pie rule.** The BGG announcement states the pie rule ("change sides") for
  both Cation and Rhode; the Zillions file omits it (a Zillions limitation).
  We implement it as the value-preserving single-stone mirror (diagonal
  reflection + recolour), the same convention as this library's Hex and
  Konobi (the latter per its designer's own Zillions file).
- The Zillions file also only *detects* wins on the 3×3–5×5 boards (an
  `absolute-config` enumeration limit); this module checks all sizes.

## Draws / termination

Rhode is drawless: boards are crosscut-free at every turn start, and a
crosscut-free full board always contains exactly one winning chain. Because
the removal step can shrink the board population, this implementation adds
the platform's standard defensive backstop: reaching a hard ply cap of 8×N×N
(or a double pass, possible only from constructed full-board positions) is
scored as an honest draw. Never observed in testing (1,100+ seeded random
playouts, longest game well under a quarter of the cap).

## How Rhode differs from its siblings in this library

All four are Bolaños Mures-style square-board orthogonal-connection games
with black top/bottom vs white left/right edges; the crosscut treatment is
what differs:

- **Cation** (same designer, same announcement thread): crosscuts are
  *allowed* against older stones and resolved by **ko fights** — the opponent
  must lift one of their stones out of the crosscut and replay it. Rhode has
  no relocation and no ko; crosscuts self-destruct via the removal step.
- **Konobi** (same designer, 2012): weak connections are handled by a
  **placement ban** (you may not attach weakly when a clean strong attachment
  exists), and chains connect 8-ways. Rhode instead *forces you to spend
  turns* consolidating weak pairs, and only orthogonal adjacency connects.
- **Flipway** (same designer, 2020): 2×2 **multi-stone drops** plus a **flip**
  action that converts the enemy pair of a crosscut. Rhode places single
  stones and removes its own crosscut stones.
- **Crossway** (Mark Steere, 2007): connection is 8-way and the crosscut
  pattern is simply an **illegal placement**. Rhode permits the placement and
  makes you pay in material.

Rhode's signature: **forced weak-pair completion + self-removal in crosscuts**.

## Status note

In April 2026 the designer wrote that "Rhode has been superseded by Akimbo
and Okimba". This package deliberately implements the original 2016 Rhode
ruleset, which is identical in the BGG thread and the Zillions submission.

Sources: [New games: Cation and Rhode (BGG)](https://boardgamegeek.com/thread/1593043);
Zillions of Games submission 2501 ("Rhode", 2016-06-26, updated 2016-07-09).
