# Halfcut

**Mark Steere (August 2023).** A square-board connection game with
**orthogonal-only** chains in which the usual crosscut ban is replaced by a
size contest: you *may* make a crosscut — if the group you just built is bigger
than at least one of that crosscut's enemy groups — and you then immediately
**kill** the enemy crosscut checkers whose groups are smaller than it. Half of every
crosscut dies the moment it is born, which is where the name comes from and why
a filled board always has a winner. *(Rules as implemented in this package.)*

## Board and goal

- Played on the squares of an initially empty square board (default **11×11**;
  this package also offers 5, 7, 9, 13 and 19 — Steere's sheet says "any size").
- **The top and bottom edges are red; the left and right edges are blue.**
- **Red** (player 0, moves first) wins by forming a path of red checkers —
  interconnected via **horizontal or vertical adjacencies only** — connecting
  the two red sides. **Blue** (player 1) connects the two blue sides.
- **Diagonal adjacency does NOT connect.** "Diagonal adjacencies are irrelevant
  in Halfcut."
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
> which is **larger than at least one** of the enemy crosscut groups **of that
> crosscut**.

"Your newly formed crosscut group" is the group containing the checker you just
placed, measured on the position **immediately after the placement and before
any removal**. "At least one" means you need only beat the **smaller** of that
crosscut's two enemy groups.

## Checker removal

> Having formed a crosscut, immediately **remove the enemy crosscut checkers**
> which are part of enemy crosscut groups which are **smaller than** your newly
> formed crosscut group, concluding your turn.

Two things this does *not* say, both settled by Figures 6a/6b:

- It removes the crosscut **checkers**, never their whole groups. In Figure 6
  the dead blue checker's group has size 2 and its group-mate stays on the
  board.
- It removes only the checkers whose group is **under the threshold**. In
  Figure 6 the crosscut's other blue checker sits in a group of size 5 against
  an attacker of size 4, and survives.

Because the crosscut rule requires you to beat at least one of the crosscut's
enemy groups, **at least one enemy checker of every crosscut you form always
dies** — so the crosscut you just made is destroyed in the same turn.

## Simultaneous crosscuts

A placement that would form two crosscuts at once must satisfy the crosscut
rule for **each of them, considered separately** (Figure 7). Two useful
consequences, both derived rather than printed:

- Two crosscuts formed in *opposite* quadrants would make all four of the new
  checker's orthogonal neighbours enemies, so its group would have size 1 and
  could beat nothing. Every **legal** double placement therefore uses two
  *adjacent* quadrants, and those two crosscuts **share exactly one** enemy
  checker. Three crosscuts at once are impossible for the same reason.
- Resolving the two crosscuts **simultaneously or one after the other gives the
  same result**. Both crosscuts contain the checker you placed, so both are
  judged against the same size *N*; every group a removal touches has size
  `< N`; groups are disjoint, so deleting a checker of one such group cannot
  change any other group. There is nothing for an ordering to change. (This
  package resolves them simultaneously.)

## Winning, draws and termination

The connection is checked at the **end of your turn**, after removals. Only the
player who just moved can win: your placement only adds your own colour, and
your removals only take the opponent's.

**Draws are impossible.** The proof is in two steps, both of which this package
tests rather than merely asserts:

1. **No crosscut ever survives a turn.** The empty board has none; every
   crosscut a placement forms loses at least one of its own enemy checkers
   immediately (above); a removal only empties squares, so it can never create
   one. So every position at the start of a turn is crosscut-free.
2. **At most one colour can be blocked on any given empty square.** For Red to
   be blocked at a square, some quadrant's two orthogonal neighbours must both
   be blue; for Blue to be blocked there, some quadrant's two must both be red.
   Those quadrants must therefore be *opposite*, which forces
   `1 + max(P,Q) ≤ N_red ≤ min(U,V)` and `1 + max(U,V) ≤ N_blue ≤ min(P,Q)`
   for the four surrounding group sizes — a contradiction. So while any square
   is empty, somebody can play; "both players stuck" means the board is **full**.
3. A full, crosscut-free board always contains a winner (the **Crossway**
   theorem: with no crosscut, two diagonally adjacent friends on a full board
   are joined through one of the two squares between them, so orthogonal
   connectivity coincides with king connectivity and the standard 8-vs-4
   duality applies). Since it is checked every turn, the win was already
   declared. The "both stuck" branch in the code is therefore unreachable; it
   scores an honest draw rather than a fabricated winner, and the selftest
   asserts every step above — exhaustively on all 19,683 3×3 boards, on all
   crosscut-free full boards up to 4×4, and on every empty square of every
   position it visits.

**The game always terminates**, even though checkers are removed and the board
does not fill monotonically. Order positions by their **multiset of group
sizes**, sorted descending and compared lexicographically. Let *N* be the size
of the group containing the checker just placed. Every friendly group it merged
has size ≤ N−1, and the removal rule only touches enemy groups of size < N
(whose remains can only be smaller still), so the multiset of sizes ≥ N gains
exactly one member, *N*, and loses none — the ordering strictly increases on
every ply. It lives in a finite set, so play is finite. **No ply cap and no
repetition rule are shipped or needed.** In practice games are short: 19×19
random games run about 370 plies (361 squares), 11×11 about 122.

## Moves in this implementation

- A move is a single cell id `"c,r"` — one click on an empty square.
- Skipped turns are folded into the preceding placement, so every ply of the
  game is a real placement and `legal_moves` is never empty on a live position.
  The move log flags them: `d2 (opponent skipped)`.
- The move log writes a placement as `d2`, a capturing placement as `d2xe2`
  (naming every checker killed), and the winning placement with `#`.

## Interpretations and verification

Every number the sheet prints is asserted in `selftest.py` against the
implementation, and all seven figures were transcribed from the PDF's **vector
artwork** (parsed disc paths snapped to each figure's 6×6 lattice), not read off
pixels. In particular Figure 3's "Red has crosscut groups of sizes 1 and 4, Blue
2 and 3", Figure 4's 3-beats-2-though-not-3, Figure 5's 3-vs-{3,5} illegal and
9-vs-{1,1} legal, Figure 6's single dead checker, and Figure 7's {2,3} and
{3,3} all reproduce exactly.

- **No pie rule.** The sheet has none; the PLAY section says only "starting with
  Red". (AbstractPlay's implementation carries a site-level `flags: ["pie"]`,
  which is a convention of that site, not a rule of Halfcut.)
- **Board-wide vs per-crosscut removal.** The removal sentence could be read as
  "every enemy crosscut checker on the board". It makes no difference: by step 1
  above, the only crosscuts in existence when a removal happens are the ones you
  have just formed.
- **Clearcut.** AbstractPlay files this game under the uid `clearcut` and offers
  a `clearcut` *ruleset variant* in which your group must beat **all** the enemy
  crosscut groups. That is a different game; this package implements Halfcut as
  the sheet is written, and Figures 4 and 6 both refute the "all" reading.
- **Differential.** Verified against the AbstractPlay `gameslib` implementation
  over 6,811 played positions and 720 planted positions — 10,858 square-by-square
  legality adjudications, 9,811 legal placements each compared by the *full
  resulting board*, 556 capture placements (993 checkers killed) and 135
  simultaneous crosscuts — with **zero rule disagreements**. The only divergence
  is the skip rule, which that implementation cannot execute at all
  (`validateMove("pass")` always rejects and `move("pass")` throws).
- **No bot evaluation is shipped, and that is a measured decision.** An
  edge-distance `heuristic` (0‑1 BFS: your own checker free, an empty square one
  step, an enemy checker blocking) was written and played head to head through
  `MCTSBot` — the consumer that would use it — against the same bot with a
  constant-zero evaluation, which is exactly what a game with no `heuristic`
  gets. At the production shape (9×9, `max_rollout=50`, 0.5 s/move, colours
  alternating) it scored **11/24** in one run and **17/26** in another —
  **28/50 = 0.56 pooled, indistinguishable from nothing**. It *is* informative:
  with the rollout cutoff forced (`max_rollout=4`) it scored **13/14**. But each
  call costs two whole-board searches, which roughly halves the rollout count,
  and at the real rollout depth that cost cancels the information. So it was
  removed rather than shipped on a plausible-looking number.

## Official rules

Mark Steere's rule sheet: <https://www.marksteeregames.com/Halfcut_rules.pdf>
(md5 `4d0c94735c463c4e7d1e9e8702a41794`, ModDate 2023-08-14 — the live file and
its single Wayback capture are byte-identical, so this sheet has never been
revised).
