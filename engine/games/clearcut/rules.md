# Clearcut

**Mark Steere (July 2023).** A square-board connection game with
**orthogonal-only** chains in which the usual crosscut ban is replaced by a
size contest: you *may* make a crosscut — if the group you just built is bigger
than **every** enemy group of that crosscut — and you then immediately **kill
both** of the crosscut's enemy checkers. The whole crosscut is cleared the
moment it is born, which is where the name comes from and why a filled board
always has a winner. *(Rules as implemented in this package.)*

## Board and goal

- Played on the squares of an initially empty square board (default **11×11**;
  this package also offers 5, 7, 9, 13 and 19 — Steere's sheet says "any size").
- **The top and bottom edges are red; the left and right edges are blue.**
- **Red** (player 0, moves first) wins by forming a path of red checkers —
  interconnected via **horizontal or vertical adjacencies only** — connecting
  the two red sides. **Blue** (player 1) connects the two blue sides.
- **Diagonal adjacency does NOT connect.** "Diagonal adjacencies are irrelevant
  in Clearcut."
- A corner square belongs to both of its edges.

## Play

On your turn you place **one** checker of your own colour on an unoccupied
square, Red first. **Passing is not allowed, but if you have no available
placement your turn is skipped** and the other player moves again.

## Groups, crosscuts and crosscut groups

- A **group** is a monocoloured set of checkers interconnected horizontally
  and/or vertically. Diagonals never join a group.
- A **crosscut** is four checkers filling a 2×2 area, two of each colour, with
  the like colours **diagonally opposed**:

```
    R B          B R
    B R          R B
```

- A **crosscut group** is a group that contains a crosscut checker. A crosscut
  therefore has up to **two crosscut groups of each colour** — one per checker —
  because its two same-coloured checkers are diagonally opposed and so need not
  be connected to each other.

## The crosscut rule

> You can only form a crosscut if by doing so you create a new crosscut group
> which is **larger than each** of the enemy crosscut groups **of that
> crosscut**.

"Your newly formed crosscut group" is the group containing the checker you just
placed, measured on the position **immediately after the placement and before
any removal**. "Each" means you must beat the **larger** of that crosscut's two
enemy groups. Only the groups **of that crosscut** count — an enemy group
elsewhere on the board, however big, is irrelevant.

## Checker removal

> Having formed a crosscut, immediately **remove the two enemy checkers of the
> crosscut**, concluding your turn.

Removal is **unconditional and takes exactly those two checkers** — never their
whole groups. In Figures 6a/6b Red's placement kills two blue checkers whose
groups have sizes 4 and 2, and both of those groups still have surviving
members afterwards.

Because both enemy checkers die, **the crosscut you just made is destroyed in
the same turn** — the whole of it, not half.

## Simultaneous crosscuts

A placement that would form two crosscuts at once must satisfy the crosscut
rule for **each of them, considered separately** (Figure 7). Three consequences,
derived here rather than printed:

- A **legal** placement forms **at most two** crosscuts. Each crosscut uses the
  two orthogonal neighbours of its own quadrant; three crosscuts, or two in
  *opposite* quadrants, would make all four orthogonal neighbours enemies, so
  the new group would have size 1 and could beat nothing. Every legal double
  placement therefore uses two *adjacent* quadrants, and those two crosscuts
  **share exactly one** enemy checker — so a double placement kills **three**
  checkers, not four. (Figure 7's shared blue checker is the printed instance.)
- Resolving the two crosscuts **simultaneously or one after the other gives the
  same result**. Both crosscuts contain the checker you placed, so both are
  judged against the same size *N*; the crosscut rule makes every group a
  removal touches smaller than *N*; groups are disjoint, so deleting a checker
  of one such group cannot change any other group — in particular it cannot
  shrink a group of size ≥ *N* that is blocking the other crosscut. There is
  nothing for an ordering to change. (This package resolves them
  simultaneously.)
- Judging the crosscuts one at a time and judging them against the **pooled**
  set of all their enemy groups are the same test, because "larger than each"
  over a union is the conjunction of "larger than each" over the parts.

## Winning, draws and termination

The connection is checked at the **end of your turn**, after removals. Only the
player who just moved can win: your placement only adds your own colour, and
your removals only take the opponent's.

**Draws are impossible.** The proof is in three steps, each of which this
package tests rather than merely asserts:

1. **No crosscut ever survives a turn.** The empty board has none; every
   crosscut a placement forms loses *both* of its enemy checkers immediately; a
   removal only empties squares, so it can never create one. So every position
   at the start of a turn is crosscut-free.
2. **At most one colour can be blocked on any given empty square.** For Red to
   be blocked at a square, some quadrant's two orthogonal neighbours must both
   be blue; for Blue to be blocked there, some quadrant's two must both be red.
   Those quadrants must therefore be *opposite*, which forces
   `N_red ≥ 1 + max(U,V)` and `N_blue ≤ max(U,V)` from one pair of neighbours
   and the mirror inequalities from the other — so `N_red ≥ 1 + N_blue` and
   `N_blue ≥ 1 + N_red`, a contradiction. So while any square is empty,
   somebody can play; "both players stuck" means the board is **full**.
3. A full, crosscut-free board always contains a winner (the **Crossway**
   theorem: with no crosscut, two diagonally adjacent friends on a full board
   are joined through one of the two squares between them, so orthogonal
   connectivity coincides with king connectivity and the standard 8-vs-4
   duality applies). Since the connection is checked every turn, the win was
   already declared. The "both stuck" branch in the code is therefore
   unreachable; it scores an honest draw rather than a fabricated winner, and
   `selftest.py` asserts every step above — on every ply of every game it
   sweeps, exhaustively over the whole reachable 2×2 and 3×3 state spaces, and
   on all 24,194 crosscut-free full boards up to 4×4 (each of which has
   **exactly one** winner).

**The game always terminates**, even though checkers are removed and the board
does not fill monotonically. Order positions by their **multiset of group
sizes**, sorted descending and compared lexicographically. Let *N* be the size
of the group containing the checker just placed. Every friendly group it merged
has size ≤ N−1, and — this is the crosscut *rule*, not the removal rule — every
enemy checker removed comes from a group of size < N. So every group of size
≥ N survives untouched and the multiset gains exactly one member, *N*: the
ordering strictly increases on every ply. It lives in a finite set, so play is
finite. **No ply cap and no repetition rule are shipped or needed.** In practice
games are short and the board ends nearly full: 11×11 random games run about
120 plies and finish with 114 of the 121 squares occupied, 19×19 about 366 plies
and 346 of 361 squares.

Note the proof is *easier* here than in Halfcut. Clearcut's removal is
unconditional and so could in principle shrink a large enemy group — but it
cannot, because a crosscut with an enemy group of size ≥ N is illegal in the
first place.

## How Clearcut differs from Halfcut

Both games ship in this library. Same designer, same board, same object, same
Figures 1, 2, 3 **and 4**. The two rule sheets differ in exactly two clauses:

| Clause | Clearcut (July 2023) | Halfcut (August 2023) |
|---|---|---|
| Crosscut rule | new group larger than **each** enemy crosscut group | larger than **at least one** |
| Removal | **the two** enemy checkers of the crosscut | only those in groups **smaller than** your new group |

**Figure 4 is the same printed position in both sheets with opposite verdicts.**
Red's new group would be size 3 against blue crosscut groups of sizes 2 and 3;
Halfcut's sheet says Red *can* place (3 > 2), Clearcut's says Red *can't*
(3 is not > 3). That single square settles the distinctness, and `selftest.py`
asserts both verdicts — the Halfcut reading is implemented separately inside the
selftest so the two can be compared. Across random dense positions the two
rulesets disagree on about **17% of crosscut placements**.

Clearcut's *second* difference is redundant given its first: because the
crosscut rule already requires your new group to beat *every* enemy crosscut
group, both enemy checkers of a legal Clearcut crosscut are always in groups
smaller than yours, so "remove the two" and Halfcut's "remove those in smaller
groups" pick out the same checkers. Figures 6a/6b therefore do **not**
discriminate the two removal clauses — measured, not assumed. The discriminator
is Figure 4.

## Moves in this implementation

- A move is a single cell id `"c,r"` — one click on an empty square.
- Skipped turns are folded into the preceding placement, so every ply of the
  game is a real placement and `legal_moves` is never empty on a live position.
  The move log flags them: `d2 (opponent skipped)`.
- The move log writes a placement as `d2`, a capturing placement as `d2xe2f3`
  (naming every checker killed), and the winning placement with `#`.

## Interpretations and verification

All seven figures were transcribed from the PDF's **vector artwork** (parsed
square paths snapped to each figure's 6×6 lattice, and the printed `?` located
from the `?` glyph's own coordinates), not read off pixels, and every number the
prose prints is asserted in `selftest.py`: Figure 3's "Red has crosscut groups
of sizes 1 and 4, Blue 2 and 3"; Figure 4's 3-vs-{2,3} illegal; Figure 5's
4-vs-{3,5} illegal for Red and 9-vs-{1,2} legal for Blue; Figure 6's two dead
blue checkers reproducing 6b square for square; Figure 7's {1,2} and {1,3} with
one shared enemy checker.

- **The anchor's discriminating power was measured, not assumed.** Fourteen
  wrong readings of the sheet are implemented in `selftest.py` and run against
  the figure assertions: the figures kill **10 of 14**. The four survivors are
  closed deliberately — "compare against *all* enemy groups on the board" and
  "judge only the first of two simultaneous crosscuts" by constructed positions
  (a legal crosscut with a size-6 enemy group in the far corner; a double
  crosscut whose first-enumerated half passes and whose second fails), and
  "remove only the smaller-group checkers" and "pool the crosscuts' enemy
  groups" by the proofs above that they are the *same predicate*, checked over
  a sweep of 850 crosscut placements.
- **No pie rule.** The sheet has none; the PLAY section says only "starting
  with Red". (AbstractPlay's implementation carries a site-level
  `flags: ["pie"]`, which is a convention of that site, not a rule of Clearcut.)
- **Removal when two crosscuts form at once.** The removal sentence is written
  in the singular ("the two enemy checkers of *the* crosscut") and no figure
  shows a legal double placement. This package applies it to **each** crosscut
  formed, matching the SIMULTANEOUS CROSSCUTS section's "each considered
  separately" — so a double placement kills the three distinct enemy checkers of
  the two crosscuts. The AbstractPlay implementation does the same.
- **Board-wide vs per-crosscut removal.** The removal sentence could be read as
  "every enemy crosscut checker on the board". It makes no difference: by step 1
  above, the only crosscuts in existence when a removal happens are the ones you
  have just formed.
- **Differential.** Verified against the AbstractPlay `gameslib` implementation
  — which files both games under the uid `clearcut` and reaches this one through
  its `clearcut` *ruleset variant* — over **2,557 played positions** in 40 whole
  games at four board sizes (5/7/9/13), giving **35,856 square-by-square legality
  adjudications driven from BOTH sides** (every square we call legal must be
  accepted and every square we call illegal must be *rejected*), plus **220
  planted dense boards** giving 6,686 further legality verdicts and **6,235 legal
  placements each compared by the FULL resulting board** after removals (137
  capturing placements, 283 checkers killed), plus **1,536 constructed
  simultaneous crosscuts** (752 of them within one checker of the legality
  threshold; the 736 legal ones each killing exactly three checkers).
  **Zero rule disagreements anywhere.** Three deliberate controls each diverge as
  they must: dropping the `clearcut` variant (the oracle then plays Halfcut),
  transposing the coordinate map, and injecting a known bug. The only genuine
  divergence is the skip rule, which that implementation cannot execute at all
  (`validateMove("pass")` always rejects and `move("pass")` throws, so a stuck
  position deadlocks there).
- **The rule sheet was revised.** marksteeregames.com served a *different*
  Clearcut between 2023-07-18 and some time before 2023-10-03 (Wayback capture
  `20230726164322`, md5 `b692772cef602d09d406e7ff8e58ac34`), whose crosscut rule
  was an entirely different mechanism — an "extended crosscut" (the crosscut
  plus all four of its checkers' groups) of which "more than half of the
  checkers are yours". That sheet also spoke of "two **or more**" simultaneous
  crosscuts and printed a Figure 7 forming *four* — which is why this package
  derives the current rule's two-crosscut bound rather than taking it on trust.
  Figures
  3, 4, 5 and 7 were redrawn for the new rule (Figures 1 and 2 are unchanged; 6a
  differs by one square). The live 2023-07-31 sheet replaced it wholesale.
  **This package implements the live sheet**; the superseded one is not offered
  as an option.
- **No bot evaluation is shipped, and that is a measured decision — with the
  numbers, including the ones that argue the other way.** An edge-distance
  `heuristic` (0-1 BFS: your own checker free, an empty square one step, an
  enemy checker blocking) was written and played head to head through
  `MCTSBot` — the consumer that would use it — against the same bot with a
  constant-zero evaluation, which is exactly what a game with no `heuristic`
  gets, colours alternating:

| Configuration | Score | One-sided p vs 0.5 |
|---|---|---|
| 9×9, `max_rollout=50`, 0.5 s/move (24 games) | 14/24 = 0.58 | 0.27 |
| 7×7, `max_rollout=50`, 0.4 s/move (38 games) | 25/38 = 0.66 | 0.037 |
| 9×9, **`max_rollout=4`** (cutoff forced, 14 games) | 13/14 = 0.93 | 0.0009 |

  The evaluation is unambiguously *informative* — with the rollout cutoff forced
  it wins 13 of 14. But each call costs two whole-board BFS, which roughly halves
  the rollout count, and at the real rollout depth that cost eats the
  information: at the configuration closest to the shipped **11×11** default it
  is indistinguishable from nothing. (The 7×7 result trends higher, on a board
  *smaller* than the default, where the eval's O(n²) cost is cheapest relative to
  a rollout; the sibling game Halfcut measured 28/50 = 0.56 independently.) So it
  was removed rather than shipped on a number that is not established at the size
  people will actually play. This is worth revisiting with a larger run — "no
  heuristic" here means "not shown to help at the default board size", not "shown
  to be useless"; pooled over both production-shape configurations it is
  39/62 = 0.63 (p = 0.028), which is suggestive rather than settled. (The 7×7
  runs were cut short by machine load, not by their scores.)

## Official rules

Mark Steere's rule sheet: <https://www.marksteeregames.com/Clearcut_rules.pdf>
(md5 `58702b118227de6083f86da7a3c3fd96`, ModDate 2023-07-31 — byte-identical to
the newest Wayback capture, 2026-04-14). Clearcut appears to have no
BoardGameGeek entry of its own; the designer's index lists it on one line with
Halfcut.
