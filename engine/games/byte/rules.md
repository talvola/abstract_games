# Byte

*Mark Steere, 2005* — a merge-only **stacking** game played with a standard
Checkers set. Rules as implemented here, from the designer's official rule
sheet ([marksteeregames.com](https://www.marksteeregames.com/Byte_rules.pdf)).
Steere designed Byte to be **drawless**: exactly three stacks of 8 form during
the game, and one player must win a majority of them.

## Board and setup

- Only the **32 dark squares** of an 8×8 checkerboard are used (here: cells
  `c,r` with `c+r` odd).
- Standard checkers setup: **White** fills the dark squares of rows 0–2 (12
  checkers), **Black** the dark squares of rows 5–7 (12 checkers).
- **White moves first.**

## Stacks

A square holds a **stack** of 1–8 checkers, in any colour mix and order.
Checker positions in a stack are **levels**, counted from the bottom (level 1).

The instant a stack of **exactly 8** forms it is removed from the board and
scored for the owner of its **top** checker. Three stacks of 8 form over the
course of the game; the player who wins the **majority (2 of 3)** wins.
(This implementation ends the game as soon as a player scores their 2nd
stack — the majority is then decided.)

## Moving

Movement is **mandatory**: if you have any legal move you must make one, even
a self-damaging one. If you have none, you must **pass** (and keep passing
until you can move again). There are two kinds of move:

### Basic move (isolated stacks only)

If a stack is **not diagonally adjacent to any other stack**, and you own its
**bottom** checker, you may slide the **entire** stack one square diagonally —
but it **must move closer to its closest stack**.

- Distance between stacks = the number of one-square diagonal moves needed to
  get from one to the other (Chebyshev distance `max(|dc|,|dr|)`; board edges
  never lengthen a shortest path on the 8×8, and intervening stacks are
  ignored — the rule sheet measures pure distance).
- If two or more stacks tie as closest, you may move closer to **any one** of
  them.
- Two adjacent stacks may **never** move to an unoccupied square.

### Merging (adjacent stacks)

If stacks A and B are diagonally adjacent and you have a checker anywhere in
A, you may pick up **your** checker together with **all checkers on top of
it** and place that portion on top of B (order preserved). Two conditions:

1. Your picked checker must land at a **strictly higher altitude** (level)
   than where it started — never the same level or lower.
2. The result may **not exceed 8** checkers.

Note the merged stack's new top is the top of the *moved portion* — which may
be an enemy checker, so a forced merge can hand your opponent a stack of 8.

## Move encoding

- Basic move: `c,r>c,r` (whole stack, one diagonal step).
- Merge: `c,r>c,r=n` where `n` = the number of checkers moved (the **top n**
  of the source stack; the picked checker is the portion's bottom).
- No legal move: the single legal move is `pass`.

## End of the game

First player to score **2 stacks of 8** wins. Genuine draws cannot occur.

*Engine safeguard only:* to guarantee termination under arbitrary play, 100
consecutive plies without a merge (or 1000 total plies) end the game as a
draw. In real play stacks are forced toward each other and must merge, so
this never triggers; it exists to bound pathological shuffle sequences.
