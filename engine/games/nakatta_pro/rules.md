# Nakatta Pro

**Mark Steere (April 2026).** A square-board connection game with
**orthogonal-only** chains. Three tiny stone patterns — the **glyphs** — may
never be formed, and those three bans are the whole game. Steere calls it *"the
long undiscovered Middle-earth between Nakatta and Minefield"*, and that is
literally true: its ban is provably weaker than Nakatta's and provably stronger
than Minefield's. *(Rules as implemented in this package.)*

## Board and goal

- Played on the points of an initially empty square grid. The sheet says
  **"a square board of any size"**; this package offers 9, 11, 13 (default),
  15 and 19.
- **The top and bottom edges are black; the left and right edges are white.**
- **Black** (player 0, moves first) wins by forming an **orthogonally**
  (horizontally and/or vertically) interconnected path of black stones joining
  the two black edges. **White** (player 1) joins the two white edges.
- **Diagonal adjacency does NOT connect.**
- A corner point belongs to both of its edges.

## Playing a turn

Starting with Black, players alternate placing **one stone of their own colour
on any unoccupied point**. Nothing is ever moved, removed or captured.

**Passing is not allowed, but if you have no available placement your turn is
skipped** and your opponent plays again. (In this implementation the skip
happens automatically — you are never offered a "pass" button.)

**There is no pie rule.** Nakatta's sheet has one and Minefield's 2026 revision
added one; the Nakatta Pro sheet — in *both* its revisions — has none, so none
is shipped here.

## The three prohibited glyphs

> *"Players are not allowed to form any of the glyphs (patterns) in Figure 2
> (or their reflections, rotations, or color reversals). The blue dots are
> unoccupied points."*

`B`/`W` are stones and `.` is a point the glyph requires to be **unoccupied**
(a blue dot in the figure). The area must lie **wholly on the board** — points
off the edge are not "unoccupied points", they are not there at all.

### Hard corner (2×2)

```
 W .
 B W
```

Two diagonally adjacent stones of one colour, one stone of the other colour,
and one unoccupied point. The identical pattern is banned in **Nakatta** and in
**Minefield**, where Steere gives it this name; the Nakatta Pro sheet names
none of its three glyphs, so the other two names below are this package's.

### Bare attachment (2×3)

```
 . .
 . .
 B W
```

An **attachment** (two orthogonally adjacent stones of opposite colour) with
**both** of the two rows beside it clear. Nakatta bans an attachment with
*one* clear row beside it (its "naked attachment"); this is the same idea one
row weaker.

### Broken switch (2×3)

```
 . B
 . .
 B W
```

Minefield's 2×3 **switch** with one of its four corner stones removed: two
stones of one colour on **diagonally opposite corners** of the 2×3, one enemy
stone on a third corner, and the fourth corner plus both non-corner points
unoccupied.

### How the restriction is applied

The rule is judged on the position **after** your placement. Every glyph
requires at least one unoccupied point, so adding a stone can only ever
*destroy* glyphs — a glyph therefore never exists on the board, and the only
patterns that need checking are those containing the point you just played.
That is what makes the mechanism purely **local**: you only have to look at the
4 + 12 areas of 2×2, 2×3 and 3×2 around the point you are considering.
`selftest.py` compares the local test against a full-board rescan on **every**
empty point, for both colours, at every position of twelve whole random games
at sizes 5, 7 and 9 — 38,194 comparisons.

A concrete consequence to feel the strength of the ban: after Black's opening
stone, **White has 76 of the 80 remaining points** — the four points orthogonally
adjacent to the opening stone are barred, because a lone attachment on an
otherwise empty board always has two clear rows beside it.

## Middle-earth: how it sits between its two siblings

| Game | The ban |
|---|---|
| **Nakatta** (2024) | hard corner + attachment with **one** clear row (2×2) |
| **Nakatta Pro** (2026) | hard corner + attachment with **two** clear rows (2×3) + the 2×3 switch **minus one stone** |
| **Minefield** (2024) | hard corner + the **complete** switch (2×3 and 2×4) |

Both containments are theorems, and `selftest.py` proves them:

1. **Weaker than Nakatta.** Every one of the 32 Nakatta Pro glyph images
   *contains* a Nakatta glyph (both 2×3 glyphs contain a 2×2 naked
   attachment), so anything Nakatta Pro forbids, Nakatta forbids too. The
   containment is strict: a bare 2×2 naked attachment is a perfectly legal
   Nakatta Pro position.
2. **Stronger than Minefield.** No Nakatta Pro-legal position can hold a
   Minefield switch. The 2×4 **long switch** *is* a bare attachment (twice
   over), so it is directly a glyph; and removing any one of the 2×3 **short
   switch**'s four stones leaves a **broken switch**, so its last stone can
   never be legally played.

## Termination and draws

**Termination is immediate:** stones are never removed and there is no pie
swap, so *every* ply places a stone on a previously empty point. A game
therefore lasts at most `size²` plies. **No ply cap and no repetition rule are
shipped or needed**, and a cycle is impossible by construction (the stone count
strictly increases every ply — asserted in `selftest.py`).

**A filled board always has exactly one winner.** Removing any one stone from a
**crosscut** (a 2×2 whose two diagonals are monochrome and of opposite colours)
leaves a hard corner, so a crosscut can never be completed. With no crosscut
anywhere, take a filled board on which Black has no orthogonal top–bottom
chain: then White has a *diagonally* connected left–right chain (4-connectivity
for one colour is dual to 8-connectivity for the other on a square grid). Any
diagonal step of that chain can be rerouted through one of the two points
completing its 2×2 — they are occupied, and both being black would make that
2×2 a crosscut — so White's chain is orthogonal after all. Both colours cannot
span at once.

**The one loose end is the early stall:** could *both* players run out of legal
placements while empty points remain? The sheet does not say, and this
implementation scores it as an **honest draw** (`winner = None`, returns
`[0, 0]`) rather than inventing a tiebreak. Measured, not assumed:

- **every reachable position of the 2×2, 3×3 and 4×4 boards enumerated
  exhaustively.** The 2×2 and 3×3 solves run in `selftest.py` through the
  game's own public API (27 and 2,924 distinct states, well under a second);
  the 4×4 solve is a one-off offline run of an equivalent enumerator keyed by
  (board, side to move) — 2,139,277 positions, 137 s. (The two keyings give
  different totals for the same game: the offline one reports 21 and 2,476 for
  the 2×2 and 3×3.) In all three: **zero** double stalls, **zero** draws, and
  never both players connected. All 4,788 filled 4×4 boards are decisive, which
  is the theorem above verified rather than argued. Game values:
  **2×2 is a White win, 3×3 and 4×4 are Black wins**;
- 2,200 **random games** at sizes 3, 4, 5, 7, 9, 11 and 13: no draw, ever;
- a directed **"strangle" hunt** that always plays the move minimising the
  opponent's move count, over sizes 4–7: no draw either (and, interestingly,
  no skipped turn — strangling ends games by *connecting* sooner, not by
  starving anyone).

A **skipped turn**, by contrast, is real and reachable: the exhaustive 3×3 solve
walks through 94 of them and the 4×4 solve 8,496, and random play produces them
up to 13×13 (25 skips in 400 random 3×3 games, 21 at 5×5, 16 at 7×7, 7 at 9×9,
1 in 100 games at 13×13).

Boards fill to 83–89% before somebody connects (measured over the random games
above), so a 13×13 game runs about 150 plies of a possible 169.

## THE RULE SHEET'S FIGURE 3 IS WRONG

This is the one thing a reader of the sheet needs to know, and it is worth
stating precisely because it looks alarming.

Figure 3 prints a 9×9 position and says *"all of the illegal placements for
Black are marked with red dots… All of the other unoccupied points are legal
placements for Black, including the two points marked with green dots."* The
figure's board is legal, **all seven of its red dots really do form a glyph of
Figure 2**, and **both of its green dots really are legal** — but **seventeen
further unoccupied points also form a glyph**, so the completeness claim is
false. This package implements **Figure 2**, the definition.

The evidence that the fault is the sheet's and not this reading of it:

- **The same pipeline reproduces the sibling sheet exactly.** Parsing
  `Minefield_rules.pdf`'s artwork the same way and matching with the same
  semantics gives Minefield's Figure 3 **exactly**: 13 red dots out of 13, both
  green dots legal, no glyph on its board.
- **No rule of the sheet's own format can produce Figure 3.** An exhaustive
  search over every prohibited-pattern set drawable as areas up to 3×3 / 2×4 —
  and, separately, over every *subset* of Figure 2's own 32-element glyph orbit
  (i.e. even allowing the figure's generator to have "forgotten" some
  rotations or colour reversals) — shows that two of the seven red dots,
  `(0,1)` and `(7,5)` in the figure's coordinates, **cannot** be made illegal
  without also making one of the figure's own "legal" points illegal. Isolating
  either of them needs a pattern of area 2×5 or larger, and each such pattern
  covers only that one dot, so five or more glyphs would be needed where the
  sheet prints three.
- **The figure contradicts itself directly.** Placing a black stone on `(5,4)`
  and on `(7,5)` creates the *same* broken-switch instance, same orientation,
  same colours, same offset — yet only `(7,5)` is marked red.

`selftest.py` pins all of it, including the exact list of 17 omitted points, so
the discrepancy can never quietly change.

**Figure 3 is still a strong anchor**, and its power was measured rather than
assumed. Twelve wrong readings of Figure 2 were enumerated — drop each glyph in
turn; the wrong symmetry group (no quarter turns); no colour reversal; the
broken switch's lone stone mis-coloured or on the wrong corner; the bare
attachment read as 2×2 (that is Nakatta) or as 2×4; the broken switch read as
the complete switch; Minefield's ruleset entire; and letting glyph areas hang
over the board edge. **All twelve are killed**, 12 of 12, by the combination of
the seven red dots (which kill the readings that are too weak — hard-corner-only
explains 3 of the 7, dropping the broken switch 4 of 7, dropping the bare
attachment 6 of 7) and the legality of Figures 1 and 3 plus the two green dots
(which kill the readings that are too strong).

## Interpretations

Everything the sheet leaves open, and what settled it:

1. **Figure 2 is the rule, Figure 3 is a broken example.** See above. The
   alternative — treating Figure 3 as authoritative — is not merely unattractive,
   it is *impossible*: no glyph set of the sheet's own format reproduces it.
2. **"Form a glyph" = the position after your placement contains one.**
   Equivalent to the local test, because every glyph needs an unoccupied point.
3. **A glyph area is exactly 2×2 or 2×3 (equivalently 3×2)** — the sizes
   Figure 2 prints. Not 2×4: Minefield's sheet says "2×3 **or** 2×4" explicitly
   when it means both, and this sheet says nothing of the kind. Reading the
   bare attachment as 2×4 is one of the twelve variants Figure 3's red dots
   kill (it explains only 6 of the 7).
4. **The area must lie wholly on the board.** Points off the edge are not
   unoccupied points. Letting areas hang over the edge is killed by Figure 3's
   own board legality *and* by both green dots — and note that **both** green
   dots sit against a board edge (row 1 and the bottom row) and both become
   illegal the moment areas are allowed to overhang. The two points the sheet
   singles out as surprisingly legal are exactly the two the board edge saves,
   which is presumably why it calls them out.
5. **No pie rule.** Not in the sheet, in either revision, unlike both siblings.
6. **The skip is not a move.** The sheet says the turn "is skipped", not that
   you play a pass, so no pass move is offered; the skip is applied inside the
   turn change.
7. **Default board size 13×13.** The sheet specifies none ("any size"). 13 is
   the default of Nakatta, the game this one is named after.
8. **The sheet's own INTRODUCTION misnames the game:** it ends "Mark Steere
   designed **Minefield** in April 2026" — a copy-and-paste slip from the
   sibling sheet. The designer is Mark Steere and the game is dated **2026** on
   his game index, which lists NAKATTA PRO with the tagline used above.
9. **Luis Bolaños Mures is not a co-designer here.** The sheet credits him with
   "a significant contribution… rephrasing the rules by using prohibited
   glyphs, instead of the awkward *'You can't form A unless it's part of B'*
   language I had originally used", which "also slightly simplified the game".
   The `bolanos-mures` tag records the contribution; the `author` field does
   not, unlike Nakatta where he is a co-designer.

## Provenance

- Live sheet: `marksteeregames.com/Nakatta_Pro_rules.pdf`, CreationDate
  2026-04-22, **ModDate 2026-06-14**, md5 `21c52dd947eb4f620c24d93fc6565b95`.
  An Adobe Illustrator PDF whose prose *is* extractable (`pdftotext` yields all
  2,228 characters, two embedded TrueType faces) but whose **figures carry no
  text at all** — and the figures are the rule here. They were read from the
  parsed vector artwork (`pdftocairo -svg`, disc and dot paths snapped to the
  10.8 pt point grid), cross-checked against a 600 dpi raster.
- **Wayback has two captures** (2026-05-11 and 2026-05-13, identical digest),
  both of the **original** April file (ModDate 2026-04-22, md5
  `67edeb7bc3450a8bcc25d03552f91320`). The live file is a **later revision that
  has never been archived** — so, as in five earlier waves, the newest Wayback
  capture predates the current sheet.
- **The revision is a typo fix and nothing else.** A pixel diff of the two
  renders differs in exactly one word ("contibution" → "contribution", design
  notes), and the parsed vector artwork of **all three figures is identical**
  between the revisions. So the Figure 3 defect is present in both and was not
  introduced (or fixed) by the revision.
- **No secondary source exists.** Nakatta Pro has no BoardGameGeek entry, is
  not in AbstractPlay's `gameslib` (which has `nakatta.ts` and `minefield.ts`
  but no Pro), and is not on Board Game Arena. The PDF is the only source, so
  there is no differential oracle for this game; the correctness evidence is
  the figures, the two containment theorems against the shipped sibling
  packages, and the exhaustive small-board solves.

## Bot strength

A **`heuristic` is shipped**: the difference in how many further stones each
side needs to join their edges (0–1 BFS; an own stone costs 0, an unoccupied
point 1, an enemy stone blocks), squashed with `tanh`.

It is not decoration, and it was **measured through `MCTSBot`** — the consumer
that actually uses it — *before* being shipped. `MCTSBot` truncates its random
rollouts after `max_rollout` plies (50 by default) and scores the cut-off
position with the game's `heuristic`, falling back to *a draw* when the game
has none. A Nakatta Pro game runs to roughly `0.85 · size²` plies (measured:
150 of a possible 169 at 13×13), so from the smallest offered board upwards
**every rollout hits the cutoff for most of the game** — and a bot with no eval
therefore scores every one of them 0–0, i.e. has no signal at all.

Head to head at 7×7 with the cutoff forced (`max_rollout=6`, 80 iterations),
seats alternated, identical budgets, the only difference being whether the game
object exposes `heuristic`:

| Run | Result (eval bot – plain bot) |
|---|---|
| 40 games | **40 – 0** |
| 40 games, independent replay, different seeds | **39 – 1** |

The evaluation ignores all three glyph bans, so it is a rough guide only, and
the bot remains weak on the larger boards, as it is for every wide-open
placement game here. Its *direction* is asserted separately from its shape in
`selftest.py` (a sign-flipped eval and a constant-zero eval both pass every
shape/range/zero-sum check), pinned to measured values, and both of those
mutants plus a bare-float return are killed.

## Verification

- The sheet's **three figures**, transcribed from the vector artwork: Figure 1
  asserted glyph-**free** (the premise it silently relies on) with the printed
  black chain joining top and bottom and the white stones *not* connected —
  which pins the seat names and the goal orientation to the artwork rather than
  to any name inside the engine; Figure 2's three glyphs detected at their
  printed anchors with the blue dots asserted to be exactly the union of their
  unoccupied points, and every cell of each glyph shown to matter; Figure 3's
  seven red dots, two green dots and seventeen omissions all pinned.
- **Anchor power measured, not assumed:** 12 enumerated wrong readings, 12
  killed (see above).
- **Two containment theorems** verified against the shipped Nakatta and
  Minefield glyph sets.
- **Exhaustive solves** of the 2×2, 3×3 and 4×4 boards.
- **Local-vs-global** glyph equivalence over whole random games.
- `serialize`/`deserialize` compared as **state objects** with a pinned key
  set, swept over whole games and over hand-built states exercising every
  field.
- `render()` dimensions asserted for **every** offered board size from a
  position reached through `apply_move` with stones in all four corners.
- **Mutation testing:** 30 hand-written semantic mutants of `game.py` — each
  glyph dropped or mis-transcribed (wrong colour, wrong corner, read as 2×2 or
  2×4), the wrong symmetry group (no quarter turns, no colour reversal), the
  local-area scan truncated or shifted, the area read column-major, 8-adjacent
  chains, swapped goals, swapped seat names, swapped edge colours, a hard-coded
  render size, a fabricated tiebreak for the stall, the win test moved after
  the stall test, dropped `serialize` fields, the skip rule removed, `max_plies`
  off by one, and a sign-flipped / constant-zero / bare-float heuristic —
  **30/30 killed** by `selftest.py`, with the unmutated canary surviving in the
  same staging. Every mutant is run under `python -O`, which strips `game.py`'s
  own module-level glyph-orbit assertions, so the *selftest* has to do the
  killing; each mutant is staged as its own `<root>/games/nakatta_pro/` and its
  loaded `__file__` asserted to be inside that root, so no mutant can silently
  fall through to the real package.

## Source

Official rules:
[marksteeregames.com/Nakatta_Pro_rules.pdf](https://www.marksteeregames.com/Nakatta_Pro_rules.pdf)
