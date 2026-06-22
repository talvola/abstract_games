# Lasca (Laska)

Lasca was invented by the world chess champion **Emanuel Lasker** in 1911. It is
draughts with **towers**: captured pieces are not removed — they are imprisoned
beneath the piece that took them. These are the rules **as implemented** here.

## Board and pieces

Play is on the **25 dark squares** of a 7×7 board. Each player starts with **11
men**, on the dark squares of their nearest three rows (White at the bottom, Black
at the top). A **column** (tower) is a stack of one or more pieces; it is
**controlled by whoever owns its top piece**, and only that top piece's powers
matter.

## Moving

- A **man** moves one square **diagonally forward** to an empty square.
- An **officer** (a promoted man) moves one square diagonally **in any direction**.

A whole column moves as a unit; the controlling top piece decides how it may go.

## Capturing (the tower rule)

If you can capture, you **must**. You capture by jumping diagonally over an
adjacent enemy-controlled column to the empty square just beyond — exactly as in
draughts — but instead of removing anything you take **only the top piece** of the
jumped column and tuck it under the **bottom** of your moving column as a
prisoner. The rest of the jumped column **stays where it is** (now possibly under
new control). Taking the enemy top can therefore **liberate** a friendly piece
that was trapped underneath.

- A **man** captures forward only; an **officer** captures in any diagonal
  direction.
- If, after a jump, the same column can jump again, it **must continue** — a
  multi-capture is played to its end as a single move.

## Promotion

A man that **ends its move on the far row** is promoted to an officer (only the
top piece is promoted). Passing through the far row mid-capture does not promote.

## Winning and draws

A player who has **no legal move** on their turn (no controlled columns, or all of
them blocked) **loses**. To guarantee termination, the game is drawn after 40
plies with no capture and no promotion, by threefold repetition, or at a hard ply
cap.

## Notation

A move is a `>`-path of squares, shown as `a-b` for a step and `a x b x c…` for a
jump chain. Squares are named by their `c,r` coordinate. In the app each square's
column is drawn as a stack of owner-coloured bands with a height badge; an officer
on top is marked `O`.
