# Gobblet

*Designer: Thierry Denoual (Blue Orange Games, 2001).* A nesting take on
tic-tac-toe: line up four of your colour, but a bigger cup can **gobble**
(cover) a smaller one, and lifting a cup **uncovers** whatever hid beneath it.

## Equipment

- A **4×4** board (cells `c,r`, both `0..3`).
- Each player owns **12 cups** held as **three off-board stacks** of four cups
  each, nested by size **4 (big) > 3 > 2 > 1 (small)**. Only the **largest
  remaining** cup of each stack is available to play; under it wait the smaller
  cups, in order. So at the start each player may place a **size-4** cup from
  any of their three stacks.

A cell holds an ordered **nest** of cups; only the **top** (visible) cup
counts and can be controlled. What is underneath is hidden, exactly as with the
physical wooden cups.

## A turn

On your turn do **exactly one** of:

1. **Place** the top cup of one of your off-board stacks onto the board —
   move notation `"<size>@c,r"` (e.g. `"4@1,2"`).
2. **Move** one of your cups that is currently the **top** of some cell to
   another cell — `"c,r>c2,r2"` (e.g. `"1,2>3,3"`). Lifting the cup **uncovers**
   the cup beneath its old cell (which may be your opponent's).

## Gobbling (covering)

A cup may land on:

- an **empty** cell, or
- a cell whose **top** cup is **strictly smaller** (`size > covered size`).

You may gobble **any** smaller cup — your own or your opponent's — and it need
not be the next size down (a 4 may cover a 1). Cups already **on the board move
and gobble freely** within these size limits.

### The off-board-gobble restriction

A cup placed **from off the board** may cover an **opponent's** on-board cup
**only if** that opponent cup is part of a **line (row, column, or diagonal) in
which the opponent already shows three cups of their colour on top**. This is
the standard anti-trivial rule: you may dive in from your reserve to block a
three-in-a-row, but you cannot otherwise smother loose enemy cups with fresh
cups. (A drop onto an **empty** cell or onto **your own** smaller cup is always
allowed.)

## Winning

You win when **four cups of your colour are showing on top** along a row,
column, or diagonal. The cups need not be the same size.

Because **uncovering changes which cup is on top**, the position is judged
**after every move**:

- If your move completes **your** four-in-a-row → **you win**.
- If your move — by uncovering — reveals a four-in-a-row of **only your
  opponent's** colour → **your opponent wins** (you lost by exposing their
  line; you must avoid moves that do this unless they also win for you).
- **Tie-break:** if a single move completes a four-in-a-row for **both** colours
  at once, the **mover wins**. Rationale: you completed your own line, which is
  the line you were building; your win takes priority over a line you merely
  uncovered. (This is a documented implementation choice; the printed rules cover
  the asymmetric uncover case but leave the simultaneous case ambiguous.)

## Termination

Gobblet has no natural draw and cups can shuffle forever. As a defensive guard
this implementation declares a **draw** if **400 plies** pass with no win.

## Variant: Gobblet Gobblers (3×3)

The kids' edition. Set the **Variant** option to *Gobblet Gobblers*: a **3×3**
board, **6 cups per player = two stacks of three** (sizes `1..3`), and **no
off-board-gobble restriction** (drops may freely cover any smaller cup). Win by
three-in-a-row of your colour showing on top. All other mechanics (nesting,
strictly-larger gobble, uncovering, the same-move tie-break) are identical.
