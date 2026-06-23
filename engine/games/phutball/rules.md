# Phutball (Philosopher's Football)

**Phutball** is John H. Conway's game, published in *Winning Ways for Your
Mathematical Plays*. It is played with shared neutral **men** (stones owned by
neither player) and a single **ball** on a grid of **points**.

## Board and goals

- The board is a grid of points; the default size is **15 wide × 19 tall**
  (also offered: 15×21, and the classic wide **19×15**). Coordinates are `c,r`
  with column `c` = 0…W−1 and row `r` = 0…H−1.
- The two **goal lines** are the short edges:
  - **row H−1** (bottom) is **Player 0's** target,
  - **row 0** (top) is **Player 1's** target.
  They are highlighted (red = bottom, blue = top).
- The **ball** starts on the centre point (`⌊W/2⌋,⌊H/2⌋`).
- The players are identical except for **which goal they aim the ball at** — the
  men are neutral and belong to neither.

## A turn — place OR jump (never both)

On your turn you do **exactly one** of:

**(A) Place a man.** Put one man on any **empty** point (not the ball's point).
Men are neutral.

**(B) Jump the ball.** Make a chain of **one or more jumps**, then stop.
A single jump: from the ball, choose one of the **8 directions** (orthogonal or
diagonal). If the immediately adjacent point(s) in that direction form an
**unbroken line of one or more men** ending at an **empty** point, the ball hops
to that empty point and **every jumped man is removed** from the board.

- After landing you **may jump again** from the new point in **any** direction.
- You **choose when to stop** the chain (the whole chain is one turn).
- A jump over a **gap** (an empty point in the line) or that would run **off the
  board edge** (other than across your own goal — see below) is **illegal**.
- You may **not** both place a man and jump in the same turn.

## Winning — on or over the goal line

You **win** when, as a result of **your** move, the ball lands **on or over your
goal line**:

- **Player 0** (bottom) wins if the ball lands on a point with **r ≥ H−1**,
  i.e. on the bottom goal row, or a jump carries it **past** that edge.
- **Player 1** (top) wins if the ball lands with **r ≤ 0**, i.e. on the top goal
  row, or a jump carries it **past** that edge.

A jump may end **over** the goal line — landing just past the edge (encoded as
row `−1` or `H`) — and this also wins, as long as the landing column is still
within the board. A jump that leaves the board across **any other edge** is not
allowed.

Note: the ball reaching the **opponent's** goal line on your move does **not**
lose for you here — only **your own** target line wins, and only on **your** move.

## Playing a jump in the app

A jump **chain** is played as a sequence of **single hops by the same player**:
click the ball's next landing point, and if more men are reachable you may click
again to keep jumping (in any direction). Once you have hopped at least once, a
**Stop** action appears — use it to end your ball turn and pass. (Engine note: a
single move string is one hop, `"c,r"`, plus the action `"stop"`; the move log
reconstructs the full path. This keeps the move list small even when many men
are on the board.)

## Termination

Phutball is finite in practice. As a defensive safety net this implementation
declares a **draw** if 600 plies pass with no win (a ply is one placement or one
ball hop).

## Ruleset notes / choices (flagged)

- **Board orientation.** Conway's original is usually drawn **wide** (like a
  football pitch, e.g. 19 wide × 15 tall) with goals on the short left/right
  ends. Sources differ on exact dimensions; common references cite a ~15×19 or
  19×15 point grid. This package defaults to a **tall 15×19** board with goals on
  the **top and bottom** short edges, and offers the classic **19×15** wide
  board as an option. The play is identical up to rotation.
- **"On vs over" rule.** The standard rule is that the ball must reach **on or
  beyond** the goal line. We implement: a jump landing **exactly on** your goal
  row wins, and a jump that carries the ball **just past** the edge (one row
  beyond) also wins — matching the "lands on or over the goal line" wording in
  Winning Ways. The over-the-edge landing column must remain within the board's
  columns.
- **Goal-line points are normal points.** The goal rows hold men and can be
  jumped from/over like any other row; what matters for a win is where the ball
  *lands* on the mover's turn.
- **Off-board jumps** are illegal except a winning jump across the mover's own
  goal line.
- **Chain modelling.** A faithful Phutball jump chain can be arbitrarily long, so
  enumerating every complete chain as a distinct move would blow up on dense
  boards. We instead model a chain as repeated **single hops by the same player**
  with an explicit **Stop**, which is rule-equivalent (the mover still freely
  chooses each hop and when to stop) and keeps the legal-move list bounded.
