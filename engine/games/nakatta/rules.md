# Nakatta

**Luis Bolaños Mures and Mark Steere (April 2024).** A square-board connection
game with **orthogonal-only** chains. Two tiny 2×2 patterns — the **hard
corner** and the **naked attachment** — may never exist on the board, and those
two bans are the whole game. The name is a pun on *NAKedly ATTAching*.
*(Rules as implemented in this package.)*

## Board and goal

- Played on the points of an initially empty square grid (default **13×13**;
  this package also offers 9, 11, 15, 19, 22 and 25 — the sheet names no size,
  and the designers' own BGG entry lists 19×19, 22×22 and 25×25 grids).
- **The top and bottom edges are black; the left and right edges are white.**
- **Black** (player 0, moves first) wins if there is a chain of black stones —
  interconnected **orthogonally** (horizontally or vertically) only —
  touching the two black edges. **White** (player 1) joins the two white edges.
- **Diagonal adjacency does NOT connect.**
- A corner point belongs to both of its edges.

## Playing a turn

Starting with Black, players alternate placing **one stone of their own colour
on any unoccupied point**. Nothing is ever moved, removed or captured.

**After your placement there must be no hard corners and no naked attachments
anywhere on the board.**

**Passing is not allowed, but if you have no legal move your turn is skipped**
and your opponent plays again. (In this implementation the skip happens
automatically — you are never offered a "pass" button.)

## The two illegal patterns

Both are patterns inside a **2×2 area of adjacent points**, in any rotation,
reflection or colour reversal. `B`/`W` are stones, `.` is an unoccupied point.
The 2×2 area must lie **wholly on the board** — points off the edge are not
"empty points", they are not there at all. (Areas that merely *touch* an edge do
count: one of Figure 2's six hard corners and one of Figure 3's seven naked
attachments sit against the border.)

### Hard corner

> Two diagonally adjacent stones of the same colour, one stone of the opposite
> colour, and one empty point.

```
 W B          (the two B stones are diagonally adjacent;
 B .           the W stone is the odd one out; one point is empty)
```

Because the like-coloured pair occupies one diagonal of the 2×2, the other
diagonal necessarily holds the lone enemy stone and the empty point — so **the
empty point is always diagonally opposite the lone enemy stone**. The prose
admits no other arrangement. The sheet's **Figure 2** prints a 9×9 position
stated to contain exactly **six** hard corners; this implementation counts
exactly six there (`selftest.py`).

### Naked attachment

> Two orthogonally adjacent empty points, one black stone, and one white stone.

```
 . .          (the two empty points are side by side, NOT diagonal;
 B W           the two stones are then side by side too)
```

The two stones are orthogonally adjacent — an *attachment* — and the pair of
points that would "clothe" it on one side are both empty. If the two empty
points are **diagonal** to each other, this is **not** a naked attachment. The
sheet's **Figure 3** prints a position stated to contain exactly **seven**;
this implementation counts exactly seven.

### Local or global?

The sheet states the condition globally ("after your placement there must be no
hard corners and no naked attachments **on the board**"). That is equivalent to
the simpler "your placement may not *form* one" (the designers' own BGG
wording), and this package implements the local form:

- the empty board contains neither pattern;
- **both patterns require at least one empty point**, so adding a stone can only
  *destroy* patterns, never preserve one elsewhere;
- a 2×2 area not containing the placed point is unchanged.

So no legal position ever contains either pattern, and every pattern a move
could create contains the stone just placed — only the (at most four) 2×2 areas
containing that point need to be examined. `selftest.py` checks the local test
against a full-board scan on every empty point of every position of complete
random games.

## Pie rule (swap)

Black places first. On **White's first turn only**, White may play **swap**
instead of placing: White takes over Black's opening. Nakatta is symmetric
under **transposition combined with colour reversal** (both patterns are closed
under reflection *and* under colour reversal, and reflecting in the main
diagonal exchanges the black row-goal with the white column-goal), so the
value-preserving implementation of "swap sides" on a platform with fixed seats
is: Black's lone stone at `(c, r)` becomes a **white** stone at `(r, c)`, and
Black is on move again. Recolouring the stone in place would *not* preserve the
value, because the two colours aim at different pairs of edges.

## Termination and draws

**Termination is immediate:** stones are never removed, so every ply either
places a stone on a previously empty point or is the one-off pie swap. A game
therefore lasts at most `size² + 1` plies. **No ply cap and no repetition rule
are shipped or needed.**

**The designers call Nakatta drawless** (their BGG description: "Nakatta is a
drawless connection game"). The rule sheet itself does not say so, and does not
say what happens if play stops with nobody connected, so this implementation
scores that as an **honest draw** (`winner = None`, returns `[0, 0]`) rather
than inventing a tiebreak. Here is what is actually established:

1. **No legal position contains a hard corner or a naked attachment** (the
   induction above).
2. **No legal position contains a crosscut** — a full 2×2 whose two diagonals
   are each monochrome and of opposite colours. A crosscut can only appear when
   its *fourth* stone is placed, and removing any one stone from a crosscut
   leaves a **hard corner**; by (1) no game is ever in that position. This is
   why the checkerboard — the classic winner-less full board — is unreachable:
   a checkerboard missing one point is a hard corner.
3. **A full board always has exactly one winner.** With no crosscut anywhere,
   any diagonal step in a chain can be re-routed through one of the two points
   that complete its 2×2 (they are never both enemy stones), so 8-connectivity
   and orthogonal connectivity coincide for both colours. The classical grid
   theorem then says that on a filled board either Black orthogonally spans top
   to bottom or White 8-connectedly spans left to right — and here the latter
   implies White spans orthogonally. Both cannot happen at once. (Only the
   mover's stone is added on a turn, so only the mover can complete a chain
   anyway; this implementation checks the connection only for the player who
   has just placed.)
4. **The one clause not proved** is the early stall: could *both* players run
   out of legal placements while the board is not yet full? A single point can
   certainly be illegal for both colours (e.g. `B . W` along the top edge with
   the three points below it empty), so it is not locally obvious. Measured
   instead:
   - **every reachable position of 2×2, 3×3 and 4×4 enumerated exhaustively**
     (919,165 positions at 4×4) — zero stalls, zero draws, and never both
     players connected;
   - **all 6,334,357 crosscut-free pattern-free 4×4 boards** enumerated
     statically (a strict superset of the reachable ones) — zero positions with
     both players stuck, and all 23,858 *full* boards have a winner, which is
     step 3 above verified rather than argued;
   - **16,000 random games** at 5×5, 7×7, 9×9 and 11×11 (864 skipped turns
     among them) plus **600 games under a "strangle" policy** that deliberately
     minimises the opponent's move count (330 more skipped turns), and further
     random games at 13×13 to 25×25 — **no draw, ever**.

   If one ever does occur, it is scored 0–0.

A **skipped turn**, by contrast, is common and fully live: it occurs in 8.6% of
random 5×5 games (342 of 4,000) and is reached on the 3×3 board too, so it is
covered by the exhaustive anchor as well as by directed play.

## Options

- **Board size** — 9, 11, 13 (default), 15, 19, 22, 25.

## Bot strength

A **`heuristic` is shipped**: the difference in how many further stones each
side needs to join their edges (0–1 BFS; an own stone costs 0, an empty point 1,
an enemy stone blocks), squashed with `tanh`.

It is not decoration, and the reason is structural rather than statistical.
`MCTSBot` truncates its random rollouts after `max_rollout` plies (50 by
default) and scores the cut-off position with the game's `heuristic`, falling
back to *a draw* when the game has none. A Nakatta game runs to roughly
`0.85 · size²` plies (measured: 147 of a possible 169 at 13×13, ~542 of 625 at
25×25), so from the default board size upwards **every rollout hits the cutoff
for most of the game** — and a bot with no eval therefore scores every one of
them 0–0, i.e. has no signal at all.

Measured head-to-head *through `MCTSBot`*, seats alternated, identical budgets,
the only difference being whether the game object exposes `heuristic`:

| Board | Rollout length | Iterations | Result (with eval – without) |
|---|---|---|---|
| 7×7 | `max_rollout=6` (cutoff forced) | 80 | **60 – 0**; an independent replay with different seeds gave **56 – 4** |
| 9×9 | 50 (platform default) | 60 | 7 – 6 |
| 11×11 | 50 (platform default) | 25 | 5 – 5 |

Read those honestly. The 7×7 row is the one that shows the eval carries real
information: with the cutoff forced, the bot without it is scoring every rollout
0–0 and is effectively picking at random, and it loses ≈93–100% of the games
(the exact score is seed-dependent; both runs above are 60 games). The
9×9 and 11×11 rows are indistinguishable from a coin flip, for two reasons that
are both about the *search*, not the eval: a 68-ply game means a 50-ply rollout
usually does reach a real terminal from about ply 18 onwards (so the plain bot
has genuine signal there), and at these branching factors — 25 iterations
against ~110 legal moves at 11×11 — neither bot can even visit every root move
once, so the comparison is mostly noise.

The eval is shipped because it is **never measurably worse** and because on the
default 13×13 board and larger the rollout cutoff never stops firing, so it is
the only signal the bot has at all. It ignores both pattern bans, so it is a
rough guide only, and the bot remains weak on the larger boards, as it is for
every wide-open placement game.

## Verification

- **The rule sheet's own figures** (`marksteeregames.com/Nakatta_rules.pdf`,
  ModDate 2024-04-24) are transcribed into `selftest.py` from the *vector*
  artwork, not from pixels: Figure 2's **6 hard corners**, Figure 3's **7 naked
  attachments** (in both cases the red dots are asserted to be exactly the
  union of the patterns' empty points), and Figure 1's won position, which is
  asserted to be **pattern-free** — the premise it silently relies on — and
  which pins "Black joins the top and bottom edges" to the printed artwork
  rather than to any name inside the engine.
- Each figure's **discriminating power was measured, not assumed**, and the
  gaps closed on purpose. Figure 2's "6" kills 5 of 7 wrong hard-corner
  readings — the two it cannot see are killed by Figure 1's legality premise.
  Figure 3's "7" kills 4 of 5 wrong naked-attachment readings; the survivor
  (counting diagonal empty pairs as attachments) is killed by a constructed
  position, on the sheet's explicit word *orthogonally*. A third mistake shape
  — letting 2×2 areas hang over the board edge — is invisible to Figures 1
  *and* 2 and is caught only by Figure 3 (8 instead of 7).
- **Mutation testing:** 27 hand-written semantic mutants of `game.py`
  (wrong 2×2 diagonal, each pattern clause dropped or inverted, one-block
  legality, swapped goals, 8-adjacent chains, a swap without the transpose or
  the recolour, the win test moved after the skip test, dropped `serialize`
  fields, a hard-coded render size, a sign-flipped / constant-zero / bare-float
  heuristic, …) — **27/27 killed** by `selftest.py`, with the unmutated canary
  surviving.
- The live PDF is **byte-identical** to its single Wayback capture
  (2024-06-18), so unlike most of this designer's sheets it has never been
  revised.
- **Differential** against AbstractPlay's `gameslib` implementation
  (`nakatta.ts`) over 8,396 positions at sizes 5, 7, 9, 13 and 22, driving from
  both sides and filtering its moves through its own `validateMove`: **no rule
  disagreement**. Two notes on the oracle: its `validateMove("pass")`
  always rejects the pass its own `moves()` offers, so **its skip rule is dead
  code** and a game in which either player is ever stuck cannot be continued
  there; and it implements the pie rule as a site-level flag outside the game
  class, so the swap has no differential coverage at all and is covered here by
  constructed tests only.

## Family

Nakatta is one of a group of square-board, orthogonal-only connection games
that answer the crosscut problem with placement restrictions. Its immediate
sibling is **Minefield** (Steere, May 2024), which keeps the *same* hard-corner
ban and replaces the naked-attachment ban with the "switch"; the other
neighbours in this collection are Crossway, Konobi, Rhode, Cation, Akimbo,
Okimba, Flipway, Keil and Necklace.

## Source

Official rules: [marksteeregames.com/Nakatta_rules.pdf](https://www.marksteeregames.com/Nakatta_rules.pdf)
