# Monkey Queen

A regicide game by **Mark Steere**, invented January 2011, played on a **12×12
checkerboard** with two tall stacks of checkers. Rules as implemented here,
taken from the designer's own rule sheet:
[Monkey_Queen_rules.html](https://www.marksteeregames.com/Monkey_Queen_rules.html)
(HTML, not PDF — there is no `Monkey_Queen_rules.pdf`).

## Board and setup

Each player has one **queen monkey** — a stack of **20 checkers** of their own
colour. **Ivory** starts on **g1** = `6,0`, **Cigar** on **f12** = `5,11`
(Figure 1). The two squares are 180° rotations of one another.

```
      a    b    c    d    e    f    g    h    i    j    k    l
 12   .    .    .    .    .   C20   .    .    .    .    .    .
 11   .    .    .    .    .    .    .    .    .    .    .    .
 10   .    .    .    .    .    .    .    .    .    .    .    .
  9   .    .    .    .    .    .    .    .    .    .    .    .
  8   .    .    .    .    .    .    .    .    .    .    .    .
  7   .    .    .    .    .    .    .    .    .    .    .    .
  6   .    .    .    .    .    .    .    .    .    .    .    .
  5   .    .    .    .    .    .    .    .    .    .    .    .
  4   .    .    .    .    .    .    .    .    .    .    .    .
  3   .    .    .    .    .    .    .    .    .    .    .    .
  2   .    .    .    .    .    .    .    .    .    .    .    .
  1   .    .    .    .    .    .   I20   .    .    .    .    .
```

**Ivory moves first.** A **Starting stack height** option offers the sheet's
"more advanced players may wish to start the game with stacks of **20 or more**":
20 (published default), 30 or 40.

The board's chequering is decoration only — nothing in Monkey Queen depends on
the colour of a square.

## Queens and babies

At every moment each player has **exactly one queen** — their unique stack of
**two or more** checkers, all of their own colour — plus any number of **babies**,
which are **singletons** of their own colour. A stack never mixes colours, and a
square never holds more than one stack.

Two consequences of the rules below keep this true: a capture never changes the
capturing stack's height, a non-capturing queen move lowers it by exactly one,
and a queen of height two may not make a non-capturing move — so a queen can
never shrink to a singleton, and two pieces can never merge.

## Moving

Every piece — queen or baby — **captures exactly like a chess queen**: slide it
in any of the eight directions along a straight run of **empty** squares and take
the **first enemy piece** you reach, **by replacement**. The whole enemy stack
leaves the game for good. **There is never an obligation to capture.**

| Move | Effect |
|---|---|
| **Queen capture** | the **entire** stack relocates onto the victim's square; its height is unchanged and **nothing is left behind** |
| **Queen non-capturing move** | slides like a chess queen to any empty square along the ray, but **leaves its bottom checker behind on the square it came from** as a new baby — the queen's height drops by one (Figure 4) |
| **Baby capture** | the singleton replaces the first enemy piece on a clear ray, at any distance (Figure 5) |
| **Baby non-capturing move** | slides like a chess queen, but **only to a square that strictly shortens its straight-line distance to the ENEMY queen** (Figure 6) |

Two rules the sheet calls out explicitly, both of which follow from the table:

> **NOTE:** A queen may not give birth to its own baby and kill an enemy baby in
> the same move.

> **NOTE:** A queen of height two may not make a non-capturing move.

**"Straight-line distance" is Euclidean**, and the engine compares **squared**
distances so the arithmetic stays exact integers. Figure 6 is the decisive
example: the ivory baby on the figure's bottom-left may slide two squares
diagonally toward the cigar queen (65 → 61), but **not** three squares to the
square marked **X**, which is at *exactly the same* distance (65 → 65). Equal is
not shorter.

## Object of the game

> To win you must either **(1)** kill the enemy queen, or **(2)** deprive your
> opponent of legal moves by leaving him with a queen of height two, no babies,
> and nothing within line of sight for said queen to kill.

The engine implements the general rule: **the player to move with no legal move
LOSES**. That is not a weaker statement — the sheet's condition 2 is a *complete*
characterisation of "no legal moves", proved below.

Figure 8 is a worked stuck-loss (Ivory has a height-2 queen, no babies and an
empty board in every direction, so he cannot move and loses). Figure 9 is a
worked forced loss: Ivory has exactly one legal move, a baby kill, and Cigar's
height-2 queen then takes the ivory queen along a clear diagonal. Figure 7 is a
position from a real game in which every one of Cigar's 92 legal moves loses his
queen on Ivory's next turn.

## The pie rule

> The pie rule is used in Monkey Queen. Black has the option of claiming White's
> first move as his own, swapping colors.

On **Cigar's first turn only**, instead of moving he may play the **Swap** action
button. The two players exchange colours, so Cigar becomes the owner of the
opening move and Ivory must now play as the second player. The engine realises
this as the exact symmetry it is: **rotate the board 180° and exchange the two
colours**, then hand the turn to the other seat. Because the two starting squares
are 180° images of one another, and because the rules are direction-symmetric and
Euclidean distance is rotation-invariant, this is an isomorphism of the game onto
itself. After a swap, the seat that opened faces the untouched 33-move opening
position from the other side.

## Why the game must end, and why a draw cannot occur

Steere states flatly that "a draw cannot occur in Monkey Queen", and his finitude
essay at [abstractgames.org/finitude.html](https://www.abstractgames.org/finitude.html)
is a general design essay that does not cover this game — so here is the argument
this implementation relies on. It needs **no repetition rule and no ply cap**.

Let

* **H** = the total number of checkers on the board;
* **Q** = the sum of the two queens' heights;
* **D** = the sum, over every baby on the board, of the **squared** distance from
  that baby to the **enemy** queen.

Then **every move strictly decreases the triple (H, Q, D) in lexicographic
order**:

1. a **capture** deletes an entire enemy stack, so H drops by at least 1;
2. a **queen non-capturing move** leaves H alone (one checker of the queen becomes
   a baby) and drops that queen's height by exactly one, so Q drops by 1;
3. a **baby non-capturing move** leaves H and Q alone, strictly shortens the
   moving baby's own distance to the enemy queen, and moves **nothing else** —
   every other baby and both queens stay put — so D strictly drops.

ℕ³ under the lexicographic order is well-founded, so play must terminate. The
one exception, the pie swap, is an *isometry*: it preserves H, Q and D exactly,
and it can happen at most once.

Counting the bound: neither H nor Q ever increases anywhere in the game, and both
stay ≥ 4 for as long as play *continues* (each side keeps a queen of height ≥ 2).
So with `m` = 2·(starting height) − 4:

* at most **`m` births** — each drops Q by exactly one, and Q ≥ 4 after every one
  of them;
* at most **`m` + 1 captures** — `m` of them while play continues, **plus the
  game-ending queen kill**, which is the one capture after which H ≥ 4 need not
  hold. (That `+ 1` is easy to miss, and missing it leaves the published bound one
  ply short of airtight.)
* D ≤ `m`·242 (242 = 11²+11² is the largest squared distance on a 12×12 board),
  and only a capture or a birth can reset it. The pie swap is an **isometry** — it
  leaves H, Q and D exactly as they were — so the baby-step runs either side of it
  share one D budget and it buys no extra run.

Those ≤ 2`m` + 1 resetting plies cut the baby-steps into at most 2`m` + 1 runs
(there is no run after the game-ending capture), each of length ≤ `m`·242. Hence

> plies ≤ (2m + 1) + 1 + (2m + 1)·m·242 = **636 050** at the default 20-high
> start (2 814 130 at 40).

`game.py` carries that formula as a hard ply cap purely as a backstop. It is
**dead code by the argument above** and has never fired: over **7 800**
machine-played random games across all three starting heights the longest was
**377 plies** (at the 40-high start; 210 at 20, 314 at 30), and `selftest.py`
re-checks the monovariant on every ply of 300 further games. If the cap ever *did*
fire it would score an honest **0–0 draw** rather than invent a winner — and, as
required everywhere in this codebase, **a decisive result outranks it**: a killed
queen and a stuck-loss delivered on the capping ply both still score decisively,
for **either** seat.

**Draws are therefore impossible**: play always ends, and every terminal position
is decisive (either a queen has been killed, or the player to move has no move
and loses). Not one draw occurred in 7 800 random games.

## Why the sheet's condition 2 is complete

The sheet says you win by leaving your opponent with *"a queen of height two, no
babies, and nothing within line of sight for said queen to kill."* That really is
the only way to have no legal move.

1. **A stuck player has no babies.** Suppose he does; among his babies take the
   one, *B*, closest to the enemy queen *Q*. If *Q* is a neighbour of *B* then *B*
   simply takes it (every neighbour lies on a queen line), so *Q* is not adjacent.
   Then — checked exhaustively over all 19 580 non-adjacent ordered pairs of
   squares (of the 20 592 ordered pairs; the minimum 2 is attained by 440 of
   them, so the bound is tight) — *B* has **at least two** on-board
   one-square steps that strictly shorten its distance to *Q*. Each of those
   squares must be occupied by one of the mover's own pieces (empty would be a
   legal baby move; an enemy piece there would be a legal capture), and each such
   piece is strictly closer to *Q* than *B* is, so by *B*'s minimality none of them
   can be a baby. That needs **two different squares both holding the queen** —
   impossible.
2. **His queen has height exactly two.** With no babies of his own, nothing blocks
   his queen's rays. A queen of height ≥ 3 may give birth onto any empty square
   along a ray, and every square has at least three on-board neighbours, so a
   queen of height ≥ 3 always has a move.
3. **And it sees nothing to kill** — which is exactly the remaining condition,
   since a height-two queen's only moves are captures.

`selftest.py` machine-checks the lemma exhaustively and then confirms the
equivalence "no legal moves ⇔ condition 2" over 8 000 randomly generated
positions (0 disagreements). A separate scratch run confirmed it over 120 000.

## Notation and clicking

A move is `from>to`, e.g. `6,0>6,4` (g1–g5): **click your stack, then the
destination.** The move log uses algebraic a1–l12 with a `Q` prefix for queen
moves, e.g. *"Ivory Qg1-g5 (birth g1, 20>19)"*, *"Ivory Qe6xe4 takes baby"*,
*"Cigar e4xi8 takes baby"*, *"Ivory Qe5xe10 takes queen (3)"*. The pie rule is
the action button **Swap**.

A **queen** is drawn as a side-view tower of same-colour bands with its **height
badge** — all the checkers in a Monkey Queen stack share one colour, so the badge
carries all the information. A **baby** is drawn as a plain disc, exactly the
distinction the rule sheet's own figures make between a numbered queen and an
unnumbered singleton.

## Notes / interpretations

Everything above is decided by the rule sheet. These are the places where a
naive reading could have gone another way, or where a source had to settle it.

1. **The two starting squares** are named nowhere in the text; they were read off
   **Figure 1** by pixel-measuring the printed 12×12 grid (`Monkey_Queen_Figure_A.jpg`
   at 498×513: a 36-px grid with its origin at (33, 33); the ivory disc's ring
   samples white at the g1 centre and the cigar disc's brown at f12). They are
   independently confirmed by the **33 legal opening moves** the position produces,
   which match the AbstractPlay reference implementation move for move, and by
   that implementation's own starting board.
2. **"For convenience, some of the checkers can be kept off the board initially,
   and added to the stacks during play as needed"** is about *physical components*,
   not a rule: a 20-high stack of checkers will not stand up, so you show 12 and
   hold 8 aside, feeding them back into the (shrinking) stack as births take
   checkers off it. A queen's height only ever goes **down**, so nothing is ever
   really "added". The game starts at 20.
3. **Handicaps.** The sheet sanctions "giving the weaker player more checkers than
   the stronger". The engine's height option is **symmetric** — asymmetric
   handicaps are not offered, to keep one dropdown instead of two.
4. **The pie rule is always on**, as the sheet states, rather than being an
   option. It is implemented as the 180°-rotation-plus-colour-exchange described
   above; note that the AbstractPlay reference implementation does **not** offer
   it at all.
5. **"Straight line distance" = Euclidean**, and only the *destination* matters —
   a baby may slide any distance and pass over any number of squares that are
   nearer or farther, as long as the square it lands on is strictly nearer.
   Figure 6 fixes both the metric and the strictness.
6. **The distance rule applies only to non-capturing baby moves.** A baby capture
   is legal even when it carries the baby *farther* from the enemy queen; the
   sheet's capture rule imposes no distance condition. **Figure 5 is itself the
   published proof of this**: the cigar queen stands three ranks below the ivory
   baby, and the figure's kill carries that baby from squared distance **10 to
   26** — strictly *away*. So the exemption is not an interpretation at all.
7. **A capture never leaves anything behind, and never changes the capturing
   stack's height** — that is exactly what the first NOTE ("may not give birth …
   and kill … in the same move") means, and Figure 3 shows a height-6 queen still
   6 high after the kill.
8. **Winning is immediate** on the move that kills the enemy queen; it is not
   deferred to the victim's turn.
9. **A stuck player loses; there is no stalemate draw.** The engine detects this
   from the position rather than from a stored flag, so a hand-built stuck
   position also reads as terminal.
   Note that the rule sheet **contradicts itself** here: the PLAY paragraph says
   *"Players will always have a move available and must make one"*, while the
   OBJECT section, Figure 8 and Figure 9 all describe running out of moves and
   losing. The Object section and the figures win; the PLAY sentence is best read
   as "you may not pass".
10. **The ply cap is a backstop, not a rule** — see above.
11. **Where the figures live.** They are JPEGs under
    `marksteeregames.com/pictures/Monkey_Queen_Figure_<L>.jpg`, and the letters are
    **not** in figure order: `A`=Fig 1, `B`=2, `C`=3, `D`=4, `E`=5, `F`=6,
    **`I`=7, `K`=8, `J`=9**. Each is an 8×8 excerpt drawn at 36 px per square
    (except Figure 1, which is the whole 12×12 board); the two-panel figures put
    "before" at x0 = 30 and "after" at x0 = 382.
12. **BGG / metadata.** BGG id **95757**, "Monkey Queen", Mark Steere, 2011,
    published by Mark Steere Games — verified via `api.geekdo.com`. The rule sheet
    has **not** been revised: the current HTML is byte-for-byte identical to the
    Wayback capture of **10 April 2011**, and Figure 1 has a single Wayback digest.

## Correctness anchors

- **Differential vs the AbstractPlay `gameslib` reference implementation**
  (scratch harness `_diff_gameslib.py`, manual/one-time, needs node; oracle only,
  no code copied): **1 400 random games, 80 626 positions, 6 433 055 moves
  compared**, driven from **both** sides, comparing the legal-move set as
  `{(from, to)}` algebraic pairs, the whole board, the side to move, terminality
  and the winner. **0 mismatches.** The opening position agrees move for move
  (33). Two documented divergences: the reference has no pie rule (the swap is
  excluded from the comparison), and it never reaches a stuck-loss under random
  play either.
- **All nine figures** are replayed in `selftest.py`. Figures 6, 8 and 9 — the ones
  whose claims could depend on where the board edge is — are checked at **all 25
  possible 8×8 crops** of the 12×12 board, so no assertion depends on guessing
  where the excerpt sat. **Figure 7 uniquely identifies its own crop:**
  of the 25 offsets, exactly one — the board's **top-right corner** — makes the
  published claim ("anywhere he moves, Ivory will kill the cigar queen") true,
  and that offset is independently confirmed by the figure's own checkerboard
  parity. In it Cigar has 92 legal moves and loses his queen to all 92.
- **Independent re-derivation.** A second move generator written straight from the
  rule *text*, without reference to `game.py`, agreed on **80 000** move-set
  comparisons over random positions and on every one of **22 816** in-game
  positions across all three starting heights — **0 mismatches**.
- **`selftest.py`** (pure stdlib, in the test suite) also covers: the exhaustive
  19 580-pair stuck-position lemma and the "no legal moves ⇔ condition 2"
  equivalence; the `queen_attacked` reverse lookup tested positively for **both**
  attacker types against a brute-force recomputation from the move generator; the
  seat-swap conjugation (both the plain colour exchange and the 180°+colour map)
  at ~1 700 positions of random games, on move sets, `returns` and `heuristic`;
  the pie rule; the `(H, Q, D)` monovariant on every ply of 300 games; a
  decisive-result-outranks-the-ply-cap re-scoring for **both** kinds of decisive
  result, with the poison shown to bite; a whole-game serialize/deserialize sweep
  comparing **state objects** plus an exact key-set assertion; per-ply invariants
  (one queen each, no empty stack, material and queen height never rise, ply
  parity tracks the seat); `describe_move` for every legal move of six whole
  games; and a `render()` bounds check for every height option from a position
  with all **four corners** occupied, reached through `apply_move`.
- **Independent QA pass (a different agent, adversarial).** All nine figures were
  re-read from the JPEGs and re-transcribed from scratch (piece-for-piece agreement,
  including the height badges 7/9, 6/4, 8/5, 3/5, 7/7, 6/9 and Figure 1's g1/f12);
  Figure 7's crop was re-derived independently and again came out **uniquely** the
  top-right corner (92 cigar moves, 0 escapes; the other 24 offsets leave 1–12).
  A second move generator written from the rule text alone agreed with `game.py` on
  **59 258** constructed positions / **3 276 834** moves (including **601** stuck
  positions, which random play never reaches) and on every ply of 400 whole games.
  A fresh differential against AbstractPlay `gameslib` compared **79 171**
  positions / **5 265 153** moves from both sides plus **700** whole games replayed
  move-for-move (0 mismatches; the coordinate mapping is pinned by the replay — a
  deliberately rank-flipped mapping fails all 700, while position-level move sets
  alone cannot pin it, the board being rank-flip symmetric). **68** independently
  designed mutants: 66 killed, the 2 survivors the same provably equivalent pair
  described below. It corrected three things: the capture bound in the termination
  proof (`m + 1`, not `m` — the game-ending queen kill), the claim that Figure 5's
  kill "happens to move closer" (it moves strictly *farther*, 10 → 26, so the
  figure is itself the published proof of the capture exemption), and **three
  unasserted seat-dependent verdicts** — the stuck-loss `returns`, the stuck-loss
  caption and the killed-queen caption were all asserted only for Ivory, so
  hard-coding the winning colour survived. `selftest.py` now scores the stuck-loss
  for **both** seats (~700 positions each) and reaches one through `apply_move` for
  each seat as exact 180°+colour conjugates.
- **Mutation testing:** **46 distinct single-point mutations** of `game.py` in two
  rounds — wrong starting squares, a wrong default height, capture-plus-birth,
  birth that costs nothing or leaves nothing behind, a height-2 queen allowed to
  give birth (and a height-3 queen forbidden), the baby distance test relaxed to
  `<=` / reversed / aimed at its own queen / measured with Chebyshev or Manhattan,
  sliding through occupied squares, captures suppressed, captures of your own
  pieces, killing a baby scoring as a win, killing the queen not scoring,
  the stuck player winning or drawing, the ply cap consulted before the winner /
  its formula weakened / set absurdly small, `MAX_D2` wrong, each dropped
  serializer field, a hard-coded 8×8 render, the stack tower dropped, babies
  rendered as towers, the turn not passed, the pie swap offered every turn / not
  rotating / not recolouring, the 180° rotation degraded to a mirror, a bare-float
  heuristic, `queen_attacked` blind to baby attackers, a mutilated direction
  table, off-by-one algebraic naming, an 11×11 board, an aliased (mutated) input
  state. **44 killed**; the 2 survivors were then *proved* behaviour-preserving:
  a wrong `height` **default of 12** is filtered back to 20 by the `HEIGHTS`
  whitelist (a default of **30**, which is in the whitelist, *is* killed), and
  making `deserialize` read `ply` with a `.get(…, 0)` default cannot matter while
  the selftest pins `serialize`'s exact key set — which is the pairing that makes
  the round-trip test non-vacuous.
