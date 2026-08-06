# Quax

**Bill Taylor, 2000** — "**Quadrangular Hex**", squeezed to *Quax*, "which is also
the noise made by the winner as he puts in the killing move!" (the designer's own
gloss). A square-lattice connection game whose signature idea is that a
**diagonal connection costs a whole turn** — and that buying it also **cuts your
opponent's crossing diagonal for good**.

These are the rules **as implemented here**.

## Board and goal

- A square board of *size* × *size* cells (default **11×11**, the size the
  designer suggests; 3, 5, 7, 9, 13 and 15 are also offered).
- **Black** (seat 0) moves first and joins the **top and bottom** edges.
  **White** (seat 1) joins the **left and right** edges. The goal edges are
  tinted in each player's colour; the four corners are tinted in a blend because
  **a corner counts as part of both of its edges**.
- You win the moment a connected chain of your own stones touches both of your
  edges. **Quax cannot be drawn** — see *Termination and drawlessness*.

## What counts as connected

Two stones of a colour are connected when they are

1. **orthogonally adjacent** (this is free — nothing to buy), or
2. **diagonally adjacent with a link of that colour between them**.

A **link** is the physical game's *rhombic tile*. Each 2×2 square of the grid
contains exactly one rhombic cell, and its two diagonals **cross** there, so the
cell can hold only one tile.

## A turn

On your turn you do **exactly one** of:

- **Place a stone** of your colour on any empty cell; or
- **Place a link** of your colour in an empty rhombic cell, joining two
  **diagonally adjacent stones of your own colour**.

There is no passing and nothing is ever removed from the board.

Because a rhombic cell holds one tile, a link is simultaneously a connection and
a permanent cut: once either player links one diagonal of a 2×2 square, **the
crossing diagonal can never be linked by anybody**. That is the whole game — and
it is why spending a turn on a link can be worth it.

## Pie rule (on by default)

The designer's sheet says: *"One player drops one stone on the board. The other
chooses who starts."* On **White's very first turn only**, White may press
**Swap** instead of moving, taking over Black's opening.

Because this engine's seats have fixed goals, the swap is implemented as the
**transpose**: every stone and link is reflected across the main diagonal and
changes owner, and it is then Black's turn again. That is exactly
value-preserving — Quax's move rules are invariant under transposition while the
two goals are *exchanged* by it (proved exhaustively over all 1,937 states of the
3×3 game in `selftest.py`). Recolouring the stone *in place* would **not** be
value-preserving, and this library has had to fix that in two other games.

Set the **Pie rule** option to *Off* for the raw game.

## Notation

- A placement is the cell, `"c,r"` (column, row; row 0 is the **bottom**).
- A link is `"c1,r1>c2,r2"`, always written with the **left-hand (smaller
  column) cell first** — click that stone, then its diagonal partner.
- The move log uses the designer's own notation: `f7` for a placement, `f7-g6`
  for a link, `swap (pie)` for the pie rule. The three published game records on
  his page replay token-for-token through this notation (`selftest.py`).

## Termination and drawlessness

**Termination.** Nothing is ever removed, and every move except the one-off
`swap` adds exactly one stone or one link. Stones are bounded by *size*², and
links by the number of 2×2 squares, (*size*−1)², because each square holds at
most one. So a game lasts at most **1 + size² + (size−1)²** plies (222 at
11×11). There is no ply cap in the code — none is needed, and the bound is
asserted from those named factors, not from a pinned constant.

**Drawlessness.** igGameCenter's rules page states flatly that "No draws are
possible in Quax", and the name *Quadrangular Hex* says the same. This package
proves the two statements it actually needs:

- **Lemma R.** In a 2×2 square that is *not* checkerboard-coloured, a
  monochromatic diagonal is **redundant** — its two endpoints already share a
  same-coloured orthogonal neighbour inside the square. (Exhaustive over all 16
  colourings.)
- **Lemma A.** On a **full** board in which every *checkerboard* square holds a
  link, **exactly one** player has a winning chain. Verified exhaustively over
  every such position on 3×3 (866) and 4×4 (**226,722**), and by sampling at
  5×5/7×7/11×11. Exactly one winner in every one, and the two winners come out
  in a perfect 113,361 / 113,361 tie at 4×4 — the transpose symmetry the pie
  rule also relies on.
- **Lemma B.** If the player to move has **no legal move**, the board is full and
  no unlinked square offers them a link. A checkerboard square always offers a
  link to *both* colours, so every checkerboard square must already be linked —
  and then Lemma A says somebody has already connected, so the game ended
  earlier. **A stuck position is therefore unreachable.**

`returns()` does contain a `[0, 0]` branch for the no-move / no-winner case. It
is provably dead by Lemmas A and B, and the selftest asserts that random play at
five board sizes never reaches it. **If this game ever reports a draw, that is a
bug in move generation, not a draw.**

Exhaustive solves of the smallest board back all of this up: 3×3 is a **first
player win** without the pie rule and a **second player win** with it (strategy
stealing — exactly what a value-preserving swap must produce in a drawless game).

## Bot strength

This package ships **no `heuristic`**, and that is a *measured* decision rather
than an omission.

A connection-distance evaluation was written — a Dijkstra "how many further
moves do I need to connect?" difference, squashed through `tanh` — and measured
**through `MCTSBot`**, the consumer that would use it, at the shipped default
`max_rollout=50` and a wall-clock budget:

| board | rollout cutoff fires (over complete games) | correct vs *flipped* (calibration) | correct vs *none* |
|---|---|---|---|
| 11×11 (default) | 68.8% | **0.800** (8/10) | **0.300** (3/10) |
| 7×7 | 12.9% | 0.450 (harness blind here) | 0.550 |

The 11×11 calibration shows the harness *can* see a sign flip at those settings,
so the 0.300 is a real (if 10-game noisy) signal: the eval is directionally
right but does not pay for the two Dijkstras it costs per cutoff, because under a
wall-clock budget that spend comes straight out of the MCTS iteration count. The
7×7 row is uninformative **by construction** — with the cutoff firing on only
12.9% of rollouts the eval is barely consulted, and indeed the calibration there
cannot distinguish a sign flip from the truth.

(For the record, in an artificial regime with the cutoff forced — 5×5 with
`max_rollout=6` — the same eval beat no-eval **24–0** and its sign-flip
calibration was also 24–0. But at 5×5 the *shipped* cutoff fires on **0.0%** of
rollouts, so that regime never occurs in production. Quoting it as bot strength
would have been exactly the mistake this table exists to avoid.)

## Interpretations, and how each was settled

1. **Does a link block the opponent's crossing diagonal, or only your own?**
   Both — either colour's link kills the crossing one. The designer writes
   "Connect two friendly stones diagonally adjacent, **if it does not cross
   another connection**" (unqualified), igGameCenter says the tile goes "in an
   **empty** rhombic cell", and his *connecting example* figure shows two Black
   stones linked while the two Red stones in the same square "cannot be connected
   directly". Implemented structurally: links are stored **per 2×2 square**, so
   the crossing link is not even expressible.
2. **Do orthogonally adjacent stones connect for free?** Yes — igGameCenter:
   "Two stones are considered to be connected ... if they are horizontally or
   vertically adjacent, **or** if they are diagonally adjacent and there is a
   rhombic tile of the same colour between them." Diagonal adjacency alone never
   connects.
3. **Which player owns which pair of edges?** The designer wrote it **both
   ways, twenty-two years apart, on the same page** — and this package follows
   the way he wrote it *first and most explicitly*.
   - **1992 (decisive).** The r.g.a post of 1992-12-18 that introduced the game
     as *Link* is quoted verbatim on his page: *"The winner is the first player
     to complete a path of stones between his own two edges of the board:
     **north-south for black, east-west for white**."* The same post prints a
     **completed 4×4 game** whose stated facts ("Black has won with a 4-counter
     2-bar path. Black has played 7 moves and white 6.") pin the assignment
     uniquely — under the opposite reading nobody has connected at all, so it
     would not be a completed game. `selftest.py` replays it.
   - **2000 (the other way).** The Quax page's own prose says "horizontal for
     Black, vertical for Red", and his *Race to connections* figure confirms
     that reading: Black's winning move `[1]` = a7 completes a chain from file
     *a* to file *k*, occupying only two ranks.
   - igGameCenter ("Black should connect the Top and Bottom edges") and
     AbstractPlay both follow the **1992** assignment, as does this package and
     the rest of this library (Rhode, Cation, Crossway, TwixT and Bridg-It all
     give the first player top/bottom).

   Nothing is at stake but the labels: transposing the board is an isomorphism
   of every rule while exchanging the two goals, and the starting position is
   empty. So the 2000-era figures are **transposed** into this frame in
   `selftest.py`, where they are the outside-the-engine ground truth for the
   seat names, the goals and both captions — and the 1992 completed game, which
   needs no transposing, is a second independent anchor for the same thing.

   ⚠ The 1992 text is on the **live** page only. Every Wayback capture of the
   page predates it — six captures with five distinct digests, 2003 to 2025, all
   byte-checked — so anyone working from an archived copy sees only the 2000
   labelling.
4. **Is the pie rule part of the game?** Yes — it is in the designer's own rule
   list, and igGameCenter applies it. Offered as an option so the raw game can
   be played too.
5. **Board size.** "Any square board"; the designer suggests 11×11 and his
   published puzzle uses 3×3, so both are offered (with 5–15 between).
6. **The Archimedean board.** The designer notes Quax is "identical to play on
   the Archimedean 8/4/4 board" — octagons for the stones, small squares for the
   links. That is a re-drawing of the same game, not a variant, so this package
   draws the plain square grid with links as lines.

## Sources

- [Games of Soldiers — QUAX](https://jpneto.github.io/world_abstract_games/quax.htm)
  (João Neto's page — the **live** URL; `di.fc.ul.pt/~jpn/gv/quax.htm` now just
  redirects here). Carries Bill Taylor's 2000 rules text, four encoded diagrams,
  three game records, **and the verbatim 1992 r.g.a "RULES OF LINK" post with
  its completed 4×4 game** — the primary source. Cite the live URL, not a
  Wayback snapshot: the 1992 post appears in no archived capture.
- [igGameCenter — Quax rules](https://www.iggamecenter.com/en/rules/quax) — an
  independent playable implementation; the source for "no draws are possible",
  for the corner belonging to both edges, and for the "empty rhombic cell"
  reading of the crossing rule.
- [BoardGameGeek 36804](https://boardgamegeek.com/boardgame/36804/quax) —
  designer Bill Taylor, 2000, web-published, 11×11 suggested.
- AbstractPlay's `gameslib` `quax.ts` — used as a differential **oracle only**.
