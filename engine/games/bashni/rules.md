# Bashni (Башни, "Towers")

**Bashni** is Russian **column draughts** — the stacking ancestor of Lasca. As in
ordinary Russian draughts, captured pieces are **not removed from the board**;
they become **prisoners** stacked under the piece that took them, forming
**columns** (towers). These are the rules **as implemented** here.

## Board and pieces

Play is on the **32 dark squares** of an **8×8** board. Each player starts with
**12 men**, on the dark squares of their nearest three rows (White at the bottom,
Black at the top) — the standard draughts opening.

A **column** (tower) is a stack of one or more pieces, ordered bottom → top. A
column is **controlled by whoever owns its top piece**, and only that top piece's
powers count. The column's colour and king-status are those of its top piece.

## Moving

- A **man** moves one square **diagonally forward** to an empty square.
- A **king** (a promoted man) is a **flying king** (Russian rules): it slides
  **any distance** along a free diagonal, like a chess bishop.

A whole column moves as a unit; its controlling top piece decides how it may go.

## Capturing — the Bashni tower rule

If you can capture, you **must**. Capturing tucks a prisoner under your column:

1. You jump diagonally over an adjacent (man) or distant (king) square whose
   column is **enemy-controlled** — i.e. has an enemy piece on top — landing on an
   empty square beyond it.
2. The **top piece of the jumped column is removed from it and placed at the
   BOTTOM of your moving column** as a prisoner. The moving column therefore grows
   by exactly **one** piece per jump.
3. The **rest of the jumped column stays where it is**. If it still has pieces, it
   is now controlled by whoever its *new* top piece is — so capturing an enemy top
   can **liberate** a friendly piece that was buried beneath it.

Capture details (Russian geometry):

- A **man captures forward *or* backward** — it jumps an adjacent enemy column in
  any of the four diagonal directions, landing one square beyond.
- A **king captures at any distance** (flying king): it slides along a diagonal
  over empty squares to the first enemy column, then lands on **any** empty square
  beyond it.
- Captures are **mandatory** and **chained**: if the moving column can jump again
  after landing, it **must continue**, and the whole multi-capture is played as a
  **single move**.

(This implementation enforces that a capture move, once begun, is run to a square
from which no further capture is possible. It does **not** impose a
maximum-capture / quantity-or-quality priority rule between *different* capture
chains — any legal complete capture chain may be chosen, as in many casual Bashni
rule sets.)

## Promotion (ruleset choice)

A man becomes a **king** when it reaches the opponent's back rank
(row 7 for White, row 0 for Black) — only the **top** piece of the column is
promoted.

Following the standard **Russian** rule, promotion happens **the instant** the man
reaches the far rank: if it arrives there *during* a capture and further captures
are then available **as a king** (i.e. using the flying-king reach), the man
promotes immediately and **continues the same multi-capture as a king**. A man that
merely passes over the far rank mid-jump without stopping there is not affected;
promotion is keyed to actually landing on a far-rank square.

## Winning and draws

A player **loses** if, on their turn, they **control no column** or have **no legal
move** (all their columns are blocked). Their opponent wins.

To guarantee the game terminates, it is a **draw** after **60 plies with no capture
and no promotion**, by **threefold repetition** of the position, or at a hard ply
cap.

## Notation

A move is a `>`-path of squares, shown as `a-b` for a step and `a x b x c…` for a
jump chain. Squares are named by their `c,r` coordinate (column,row). In the app
each square's column is drawn as a stack of owner-coloured bands with a height
badge; a king on top is marked `K`.
