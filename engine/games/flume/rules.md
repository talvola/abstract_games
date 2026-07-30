# Flume

**Mark Steere, January 2010.** Two players, no draws, no passing, no captures — you simply
keep adding stones, and a well-placed stone lets you keep adding.

Official rule sheet: [Flume_Go_rules.pdf](https://www.marksteeregames.com/Flume_Go_rules.pdf).
This page describes the rules **as implemented in this package**.

## The board

Flume is played on the *intersections* of an odd-sized square grid whose **outermost ring is
pre-filled with permanent, ownerless green stones** (Fig. 1 of the sheet). The green stones are
never placed, never moved and never owned — but they **count as stones** for everything below.

So a "7×7 Flume board" is a 9×9 grid of points: a green ring of 32 stones around a 7×7 playable
square of 49 points. On real equipment you set it up by filling the outer ring of a Go board;
the default here is a **9×9 Go board ⇒ 7×7 playable**.

```
G G G G G G G G G        G = permanent green stone (never played on)
G . . . . . . . G        . = playable point
G . . . . . . . G
G . . . . . . . G        A playable CORNER point touches 2 green stones.
G . . . x . . . G        A playable EDGE point touches 1.
G . . . . . . . G        An interior point touches none.
G . . . . . . . G
G . . . . . . . G        x = the centre point, banned on Red's first turn
G G G G G G G G G
```

Cell ids are `"c,r"` on the **whole** grid — `0` and `n+1` are the green ring, `1..n` are the
playable points, `r` counts upward from the bottom. The move log names playable points
Go-fashion, `A1`…(columns left→right skipping `I`, rows bottom→top), so `A1` is the bottom-left
playable point.

| Option | Playable points | Full grid | Equipment |
|---|---|---|---|
| 5×5 | 25 | 7×7 | the sheet's Figure 1 board |
| **7×7** (default) | **49** | **9×9** | 9×9 Go board |
| 9×9 | 81 | 11×11 | — |
| 11×11 | 121 | 13×13 | 13×13 Go board |
| 17×17 | 289 | 19×19 | 19×19 Go board |

## Play

**Red (seat 0) moves first.** A **turn** is a run of one or more stone placements.

1. **Stone placement.** Place a stone of your own colour on any unoccupied playable point.
2. **Multiple stone placement.** Count the placed stone's **connections** = its occupied
   *orthogonal* neighbours. **Colour does not matter** — red stones, blue stones and green ring
   stones all count. If the count is **3 or 4**, you must immediately place another stone, still
   on the same turn. And so on. Your turn ends the moment you place a stone that forms **2 or
   fewer** connections.
3. **Anti-mirroring.** On Red's **first turn**, Red may not play the **centre point**.
4. **Pie rule.** Instead of placing, Blue's first turn may be **`swap`** — Blue takes over Red's
   opening stone (it becomes blue) and Red moves again.

Nothing is ever captured or removed, passing is not allowed, and there is always a legal move
while any point is empty.

## Object

The board fills up; **whoever ends with more stones wins.** Because the playable side `n` is odd,
`n²` is odd and the two counts can never be equal — see *No draws* below.

## In this implementation

* **One placement = one ply.** A cascading turn is *not* a single compound move string; the
  engine keeps `current_player` on the same seat and sets a `cont` flag ("you owe another
  stone"), and the caption reads **"must place again (same turn)"**. You click each stone
  separately, exactly as you would on a physical board. The alternative — enumerating whole
  cascades as `"c1,r1>c2,r2>…"` — would make `legal_moves` exponential in the cascade length for
  no gain. All the stones of the current run are marked as "last move" so a long cascade is
  readable at a glance.
* **`swap` renders as an action button**, offered only at the very start of Blue's first turn
  (never in the middle of a cascade) and only once.
* **The game ends the instant it is decided.** As soon as a player holds `(n²+1)/2` stones the
  other player cannot catch up (stones are never removed), so the result is fixed and the
  remaining points are not played out. This is a shortcut, not a rule change: the winner is
  identical to filling the board. The reference implementation uses the same threshold, but only
  tests it at the end of a whole *turn*, so its cascades can overshoot it; this engine stops the
  moment the threshold is crossed, even in the middle of a forced continuation. Because the stop
  means the two counts need **not** add up to `n²`, the end-of-game caption says how many points
  were left unplayed instead of implying the board filled.

## No draws — the proof

Every placement fills exactly one previously-empty playable point and no stone is ever removed, so
played out in full the two armies partition the `n²` playable points: `red + blue = n²`. The
playable side `n` is odd (5, 7, 9, 11, 17 — the only options offered, and the rule sheet says "odd
sized"), so `n²` is odd, so `red ≠ blue`. A tie is arithmetically impossible.

Stopping early does not reopen it: the game only stops when one seat holds `(n²+1)/2` stones, which
is strictly more than the `(n²−1)/2` points that remain for the opponent even if the opponent took
every one of them. So the leader at the stop is the winner of the full playout too. The code
nevertheless returns an honest `0 / 0` draw if the counts were ever exactly equal, rather than
inventing a tiebreak.

## Termination — the proof

There is no repetition rule and none is needed. Each ply places exactly one stone on a
previously-empty point, and **no stone is ever removed, moved or recoloured** (except the
one-shot `swap`, which changes no stone's *position* and can happen at most once). Therefore
`|stones on the board|` strictly increases every *placement*, is bounded by `n²`, so there are at
most `n²` placements — 49 on the default board. The one-shot `swap` is the only ply that places no
stone, so the ply bound is **`n² + 1`** (and that is tight: swapping and then filling the board
completely really does take 50 plies on the default board). So Flume is hard-finite by a trivial
monovariant, with no ply cap, no no-progress rule and no `max_random_plies` override; the selftest
asserts both bounds over random games and pins the `n² + 1` witness.

## Notes / interpretations

* **The green ring is modelled explicitly** as a `(n+2)×(n+2)` board whose perimeter carries
  green pieces, rather than as "a board edge counts as one connection" on an `n×n` board. Both
  give identical connection counts, but the explicit ring (a) keeps move notation and the
  rendered board in one coordinate system, (b) makes the "the edge counts as a stone" rule
  visible to the player exactly as Steere draws it, and (c) is never offered as a move, so a
  click on a ring point does nothing — the ring is inert.
* **"3 or 4 connections"** is a *count*, and 4 is the maximum on a square grid, so the trigger is
  equivalently "3 or more". `0`, `1` and `2` end the turn. Verified against both published
  examples (Fig. 3b = 3, Fig. 3c = 4, Fig. 3d = 1 → turn over; Fig. 4b/c/d = 3, Fig. 4e = 2 →
  turn over).
* **The anti-mirroring ban covers Red's whole first turn**, which is the literal reading. It is
  provably indistinguishable from "Red's first *placement*": on an empty board the largest
  possible connection count is 2 (a corner point's two green neighbours), so **the first turn of
  the game is always exactly one stone** and no cascade can reach the centre on it. The selftest
  asserts that maximum for every board size, so the equivalence cannot silently break.
* **The centre point is unique** because the playable side is odd. The ban lifts from Red's
  second turn onward, and it never applied to Blue.
* **`swap` is implemented as recolour-and-hand-back**: every stone on the board changes owner and
  seat 0 moves next. With exactly one stone on the board (guaranteed — see above) that is
  precisely the physical pie rule.
* **The 2022 revision.** The current sheet is *not* the 2010 original: the Wayback Machine shows
  the PDF's digest changing between 2019 (`J53PIG5E…`, ModDate Oct 2010) and October 2022
  (`AOG363RN…`, ModDate Sep 2022), and the **entire ANTI-MIRRORING RULE paragraph was added** in
  that revision — it is the *only* difference in the text layer, and the two PDFs share their
  2010 `CreationDate`. Everything else is unchanged: re-reading both renderings stone-by-stone
  gives cell-for-cell identical Figures 3 and 4 and the same 7×7-grid board in Figure 1 (the
  pixels shift only because the inserted paragraph reflows the page). This package implements the
  **current** (2022) sheet, i.e. *with* the centre ban. There is no separate `Flume_rules.pdf`
  (it 404s and has no Wayback captures); only the "Go set" edition exists.
* **Board size.** Steere writes only "the odd sized, square board", so the size is a parameter,
  not a rule. Figure 1 (and Figures 3–4) draw a 7×7 grid, i.e. a **5×5 playable** board — that is
  offered as the `5×5` option. The **default is 7×7 playable** (a 9×9 grid): it is the smallest
  standard Go board, matches the reference implementation's default, and 25 points is too few for
  a real game.
* **Category** `Territory`: the game is a board-filling area majority.
* **Anchors.** The two published worked turns (Figures 3 and 4, extracted from the PDF at 400 dpi
  by mapping the coloured stone blobs onto the 7×7 lattice) are replayed placement-by-placement in
  `selftest.py`, asserting each stated connection count and the exact placement that ends the
  turn. Separately, a one-time differential against the AbstractPlay `gameslib` implementation
  (MIT, used as an oracle only) compared opening move sets, **full cascade enumerations** and
  24 complete random games driven from both sides on three board sizes, comparing board state,
  scores, terminal detection and winner. Result: **0 mismatches** over 701 turns / 1,120
  placements, 1,170 enumerated cascades and the opening sets on all three sizes.
  *Oracle bug found:* `gameslib`'s `moves()` implements the centre ban by deleting the
  **hard-coded string `"e5"`**, which is the centre only on its default 9×9 grid. On its `7x7` and
  `11x11` grids `e5` is an ordinary legal point, so the opening list silently **drops a legal
  move and keeps the illegal centre** (`d4` / `f6`) — its own `validateMove`, which computes the
  centre from the board size, rejects that centre. `validateMove` was therefore used as the
  authority for the ban, and the two paths agree with this package everywhere else.
* **Independent QA replication.** A second, adversarial pass re-read the figures off the PDF from
  scratch (they matched cell-for-cell), re-verified the 2022 revision from the Wayback CDX, and ran
  its own differential: a *second implementation written from the rule sheet alone* using the
  opposite board model (no explicit ring — an off-board neighbour simply counts as green) agreed
  with this engine over 350 games / 16k move sets / 585k connection counts, and the `gameslib`
  replay agreed over 24 games, 700 legal-move sets and 29,583 cascade-continuation flags. Playing
  the same games out to a **full** board (the literal rule) never changed the winner in 140 games,
  which is the early stop's proof. Figure 4's stated alternative — "Red could have claimed 6 points
  instead of 4" — replays to exactly six placements, and is now asserted in `selftest.py`.
