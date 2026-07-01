# Lasker Morris (Ten Men's Morris)

Lasker Morris is Emanuel Lasker's improved version of **Nine Men's Morris**,
described in his 1931 book *Brettspiele der Völker*. It is played on the **same
24-point board** — three concentric squares joined by spokes at the middle of
each side — and shares almost every rule, with two changes that make the game
noticeably more dynamic. The rules **as implemented** here are documented below.

## The board

The 24 points sit on the corners and side-midpoints of the three squares. Two
points are **adjacent** when a line joins them directly: along the edges of each
square, and along the four spokes that connect the middle square to the points
just inside and outside it. Corners are **not** joined across squares, and there
are no diagonals. A **mill** is three of your men in a row along one of the 16
lines (four edges on each of the three squares, plus the four spokes).

## What Lasker changed

1. **Ten men each** instead of nine.
2. **No rigid two-phase structure.** In plain Nine Men's Morris you must place
   all nine men first and only then may you slide. In Lasker Morris there is no
   such split: **on every turn, as long as you still have men in hand, you may
   *either* place a new man on any empty point *or* slide an already-placed man
   to an adjacent empty point.** Placing and moving are freely interleaved from
   the very first move. Only once your hand is empty are you restricted to
   sliding. This interleaving is Lasker's improvement — it removes the mechanical
   opening of the classic game.

## Forming a mill and removing a man

Whenever a placement or a slide completes a mill (three of your men along a
line), you immediately **remove one of the opponent's men** of your choice, with
one restriction: **you may not take a man that is part of a mill, unless every
enemy man on the board is in a mill** (then any may be taken). Forming **two
mills at once** still removes only **one** man.

## Flying

**Flying:** when you are reduced to exactly **three men** (all placed, none left
in hand), you may move a man to *any* empty point, not just an adjacent one. This
is the common optional rule and the default here; it can be turned off with the
*Flying* option, in which case you must always move to an adjacent point. Sources
for Lasker Morris differ on whether flying applies — the option lets you choose.

## Winning and drawing

You **win** when the opponent is reduced to **two men** (counting men still in
hand — too few to ever form a mill again), or when the opponent has **no legal
move** on their turn.

The game is a **draw** by repetition (the same position, with the same player to
move, occurring a third time) or if **50 plies** pass with no mill formed and no
man placed (a no-progress rule that also guarantees the game ends).

## Notation

A **placement** is a single point like `3,0` (shown as `@3,0` in the log). A
**slide** is `from>to`, e.g. `3,0>3,1` (shown as `3,0-3,1`). When you form a
mill, your next click removes an enemy man (shown as `x3,2`). Points are named by
their `x,y` coordinate on the board diagram.
