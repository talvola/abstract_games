# Blast Radius

**Mark Steere, November 2024.** Two players, hexagonal board, no draws.

Official rule sheet: [marksteeregames.com/Blast_Radius_rules.pdf](https://www.marksteeregames.com/Blast_Radius_rules.pdf).
This page describes the rules **as implemented here**, and is the local source of truth.

> **Rule-sheet revision.** The sheet was revised without announcement between
> 2024-12-02 and 2025-05-28. The old text read *"If there are no enemy checkers on
> the board at the conclusion of your turn, you win."* The current text adds
> *"**(except at the conclusion of Red's first turn)**"* — without which Red would win
> on move 1, since the board starts empty and Blue therefore has no checkers on it.
> Nothing else changed: the prose diff is that one parenthetical plus the line
> reflow it caused, and all 194 shapes of all four figures are geometrically
> identical between the two revisions (checked by parsing the vector paths of
> both PDFs). The sheet live today is byte-identical to the 2025 snapshot.
> **This package implements the current (2025) rule.**

## Board and equipment

A hexagonal board (a "hexhex") of any side length, **initially empty**, and a supply
of red and blue checkers. Cells are addressed by axial coordinates `"q,r"`; the
distance between two cells is the ordinary hex distance (the number of steps from
one to the other).

| Option | Cells | Note |
| --- | ---: | --- |
| side 4 | 37 | the board drawn in all four figures of the rule sheet |
| side 5 | 61 | |
| **side 6** | **91** | default; also AbstractPlay's default |
| side 7 | 127 | |

Red is seat 0 and moves first.

## Stacks and the radiation exclusion zone

A **stack** is one or more like-coloured checkers on a single cell. Stacks are
always mono-coloured — you may only add to your own — and a stack's **height** is
the number of checkers in it.

Every stack is surrounded by a **radiation exclusion zone (REZ)** whose radius equals
its height: the REZ of a height-*h* stack is every cell at hex distance ≤ *h*,
**ground zero (the stack's own cell) included**.

```
        . . . .              A height-2 stack at the centre.
       . x x x .             Its REZ = the 19 cells marked x or @
      . x x x x .            (distance 0, 1 and 2).
     . x x @ x x .
      . x x x x .
       . x x x .
        . . . .
```

## Play

Red places first, then the players alternate, **one checker per turn**, subject to
two restrictions:

1. **You can't place a checker within a REZ** — anybody's REZ — **except on a
   friendly stack at ground zero.**
2. **You must form the smallest stack that you can.** So: if there is any cell that
   is empty *and* outside every REZ, you must place there. Only when no such cell
   exists may you build, and then you must place on one of **your own shortest
   stacks**.

A turn is always exactly one placement; there is no pass and no other move.

## Captures

**Upon forming a stack of height 2 or more, every other stack — friendly and enemy
alike — inside the newly formed REZ is removed**, and your turn ends. The stack you
have just built is at ground zero of its own blast and **survives**.

There is no cascade: the removals happen in a single simultaneous sweep, and since
removing stacks never *forms* a stack, nothing else can be triggered.

## Object

**If there are no enemy checkers on the board at the conclusion of your turn, you
win** — except at the conclusion of Red's first turn.

There are no draws (see below).

---

## Notes on the implementation

### Anchors: the rule sheet's own figures

All four figures are reproduced cell-for-cell in `selftest.py`, decoded from the
vector paths of the PDF rather than from the prose:

* **Figure 1** (a height-2 red stack and a height-1 blue stack) marks 16 red dots,
  4 blue dots and 2 purple dots. Our REZ generator produces exactly those cells,
  with the two stack cells themselves red-only / blue-only — which is what fixes
  **ground zero as being inside its own REZ**. (Rule 1's carve-out — "except on a
  friendly stack at ground zero" — would otherwise be unnecessary.)
* **Figure 2** — Red's legal placements are exactly the two green-dotted cells.
* **Figure 3** — no cell is both empty and outside every REZ, so restriction 2 forces
  Red onto his shortest stacks: exactly the three green-dotted height-1 stacks. Red's
  height-2 stack, though legal under restriction 1, is excluded by restriction 2.
* **Figure 4** — Red builds his height-3 stack to 4; exactly the two yellow-dotted
  stacks (both at distance 4) are removed, the blue stack at distance 6 survives, and
  so does the newly built stack itself.

### The separation invariant

At the conclusion of every turn, any two distinct stacks *A* ≠ *B* satisfy

> **dist(A, B) > max(height(A), height(B))**

*Proof.* Trivially true on an empty board. A placement on an empty cell is legal only
outside every REZ, so dist to every stack *B* exceeds height(*B*) ≥ 1 — hence is at
least 2, which also exceeds the new stack's height of 1. A placement on your own
stack at *c* raises its height from *h* to *h*+1; by the invariant every other stack
was already at distance ≥ *h*+1, and the capture removes precisely those at distance
exactly *h*+1, so every survivor is at distance ≥ *h*+2 > *h*+1. ∎

Three things follow, each of which settles a question the sheet leaves open:

* **No stack is ever inside another stack's REZ.** So "remove all stacks within the
  *newly formed* REZ" (the sheet) and "remove every stack that lies inside any REZ"
  (AbstractPlay's formulation) are the same rule, and — more importantly —
  restriction 1's exception is **unambiguous**: a friendly stack's ground zero lies
  inside its own REZ and no other, so it makes no difference whether the carve-out is
  read as blanket or as lifting only the stack's own zone. The two readings can never
  diverge.
* **A height-1 placement never captures.** Its REZ has radius 1 and no stack is
  within distance 1 of it. So "upon forming a stack of height 2 or more" loses nothing
  by being written as an unconditional sweep of the new REZ.
* **Captures cannot begin until the board saturates.** While an empty non-REZ cell
  exists, restriction 2 forces a placement there, which creates a height-1 stack and
  captures nothing. So the first phase of every game is both sides packing singletons
  onto the board; only when nothing is left to pack does anyone start building — and
  detonating.

### Termination — proved, so there is no ply cap and no repetition rule

Write a position's stack heights as a vector sorted **descending** and padded with
zeros to the number of cells. **Every legal move raises that vector strictly in
lexicographic order.**

* *Placing on an empty cell* appends a 1: the first *k* entries (the existing stacks)
  are unchanged, and entry *k*+1 goes from a padding 0 to 1.
* *Building a stack from h to h+1* — every captured stack is strictly shorter than the
  new one (a stack at distance *d* ≤ *h*+1 had height < *d*, so height ≤ *h*), so the
  entries greater than *h* are untouched. If there are *k* of them, entry *k*+1 was
  *h* (the stack being built, the tallest of those ≤ *h*) and is now *h*+1.

The vector is bounded — its length is the cell count and, by the separation invariant,
no height can exceed the board diameter **2·(side − 1)** — so the sequence of positions
in a game is a strictly increasing sequence in a finite well-order and must be finite.
**No position can ever repeat**, so the game needs neither a repetition rule nor a ply
cap, and there is no cap in the code that could decide a result. The selftest asserts
the strict increase on every ply of thousands of random games, and measures the
observed maximum height at 6 / 8 / 10 / 12 on sides 4 / 5 / 6 / 7 — exactly the bound.

Typical random-game lengths: 24 plies (side 4), 45 (side 5), 76 (side 6), 118 (side 7).

### Why only *Red's* first turn is excepted

* **Blue needs no exception.** Blue's first placement is on an empty cell (there are
  always plenty at that point), so it forms a height-1 stack and, by the corollary
  above, captures nothing — Red's checker is still there.
* **Mutual annihilation cannot happen.** The stack you have just built survives its own
  blast, so at the conclusion of *your* turn you always have at least one checker on
  the board. A position with nobody on the board is unreachable. (`returns` still
  reports an honest 0–0 draw for it rather than fabricating a winner; the selftest
  asserts the mover always survives.)
* **Nobody can ever be stuck.** If you have a stack you always have a move
  (restriction 2 falls back to your own shortest stacks). If you have no stack the
  game is already over — except on Blue's very first turn, and a single height-1 red
  checker excludes at most 7 of the ≥ 37 cells. This is why the smallest board offered
  here is side 4; on a side-2 board (7 cells) a *central* opening checker covers the
  whole board and Blue would have no legal move at all.

AbstractPlay's implementation is slightly more conservative — it suppresses the win
check for the first *three* plies, i.e. through Red's second turn as well. On every
board size offered here that extra slack is unreachable: at Red's second turn the board
holds two height-1 stacks whose REZs cover at most 14 cells, so restriction 2 forces an
empty-cell placement, which cannot capture. The two implementations agree everywhere.

### The bot's evaluation has a counter-intuitive sign

The MCTS bot's position evaluation says that **owning fewer stacks than your opponent
is good**. That is not what it looks like from the win condition, so it was measured
rather than guessed, twice and independently:

| measurement (sides 4 / 5) | result |
| --- | --- |
| correlation of *(my stacks − your stacks)* with sampled win probability | **−0.22 / −0.33** |
| greedy play on the eval vs. a random player | **0.61** |
| greedy play on the **sign-flipped** eval vs. a random player | 0.34 |
| greedy play on a constant (i.e. no eval at all) | 0.50 |

The intuition afterwards: restriction 2 forces you to keep putting checkers down while
any empty non-REZ cell exists, and every checker you put down is one more target for
the next detonation. A total-material term was measured too (+0.24 / +0.04 — noise)
and is deliberately left out. `selftest.py` pins both the values and the direction,
including the paired greedy match against the flipped sign, because a sign flip passes
every shape, range, zero-sum and seat-symmetry check.

### Not implemented

* **The pie rule.** AbstractPlay offers one as a site convention; Steere's sheet has no
  swap rule, so this port has none.

### Reading the board

* Each stack is drawn as a **side-view tower of checkers with a height badge** — the
  platform's standard stacking glyph. Height is the whole game (it is the blast radius,
  and it is what restriction 2 compares), so it is never left implicit.
* Every cell inside a radiation exclusion zone is **tinted** — reddish for Red's zones,
  bluish for Blue's, purple where they overlap (the same convention as Figure 1). The
  untinted empty cells are precisely the cells you may place on; when there are none,
  the caption says the board is saturated and you must build.
* The last placement and the stacks it blew away are highlighted.
