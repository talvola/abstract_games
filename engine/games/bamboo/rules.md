# Bamboo

**Mark Steere, March 2021.** Two players, Red and Blue, on an initially empty
hexagon of hexagons. Official rule sheet:
[marksteeregames.com/Bamboo_rules.pdf](https://marksteeregames.com/Bamboo_rules.pdf)
(a four-sentence ruleset — everything below is those four sentences plus the
two figures that go with them). The sheet has **never been revised**: the live
PDF is byte-identical to every Wayback capture from May 2021 to November 2025
(one SHA-1 across all seven snapshots).

## Play

- **Red moves first.** On your turn you place **one stone of your own colour on
  any empty cell**. Stones are never moved, captured or removed.
- **Passing is not allowed.**
- A **group** is one or more interconnected like-coloured stones (connected
  through the six hex adjacencies).

## The one restriction

> **A player's group can't contain more stones than the number of groups he has.**

This is a property of the **position after your placement**, applied to **all of
your own groups** — the opponent's groups never matter. Writing `g` for your
number of groups after the placement, *every* one of your groups must have size
at most `g`.

A placement can do two things at once: it grows the group it joins, and — when
it touches two or more of your groups — it **merges** them, which *lowers* your
group count. Both effects are taken into account.

For example, suppose your stones form groups of sizes **4, 1, 1, 1** — four
groups, largest 4, which is legal. Now you place a stone touching two of the
singletons. Those two plus the new stone become one group of 3, and you are left
with sizes **4, 3, 1** in **three** groups. Your 4-group is now bigger than your
group count, so **that placement is illegal** — even though the group your stone
actually joined is only 3 stones and would have been fine on its own.

Consequences worth knowing:

- A stone placed with **no friendly neighbour** is always legal: it adds a new
  group of one, so the count goes up and no group grows.
- Therefore the **first move is always legal** (one group of one stone, group
  count one), and a player is only ever stuck when every empty cell touches at
  least one of his own stones *and* every such placement breaks the rule.
- Because every legal position already satisfies the rule and every legal move
  preserves it, "a player's group can't contain more stones than the number of
  groups he has" is a true **invariant** of the whole game.

## Object

**The last player to place a stone wins.** Equivalently: passing being illegal,
the player who has no legal placement on his turn **loses** immediately.

The board is usually **not full** when this happens — the losing player is
simply walled in by his own shape.

**There are no draws.** The empty board always admits a move, so at least one
stone is always placed and "the last player to place a stone" is always defined.

## Board

A hexagon of hexagons ("hexhex") of side *n*, i.e. `3n² − 3n + 1` cells.

| Side | Cells | Note |
|---|---|---|
| 4 | 37 | quick game |
| **5** | **61** | **default — the size both rule-sheet figures use** |
| 6 | 91 | AbstractPlay's `hex6` variant |
| 7 | 127 | AbstractPlay's default |

The rule sheet says only "hexagonal grid" and never names a size; both of its
figures are drawn on a side-5 board (61 cells, rows of 5·6·7·8·9·8·7·6·5), which
is the only board size the author himself depicts, so that is the default here.

Cells are named the way AbstractPlay names the same board: a row letter counted
**up** from the bottom row, then the cell's 1-based index from the left within
that row, so `a1` is the bottom-left cell. Move notation in this engine is the
axial cell id `"q,r"`; the move log shows the algebraic name.

## Ruleset choices made in this implementation

**1. The restriction is a whole-position invariant on the mover, not a test of
the placed stone's group only — and the rule sheet's Figure 2 proves it.**

This is the only interpretive question the game has, and it is decisive. The
sentence "a player's group can't contain more stones than the number of groups
he has" quantifies over *a player's group*, i.e. all of them; the Fig. 1 caption
adds that Red "can merge his groups, and so reduce his number of groups, but
only in a way that doesn't violate the rules". The two readings differ exactly
when a placement merges groups without joining the largest one.

Both figures mark **all** available placements in green, which makes them exact
oracles. Transcribing them from the PDF's vector artwork (fill colour + centre
of all 138 disc paths — 49 red, 48 blue, 25 empty, 16 green markers):

| | board | stones | Red groups (largest) | Blue groups (largest) | printed green |
|---|---|---|---|---|---|
| Fig. 1, Red to move | side 5 | 46 | 9 (5) | 10 (6) | **12** cells |
| Fig. 2, Blue to move | side 5 | 51 | 7 (7) | **9 (9)** | **4** cells |

Six candidate readings, scored against the two printed green sets:

| Reading | Fig. 1 (12 printed) | Fig. 2 (4 printed) |
|---|---|---|
| **all groups, position AFTER the placement** | **12 ✓** | **4 ✓** |
| only the group the new stone joins, after | 12 ✓ | 8 ✗ |
| all groups, but against the group count *before* | 14 ✗ | 8 ✗ |
| placed group only, against the count *before* | 14 ✗ | 8 ✗ |
| group *sizes* before, count after | 15 ✗ | 4 ✓ |
| merging outright forbidden | 5 ✗ | 4 ✓ |

Only one reading survives both figures. Fig. 1 rules out the "before"
variants; Fig. 2 rules out the placed-group-only one — in Fig. 2 Blue is exactly
at the limit (largest group 9, group count 9), so *any* merge drops his count
below his own largest group.

This package implements the all-groups reading and `selftest.py` asserts both
figures cell-for-cell, together with their preconditions (board size, stone
counts, per-seat group counts and largest groups) so a mis-transcription cannot
pass silently.

**AbstractPlay's `gameslib` implements the placed-group-only reading** (its
`canPlaceAt` returns `found.length <= conn.length`, testing only the group
containing the new stone) and therefore allows placements Figure 2 shows as
unavailable. We follow the rule sheet.

**2. End of game.** The sheet states the object ("the last player to place a
stone wins") and that passing is forbidden, but never says the game ends when a
player is stuck — it follows, since a player with no legal placement can neither
place nor pass. `gameslib` reads it the same way. The loser is the player to
move; the winner is the previous player. The board is typically not full.

**3. No ply cap and no repetition rule** — neither is needed. Every move places
exactly one stone and nothing is ever removed, so the number of empty cells
strictly decreases and the game cannot last more than `3n² − 3n + 1` plies (the
number of cells; the bound is computed from the board, not pinned). In practice
games end well short of it: random play on the default board averages ~53 of 61
plies, and across 520 random games on all four sizes the board was **never**
full at the end (the exhaustively solved side-2 board likewise never reaches its
7th cell).

**4. No draw is possible**, so `returns` is always ±1 — no fabricated tiebreak
and no honest-draw branch is reachable. (An honest draw would be the right
answer if one existed; the empty board always having a legal move is what rules
it out.)

**5. Board sizes** are an option rather than separate games; 5 is the default
for the reason given above.

## Correctness anchors

- **Both rule-sheet figures**, reproduced exactly (12 and 4 cells), with their
  preconditions asserted.
- **Exhaustive solve of the smallest hexhex** (side 2, 7 cells): 175 reachable
  positions, 29 terminal, longest game 6 plies, and the game is a **second-player
  win** with perfect play. This simultaneously proves cycle-freedom (the ply
  count equals the stone count everywhere), drawlessness, and a game value.
  A separate one-time bitboard solve of **side 3** (19 cells) — 2,409,556
  distinct solved positions — also makes it a **second-player win**. (Nothing is
  claimed about the larger boards; those are far out of reach.)
- **An independent brute-force move generator** in `selftest.py` (recompute
  every group from scratch after every hypothetical placement) checked against
  the O(cells) incremental generator on every position of whole random games at
  every board size.
- **Differential vs AbstractPlay `gameslib`** (oracle only). Its board graph is
  edge-for-edge identical to ours (91 cells / 240 edges at side 6, 127 / 342 at
  side 7), and emulating its placed-group-only reading reproduces its move list
  **exactly on all 3,157 plies of 32 games** across both board sizes, both rule
  readings and both seats — which isolates the divergence above to that single
  rule and nothing else. Two deliberately wrong adjacency maps were run as
  controls and both diverged, as required.
  The divergence is not academic: on **474 of those 3,157 plies (15%)** gameslib
  offers placements the rule sheet's figures mark as unavailable (2,407 extra
  cells in total).

## Bot evaluation

The package ships a `heuristic`: the **mobility balance**,
`tanh(0.08 × (my legal placements − opponent's))`, returned as a per-seat list.
It is the goal restated — the loser is exactly the player who runs out of
placements first.

It was measured through `MCTSBot`, the actual consumer, **not** by 1-ply greedy
play. The eval only ever fires when a rollout is truncated, so how much it is
worth depends entirely on how often that happens:

| Measurement | Result |
|---|---|
| `max_rollout=4` (cutoff forced), side 4, 150 iterations, 40 games | eval **37/40 = 0.925 ± 0.082** vs no eval |
| same, no-eval-vs-no-eval control | 25/40 = 0.625 ± 0.150 |
| `max_rollout=50` (the shipped default), side 5, 120 iterations, 20 games | 11/20 = 0.550 ± 0.218 — **indistinguishable** |
| how often the default 50-ply cutoff fires (6 opening moves × 100 iterations) | side 4: **0%**, side 5: **32%**, side 6: **100%**, side 7: **100%** |

Read together: on the small boards a Bamboo game is *shorter* than the default
rollout, so MCTS reaches real terminals and no eval is needed (and none is used
— hence the flat 0.550). On sides 6 and 7 every rollout is truncated, so without
a `heuristic` the bot would score **every** rollout as a draw and have no signal
at all; the forced-cutoff match measures exactly that regime and the eval wins
0.925 there, against a 0.625 same-vs-same control (that control is consistent
with 0.5 at this sample size; the eval's margin over it is z ≈ 3.4, p < 0.001).
The heuristic was consulted 74,315 times in the forced-cutoff match, so the
measurement is not vacuous. A "group slack" alternative
(`groups − largest group`) scored identically (37/40); mobility was kept as the
more direct statement of the goal.

`selftest.py` pins the eval's direction and scale to a measured value on a
constructed position (mobility 51 vs 41 → +0.6640 for Red), checks seat symmetry
and zero-sum, and drives `MCTSBot` with `max_rollout=4` so the per-seat list
shape is exercised on the path that would otherwise hide a malformed eval.

## Strategy note

Every stone you add to an existing group has to be "paid for" by owning at least
that many groups, so Bamboo is a game of spending and hoarding groups. Merging
is sometimes forced and always expensive: it converts several cheap groups into
one expensive one and lowers the ceiling for every other group you own. Late in
the game the board fills with cells that all touch your own stones, and the
player who ran his group count down first is the one who runs out of moves.
