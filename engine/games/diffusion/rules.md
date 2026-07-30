# Diffusion

**Diffusion** (Mark Steere, January 2006) is a two-player Mancala with **no
capturing, no laps, no scoring and no draws**. You do not sow *around* the
board — you **diffuse** a pit's stones into the ring of pits immediately
**around** it. The twelve pits are split into two blocks, and you win the
instant **your own** block is completely empty.

This page documents the rules **exactly as implemented**. Every rule below was
taken from the official rule sheet
([Diffusion_rules.pdf](https://www.marksteeregames.com/Diffusion_rules.pdf)) and
its figures; each worked example in the sheet (Figures 3, 4, 5, 6 and 8) is
replayed move-for-move by `selftest.py`.

The current sheet is the **2009 revision**. An **earlier revision (2006/2008)**
of the same document — recovered from the Internet Archive — says the same things
in much more words, prints the *stone counts* in its figures, and settles by name
every point the 2009 wording leaves open. Its three worked examples are replayed
too. Where the two revisions differ, the differences are only in wording and in
one *explicitly free* choice; they are listed under **Notes** below.

## Board & setup

A **2 × 6** array of pits with a **store** at each end. Because the board is two
rows deep, an end column is *literally two cells* — which is exactly what the
sheet means by "treat a store as two pits when distributing stones". So this
package renders an **8 × 2 square board** whose outer columns are the stores:

```
 col:    0        1    2    3    4    5    6        7
       +----+  +----+----+----+----+----+----+  +----+
row 1  |    |  | a2 | b2 | c2 | d2 | e2 | f2 |  |    |     <- Player B
       | L  |  +----+----+----+----+----+----+  | R  |
row 0  |    |  | a1 | b1 | c1 | d1 | e1 | f1 |  |    |     <- Player A
       +----+  +----+----+----+----+----+----+  +----+
        store           the 12 pits              store
```

**Setup (Figure 1):** every one of the 12 pits holds **4** stones — 48 stones
in all — and both stores are empty. The stones are all one colour; nobody owns
a stone.

Each pit shows its stone count. A store's running total is printed on the lower
of its two cells in neutral grey (both cells are shaded to show they are one
store), and both totals also appear in the caption. **Store contents are pure
scrap** — they never come back and never affect anything.

**Blocks.** Each player owns a block of six pits and the board is tinted to show
it (red = Player A, blue = Player B):

| Option | Player A (seat 0) owns | Player B (seat 1) owns |
|---|---|---|
| **`v1`** — *Diffusion*, two 2×3 blocks (Fig. 2, default) | the **left** block, columns a–c | the **right** block, columns d–f |
| **`v2`** — *Diffusion v2*, two 1×6 blocks (Fig. 7) | the **lower** row, rank 1 | the **upper** row, rank 2 |

## A move: scoop and diffuse

On your turn you **scoop all of the stones out of any one of the 12 pits** — any
pit, yours or your opponent's — and distribute them one by one into the pits
**adjacent** to it.

"Adjacent" means all eight **king-neighbours** (orthogonal *and* diagonal),
restricted to the board. Since the board is only two rows deep and the stores
occupy the outer columns, **every pit has exactly five adjacent slots**.

**The order (Figures 3 and 4).** Starting at the **most clockwise** slot,
stones go in one at a time **counterclockwise**. The five slots of a pit form a
half-circle, so this is unambiguous: begin at the end of the arc from which
continuing clockwise would leave the board, and sweep the other way.

Numbering the five slots in the order they are filled, where `X` is the pit
being scooped:

```
   scooping a BOTTOM-row pit            scooping a TOP-row pit

   rank 2 :   4    3    2               rank 2 :   1    X    5
   rank 1 :   5    X    1               rank 1 :   2    3    4

             c-1   c   c+1                        c-1   c   c+1
```

* **bottom row:** E → NE → N → NW → W
* **top row:** W → SW → S → SE → E  (the 180° rotation of the above)

Because a pit never holds more than 5 stones and always has exactly 5 slots,
**distribution never wraps around the ring for a second lap**, and **the source
pit itself never receives a stone**.

The two cells of a store column are ordinary slots in this ring. A stone that
lands in one is dropped into that store and **leaves the game**.

> **Worked example (Figure 4).** The top-left pit `a2` holds 5 stones. Its ring
> is `[left store (row 1)], [left store (row 0)], a1, b1, b2`, so **two** stones
> go into the left store and one each into `a1`, `b1`, `b2`.

## Overflow

**A pit holds a maximum of 5 stones.** If adding a stone would make 6, that
sixth stone goes **into a store instead** and leaves the game; the pit stays at
5. Distribution then **carries straight on to the next slot** in the ring — an
overflow costs the sequence nothing.

The sheet says it does not matter which store the stone goes in. This package
banks everything a move sends off the board into the store on the **source pit's
own half** (a–c → left, d–f → right), which is also the store a corner pit's own
store slots physically land in, and which reproduces the store counts printed in
the earlier revision's Figures 4 and 5.

**Stores never overflow.** "The number of stones in a store has no relevance in
the game. They're literally just used for storage."

> **Worked example (Figure 5).** `c1` holds 4 and `d2` is full with 5. Scooping
> `c1` sends stones to `d1`, `d2`, `c2`, `b2`. `d1`, `c2` and `b2` each gain one;
> the stone bound for the full `d2` is banked in a store instead.

## Object of the game

**If at any time one of the two blocks becomes completely vacant, the owner of
that block wins.** It does not matter who emptied it. Any pit is scoopable, so
either player can be the one who empties either block: your opponent can hand
you the game by scooping the last occupied pit of **your** block, and you can
**lose on your own move** by scooping the last occupied pit of **his**.
(Figure 6: Player B wins when the right block empties.
Figure 8: Player B wins Diffusion v2 when the upper row empties.)

The check is made **after the move is complete**, never in the middle of a
distribution — a scoop empties the source pit first, so a block can be
momentarily empty mid-distribution and then refilled by the very same move. The
2009 sheet's "at any time" is loose here, but the earlier revision says it
outright: *"If, **at the conclusion of a turn**, one of the two blocks is
completely vacated, the owner of that block wins."*

### Draws really cannot occur

The sheet claims it, and here is the arithmetic.

**1. Both blocks can never become vacant on the same move.** Both blocks vacant
means all 12 pits are empty. A move only ever *removes* stones from the pit it
scoops — every other pit's count is unchanged or larger afterwards. So if all 12
pits are empty after the move, all 12 non-source pits were already empty before
it, i.e. every stone was in the single scooped pit. That pit lies in one block,
so **the other block was already vacant and the game had already ended.** The
opening position has all 12 pits full, so this is unreachable from move one on.

**2. There is no repetition, no cycle and no move limit to hit.** See the
termination proof below: a strictly decreasing integer quantity means **no
position can ever occur twice**, so no repetition rule is needed and none is
implemented.

A tie is therefore genuinely impossible rather than merely unlikely. The engine
*does* still return an honest 0–0 draw for both of these states rather than
inventing a winner, and it checks the vacant-block win **before** the ply-cap
backstop so a decisive result can never be absorbed by a counter.

## Termination — proof

Stones leave the board only into the stores and never come back, so the
on-board total **S** is non-increasing. But it is not *strictly* decreasing, so
that alone does not prove the game ends. It does, together with a second
quantity.

Call a move **conserving** if no stone leaves the board on it — i.e. none of its
destination slots is a store slot and none of its destination pits is already
full. Give each pit an integer weight:

| row | a | b | c | d | e | f |
|---|---|---|---|---|---|---|
| **rank 2** (top) | 0 | 27 | 32 | 33 | 34 | 35 |
| **rank 1** (bottom) | 35 | 34 | 33 | 32 | 27 | 0 |

and let **Φ = Σ (stones in pit) × (weight of pit)**.

There are exactly **46** (source pit, stone-count) combinations that can be
conserving, and for **every one of them Φ falls by at least 1** — checked
exhaustively in `selftest.py`. (The table was produced as the minimum-range
vertex of the corresponding linear program, so it is about as tight as a linear
certificate gets.) Meanwhile no move can raise Φ by more than **96**.

So put **Ψ = 97·S + Φ**:

* a conserving move leaves S alone and drops Φ by ≥ 1 ⇒ **Ψ drops by ≥ 1**;
* any other move drops S by ≥ 1 and raises Φ by ≤ 96 ⇒ Ψ changes by
  ≤ −97 + 96 = **−1**.

Ψ is a non-negative integer (all weights are ≥ 0) and starts at
97 × 48 + 4 × 322 = **5944**. Therefore:

* **every Diffusion game ends after at most 5944 plies**, from any position and
  under any play, with no repetition rule and no no-progress rule; and
* since Ψ is a function of the position alone, **Ψ strictly decreasing means no
  position is ever repeated.**

Random self-play agrees with room to spare: across two independent 60,000-game
uniform-random samples the longest was **141 plies** (median ≈86), and Ψ
decreased on every single move.

`PLY_CAP = 5944` is implemented as a draw-declaring backstop purely to guard
against a future implementation bug; the proof says it can never be reached, and
the vacant-block win is always evaluated first.

## Notes / interpretations

- **Adjacency includes diagonals.** Figure 3 scoops a 5-stone bottom-row pit and
  lands stones in five distinct pits — three in the other row — which is only
  possible if the ring is the king-neighbourhood. The earlier revision states it:
  *"pits which are **orthogonally or diagonally adjacent** to the newly emptied
  pit"*.
- **"Most clockwise, then counterclockwise"** is relative to the source pit's own
  compass, not to the board's centre. Fixed by Figure 3b (the arrow starts at the
  east neighbour, arcs over the top and ends at the west one), independently by
  Figure 4b (from a top-row pit both store slots fill first), and stated outright
  in the earlier revision: *"start at the clockwise limit and distribute the stones
  in sequence, counterclockwise around the emptied pit"*, with the two ends spelled
  out as "the small pit immediately to the **right**" for a pit in your **near** row
  and "to the **left**" for one in your **far** row. Note those two phrasings agree
  with each other for *both* seats, so the rule is purely geometric: bottom row
  starts east, top row starts west.
- **No wrap / second lap.** Cannot arise: max 5 stones, always exactly 5 slots.
  The source pit therefore never receives a stone either.
- **Only non-empty pits may be scooped.** The earlier revision is explicit: *"any
  one of the 12 small pits **which contains stones**… Players cannot pass on their
  turn. There will always be at least one move available."* Scooping an empty pit
  would be a null move and would break both termination and the no-draws claim.
  The AbstractPlay implementation agrees (its legal list is the pits holding > 0).
- **A store is two slots, and stores never overflow.** The earlier revision:
  *"treat the adjacent large pit as **two empty small pits**"* — always empty, so
  the 5-stone cap never applies to them.
- **Which store an overflow stone goes to** is explicitly the player's free
  choice, and the two published revisions demonstrate it by disagreeing. The
  earlier Figure 5 scoops `d2` and banks both overflow stones in the **right**
  store — the source's own half, the rule this package uses. The 2009 Figure 5
  scoops `c1` (left half) and banks its one overflow stone in the **right** store —
  the opposite half, which this package would put on the left. Both are legal,
  because the choice is free. `selftest.py` additionally asserts that perturbing
  the store contents never changes a legal move, a terminal test or a result, so
  the choice is *provably* immaterial; and it is the only deliberate mutation of
  `game.py` whose only visible effect is on the stores.
- **Diffusion v2 blocks** are the lower and upper *rows*, with **Player A = the
  lower row** — read off Figure 7's labels and confirmed by Figure 8's caption
  ("Player B wins since the upper 1x6 block becomes vacant"). **v2 did not exist in
  the earlier revision**; it was added in the 2009 rewrite.
- **No pie rule.** AbstractPlay adds an optional swap after the first move; that
  is a platform convention of theirs and is not in Steere's rules, so it is not
  implemented here.
- The board's 180° rotation (column *c* ↔ *7−c*, row *r* ↔ *1−r*) is an exact
  symmetry of the geometry, the distribution rings **and** the block assignment in
  both variants — `selftest.py` uses it to test both seats.
- Steere dates the design precisely: *"Mark Steere invented Diffusion on
  **January 20, 2006**"*. BGG lists it as **22326**, published 2006 by Mark Steere
  Games.

## Anchors

- Every worked example in the 2009 rule sheet (Figures 1, 3, 4, 5, 6, 7, 8) and
  all three in the earlier revision ("Edge Move", "Corner Move", "Max 5-Count",
  whose figures print exact stone *and store* counts) are replayed in
  `selftest.py`, with the full 12-pit distribution table frozen as a literal.
- Differential-tested against **AbstractPlay gameslib**'s independent
  `diffusion` implementation: **70,510 plies over 800 random games** (both
  variants, driven from both sides), comparing board contents, both store totals,
  legal-move sets, game-over and winner — **zero mismatches**.
- 31 deliberate mutations of `game.py` (ring order, diagonals, overflow, store
  slots, block assignment, win polarity, draw-counter precedence, serialize
  fields, turn order, the potential weights, render) were each caught by
  `selftest.py`.
- **Independent QA pass.** The termination proof was re-derived from scratch (all
  46 conserving cases, the +96 rise bound and Ψ(open) = 5944 reproduced, plus an
  exhaustive check that **every** one of the 588 possible move *shapes* drops Ψ);
  a second implementation written from the rule sheet alone agreed over **103,273
  plies / 1,200 games**, and a fresh gameslib differential over **43,082 plies /
  500 games** (with a mirror control that breaks at ply 1, so the coordinate map
  is pinned by data) found no mismatch. A 69-mutant sweep killed every rule
  mutant; the nine that survived were all unasserted *presentation* behaviour
  (pit/store colours, the caption, the `a1`–`f2` notation, the heuristic's sign
  and the `apply_move` guards) and `selftest.py` now asserts each of them.
