# Six Men's Morris

Six Men's Morris is the smaller member of the morris (mill) family, played on a
board of **16 points** — two concentric squares joined by spokes at the middle of
each side. The rules **as implemented** here follow the standard game.

## The board

The 16 points sit on the corners and side-midpoints of the **two** squares (the
outer and the inner). Two points are **adjacent** when a line joins them directly:
along the edges of each square, and along the four spokes that connect the
mid-side point of the outer square to the mid-side point of the inner square.
Corners are **not** joined across squares, there is no middle ring, and the centre
is not a point.

A **mill** is three of your men in a row along one of the **8 lines** — the four
sides of the outer square and the four sides of the inner square. The spokes are
**not** mills (each spoke joins only two points).

## Phase 1 — placing

Each player has **six men**. Players alternate **placing** one man on any empty
point (White first). Whenever you complete a mill — in this phase or the next —
you immediately **remove one of the opponent's men** from the board.

## Phase 2 — moving

Once all twelve men have been placed, players alternate **moving** one man along a
line to an **adjacent empty point**. Completing a mill again removes an enemy man.

There is **no flying** in Six Men's Morris: you must always move to an adjacent
point, even when you are reduced to three men.

## Removing a man

When you form a mill you remove one enemy man of your choice, with one
restriction: **you may not take a man that is part of a mill, unless every enemy
man is in a mill** (then any may be taken). Forming **two mills at once** still
removes only **one** man.

## Winning and drawing

You **win** when the opponent is reduced to **two men** (too few to form a mill),
or when the opponent has **no legal move** on their turn. These loss conditions
apply only once the placing phase is over.

The game is a **draw** by repetition (the same position, with the same player to
move, occurring a third time) or if **50 plies** pass with no mill formed and no
man placed (a no-progress rule that also guarantees the game ends).

## Notation

During placing, a move is a single point like `3,0` (shown as `@3,0` in the log).
During moving, it is `from>to`, e.g. `3,0>3,2` (shown as `3,0-3,2`). When you form
a mill, your next click removes an enemy man (shown as `x3,2`). Points are named
by their `x,y` coordinate on the board diagram.
