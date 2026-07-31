# Clusterfuss

**Mark Steere, July 2023.** Two players, no chance, no hidden information.
Rules as implemented by this package; the official rule sheet is
[Clusterfuss_rules.pdf](https://marksteeregames.com/Clusterfuss_rules.pdf).

Steere notes on the sheet that Clusterfuss is predated by a similar game,
**Advanced Forms (2011) by Steven W. Meyers**.

## Setup

A square board of any size, **completely filled** with checkers in a strict
checkerboard pattern. **Red** takes the top-left cell; colours alternate from
there, so no two orthogonally adjacent checkers start the same colour. This is
Figure 1 of the rule sheet (drawn there on a 4x4):

```
  R  B  R  B
  B  R  B  R
  R  B  R  B
  B  R  B  R
```

**Red moves first.** The default board is **8x8** (64 checkers, 32 each);
4x4, 5x5, 6x6 and 10x10 are also offered — see *Board size* below.

## Object

**Remove all enemy checkers from the board.**

## Moves

Every move is an **orthogonal king capture**. You move one of your own checkers
one step up, down, left or right onto an **occupied** cell, capturing whatever
stood there by replacement. There are no non-capturing moves and no diagonal
moves, so the board loses at least one checker every single turn.

**You may capture a friendly checker as well as an enemy one.** That is not a
curiosity — the rule sheet devotes two puzzle figures to positions where the
*only* winning move is a friendly capture (see *The friendly-capture puzzles*).

Passing is not allowed. The sheet adds that a player with no available move has
their turn skipped; in Clusterfuss that clause turns out to be **vacuous** (see
*Notes on interpretation*), so in practice the players simply alternate.

## Groups

A **group** is a maximal set of checkers connected orthogonally — horizontally
or vertically. **Diagonal adjacency is irrelevant**, and a group **may contain
checkers of either or both colours**. Connectivity in Clusterfuss is
colour-blind, which is unusual: in most connection games a group is one colour.

At the conclusion of your turn there must be only **one group on the board**.

## Move restriction

You may only play a move such that, after it, there is exactly **one group
containing your checkers** (that group may also contain enemy checkers).

Figure 2 of the sheet — Red to move:

```
  .  R  R  .
  B  R  B  .
```

Red **can** capture the blue checker on the right, but **cannot** capture the
blue checker on the left: that would leave the two upper reds in one group and
the capturing red in another, i.e. two groups containing red checkers.

## Enemy-only group removal

If your move detaches groups made up **only of enemy checkers**, those groups
are **removed from the board immediately**, concluding your turn.

Figures 3a, 3b and 3c — Red to move, then captures the blue checker on the
right:

```
  3a (before)      3b (after the capture)     3c (after removal)
  .  B  .  .          .  B  .  .                 .  .  .  .
  B  R  B  .          B  .  R  .                 .  .  R  .
  B  B  .  .          B  B  .  .                 .  .  .  .
```

The capture detaches **two** enemy-only groups — the lone blue above and the
three-checker blue group at the left — both are removed at once, and Red has
removed every enemy checker and won.

Note how the two rules fit together: because the move restriction guarantees
that exactly one group holds your checkers, *every other group on the board is
enemy-only*, so removal always leaves exactly one group. The GROUPS paragraph's
"only one group on the board" is therefore a consequence of the (weaker,
precise) MOVE RESTRICTIONS wording, not a separate constraint.

**Order of resolution used by this implementation:**

1. Move your checker X onto the adjacent occupied cell Y; Y now holds your
   checker and X is empty.
2. Recompute the groups of the whole board (colour-blind).
3. **Legality:** exactly one group may contain your checkers. Otherwise the
   move was never legal and is not offered.
4. Remove every group that holds no checker of yours.
5. Your turn ends.

Steps 3 and 4 are order-independent — a group that holds none of your checkers
cannot be the group that holds your checkers — so the wording of the two
paragraphs never actually conflicts.

## Winning

The player who removes the last enemy checker wins. Because the checker you
move always survives, you can never wipe *yourself* out, and both colours can
never disappear on the same move.

## The friendly-capture puzzles

Figures 5 and 6 of the sheet are stated as puzzles: *"In both examples, Red can
capture a friendly checker and then have a path to winning. But if Red were to
capture an enemy checker instead, Blue would have a path to winning."*

```
  Figure 5 (Red to move)      Figure 6 (Red to move)
  R  .  .  .                  .  .  R  .
  R  B  B  R                  .  R  R  .
                              .  B  B  .
```

Both positions are **solved exhaustively** in this package's `selftest.py`, and
the sheet's claim holds exactly:

| Figure | Red's moves | Value for Red |
|---|---|---|
| 5 | friendly capture (top red takes the red below it) | **win** |
| 5 | the only enemy capture | **loss** |
| 6 | friendly capture (top red takes the red below it) | **win** |
| 6 | the other friendly capture | loss |
| 6 | the only enemy capture | **loss** |

(The sheet says Red *can* win with a friendly capture, not that every friendly
capture wins — Figure 6 has one of each, which is consistent.)

## Board size

The sheet says "a square board of any size". This package offers **4, 5, 6, 8
(default) and 10**. Eight matches the reference implementation on AbstractPlay.

An **odd** board cannot be filled with a balanced checkerboard: all four corners
take the same colour, so on 5x5 **Red starts with 13 checkers to Blue's 12** and
also has the first move. That is why the odd size is labelled as such in the
lobby; even boards split the material exactly.

## Notation

A move is written `from>to` in `col,row` cell ids, e.g. `3,4>3,5` — column 0 is
the left file, row 0 is the bottom rank. In the move log a capture of your own
checker is marked `(own)`, and a move that detaches enemy groups shows how many
checkers it swept away, e.g. `R 1,1x2,1 [4 cut off] wins`.

## Notes on interpretation

* **Termination is proved, not capped.** Every move removes at least one
  checker and no move ever adds one, so a game lasts at most `n*n - 1` plies
  (63 on the standard board). There is no repetition rule and no ply cap, so no
  cap can be outcome-load-bearing. The bound is tight: 4x4 games really do reach
  15 plies.
* **Nobody is ever skipped.** After any legal move exactly one group survives,
  so the board is always a single connected group. In a connected group, take
  the spanning tree of the cells and consider the subtree spanned by one
  player's checkers: a leaf X of that subtree is one of their checkers, removing
  X leaves all their other checkers in a single component, and that component
  touches X — so X has a legal move. Every player holding a checker therefore
  always has a move, and the sheet's skip clause can never fire. The engine
  still implements it (a skipped turn simply returns the move to the other
  player) as a defensive measure.
* **There are no draws in practice.** If both players were somehow immobile the
  engine scores an honest draw (`0-0`, no winner) rather than inventing a
  tiebreak, but the argument above shows that state is unreachable: none of the
  ~450 random games in the selftest, at any board size, ended in anything but a
  win. A decisive result always outranks that draw.
* **No swap / pie rule.** The rule sheet has none, so this package has none.
  (AbstractPlay's implementation offers an optional pie swap as a site-level
  convenience; that is not part of Steere's rules.)
* **Figure numbering.** The official sheet's figures run 1, 2, 3a, 3b, 3c, 5, 6
  — there is no Figure 4. That is a quirk of the sheet, not a missing diagram.
* **Rule-sheet revisions.** The Wayback Machine holds one snapshot of the sheet
  (2023-10-03) and it is byte-identical to the live PDF, so there is no
  superseded revision to reconcile.

## Correctness anchors

* Figure 1 (the setup), Figure 2 (the move restriction, with its full legal-move
  set frozen) and Figures 3a-3c (enemy-only removal of exactly two groups,
  ending in the lone red checker) are reproduced cell by cell.
* Figures 5 and 6 are **solved exhaustively** and the designer's published
  claim about them is asserted move by move — a whole-ruleset end-to-end check.
* The opening move count is **112** on the standard 8x8 board, matching the
  independent AbstractPlay implementation.
* A move-for-move differential against that implementation (legal-move sets,
  post-removal boards, winners) was run over complete random games on the 8x8
  and 10x10 boards, driven from both sides, with deliberately broken variants
  required to diverge.
