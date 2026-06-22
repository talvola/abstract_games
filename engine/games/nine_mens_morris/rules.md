# Nine Men's Morris

Nine Men's Morris is a classic mill game played on a board of **24 points** —
three concentric squares joined by spokes at the middle of each side. The rules
**as implemented** here follow the standard game.

## The board

The 24 points sit on the corners and side-midpoints of the three squares. Two
points are **adjacent** when a line joins them directly: along the edges of each
square, and along the four spokes that connect the middle squares to the points
just inside and outside them. Corners are **not** joined across squares, and the
centre is not a point.

A **mill** is three of your men in a row along one of the 16 lines (four edges on
each of the three squares, plus the four spokes).

## Phase 1 — placing

Each player has **nine men**. Players alternate **placing** one man on any empty
point (White/red first). Whenever you complete a mill — in this phase or the next
— you immediately **remove one of the opponent's men** from the board.

## Phase 2 — moving

Once all eighteen men have been placed, players alternate **moving** one man along
a line to an **adjacent empty point**. Completing a mill again removes an enemy
man.

**Flying:** when you are reduced to exactly **three men**, you may move a man to
*any* empty point, not just an adjacent one. (This is the standard rule and the
default; it can be turned off with the *Flying* option, in which case you must
always move to an adjacent point.)

## Removing a man

When you form a mill you remove one enemy man of your choice, with one
restriction: **you may not take a man that is part of a mill, unless every
enemy man is in a mill** (then any may be taken). Forming **two mills at once**
still removes only **one** man.

## Winning and drawing

You **win** when the opponent is reduced to **two men** (too few to form a mill),
or when the opponent has **no legal move** on their turn. These loss conditions
apply only once the placing phase is over.

The game is a **draw** by repetition (the same position, with the same player to
move, occurring a third time) or if **50 plies** pass with no mill formed and no
man placed (a no-progress rule that also guarantees the game ends).

## Notation

During placing, a move is a single point like `3,0` (shown as `@3,0` in the log).
During moving, it is `from>to`, e.g. `3,0>3,1` (shown as `3,0-3,1`). When you form
a mill, your next click removes an enemy man (shown as `x3,2`). Points are named
by their `x,y` coordinate on the board diagram.
