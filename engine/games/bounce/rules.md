# Bounce

**Mark Steere, August 2023.** Two players, no captures, no draws.
Official rule sheet: [marksteeregames.com/Bounce_rules.pdf](https://marksteeregames.com/Bounce_rules.pdf) — the rules below are the rules *as implemented here*.

## Board and setup

A square board of **any even size**. This package ships **6×6, 8×8 (default) and 10×10**.

The board starts **completely full** with a checkerboard pattern of Red and Blue
checkers — **except the four corner squares, which are empty**. On 8×8 that is
30 checkers each and exactly four empty squares.

```
 8  .  B  R  B  R  B  R  .
 7  B  R  B  R  B  R  B  R
 6  R  B  R  B  R  B  R  B
 5  B  R  B  R  B  R  B  R
 4  R  B  R  B  R  B  R  B
 3  B  R  B  R  B  R  B  R
 2  R  B  R  B  R  B  R  B
 1  .  R  B  R  B  R  B  .
    a  b  c  d  e  f  g  h
```

Because the board is even-sized, two corners fall on each colour of the
underlying chequering, so both players lose exactly two squares and the setup is
perfectly symmetric. **Red moves first.**

## Group

A **group** is a monocoloured, **orthogonally** interconnected set of checkers.
Diagonal contact does *not* connect. A single isolated checker is a group of one.

## Play

On your turn you **move one of your checkers to any unoccupied square on the
board**. This is a *teleport*, not a step — the destination need not be anywhere
near the checker you pick up.

> **The checker you move must be part of a strictly LARGER group after your move
> than it was before your move.**

Only the *moved checker's own* group sizes are compared. What happens to the
group it left — it may shatter into fragments — does not matter.

**Worked example (Figure 3 of the rule sheet).** Red moves the checker on **h7**
to **e1**. Before the move that checker sits in a Red group of **11**; after the
move it sits in a Red group of **20**. 20 > 11, so the move is legal. (Both
numbers are asserted in this package's `selftest.py`.)

## Checker removal

**If you have no legal move at all on your turn, you must instead remove any one
of your own checkers from the board, which concludes your turn.**

This is never optional: removals are offered *only* on a turn with no legal move,
and then every one of your checkers is a legal choice.

## Object

**If, at the conclusion of your turn, all of your checkers are in one group, you
win.**

## Rulings and interpretations

Everything below was decided against the official sheet and cross-checked
against [AbstractPlay's independent implementation](https://github.com/AbstractPlay/gameslib)
(`src/games/bounce.ts`), whose move list this package matches exactly over 440
plies of whole-game differential play on 8×8 and 10×10.

| Question | Ruling here | What settled it |
|---|---|---|
| Whose unification is checked at the end of a turn? | **Only the player who just moved.** | The sheet says "at the conclusion of **your** turn"; AbstractPlay tests only the previous player. It also cannot matter: groups are monocoloured and adjacency is direct, so **a player's group structure can only change on that player's own turn**. Since neither side starts unified, "check the mover" and "check both" are the same rule. |
| Can both players be unified at once (a draw)? | **Impossible**, so there is no tiebreak to fabricate. | Same argument — your groups never change while your opponent is moving, so you would already have won at the end of your own previous turn. |
| Is a lone checker "one group"? | **Yes — it wins.** | "All of your checkers are in one group" is satisfied vacuously by one checker; AbstractPlay agrees (one connected component). |
| Can a player be reduced to zero checkers? | **No.** | Material only ever drops on your own removal, by one, and the win test fires at the end of that same turn — so the removal that takes you from 2 to 1 wins the game before you can go to 0. Zero checkers is therefore unreachable; it is also *not* treated as a win (no checkers, no group). |
| Is a move a step, or a teleport? | **A teleport to any empty square.** | The sheet says only "moving one of their checkers to an unoccupied square", with no adjacency language, and AbstractPlay pairs every own checker with every empty square. It is directly visible in the opening: all 60 of Red's first moves land on **a1** or **h8**, the far corners. |
| Draws | **None exist.** | The game is finite (below), every turn always has a legal action, and it can only end by somebody unifying. |
| Pie / swap rule | **Not implemented.** | AbstractPlay tags the game with its platform-wide `pie` flag, but Steere's sheet contains no swap rule, and the sheet outranks the oracle. |
| Board size | 6 / 8 / 10, default 8. | The sheet allows "any even size"; the figures and AbstractPlay's default are 8×8, and AbstractPlay also ships 10×10. Sizes below 4 are rejected — on a 2×2 board every square is a corner. |

## Why the game must end (no ply cap, no repetition rule)

Checkers move freely to any empty square, so positions *could* in principle
repeat — but they cannot, and this package therefore carries **no ply cap and no
repetition rule at all**. The proof:

Write **S** for the multiset of one player's group sizes in **descending** order.
A move takes the moved checker out of its group **A** (size *a*), possibly
shattering A into fragments (each smaller than *a*), and drops it where it merges
with some groups **C₁…C_k** and possibly some of those fragments, forming a new
group of size *b*. The rule demands **b > a**.

Every size *removed* from S is either *a* (which is < b by the rule) or some
*C_i* (which is < b, since b ≥ 1 + C_i). Every size *added* is either *b* itself
or a fragment (< a < b). So S and S′ agree on the count of every value strictly
greater than *b*, and at the value *b* itself S′ has one more. Hence **S increases
strictly lexicographically on every one of that player's moves** — and the
opponent's turns leave it untouched.

Since a player's checker count is fixed between removals, and there are only
finitely many multisets for a given count, only finitely many moves can happen
between two removals; and a player can only remove as many checkers as they have.
The game is therefore finite. Measured over 2,000 random 8×8 games: **23–73
plies**, median 41; across roughly 5,500 random games at 6×6 / 8×8 / 10×10 the
longest seen was **112 plies** (on 10×10). Independently, the smallest legal
board (4×4) was solved by memoised negamax over 29,602 distinct positions with
an explicit on-line repetition assertion: no position ever recurs on a line,
every line terminates, and perfect play there is a **second-player win**.

A corollary of the same argument is that a player's **largest** group size never
shrinks while their material is constant — and "largest group = all my checkers"
is exactly the win condition.

## How this differs from Ayu

Both games start with a filled board and are won by gathering your stones into
one orthogonal group, but the moves are opposites:

- **Ayu** moves a stone one step to an *adjacent* empty point (or extrudes it
  from a group without splitting that group), and every move must *approach* the
  nearest friendly unit. **Bounce** teleports a checker to any empty square on
  the board and only cares that the checker lands in a bigger group.
- **Ayu** is won by the player who *cannot move*; **Bounce** punishes a player
  who cannot move by making them **destroy one of their own checkers**, and is
  won outright by unifying.
- Ayu never removes stones; Bounce's material is a one-way ratchet downwards.

## Notation and controls

- A move is `from>to` — click your checker, then the empty square.
- A forced removal is a single cell id — on a turn with no legal move, click the
  checker you want to remove (the board caption tells you when this is the case).
- The move log shows `h7-e1 (11→20)`: the moved checker's group size before and
  after. A removal reads `xe4 (no legal move)`.
