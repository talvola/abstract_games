# Ordo

**Designer:** Dieter Stein (2009), published by nestorgames.
**Players:** 2 · **Board:** 10 × 8 (10 files `a`–`j` wide, 8 ranks tall).

Rules as implemented here, following the designer's official rules at
[spielstein.com/games/ordo/rules](https://spielstein.com/games/ordo/rules).

## Goal

Be the first to land one of your men on the **opponent's home row** (the far row
from your side). You also win by capturing all of the opponent's men, or by
splitting the opponent's group so they cannot put it back together.

## Setup

Each player has **20 men**, arranged in a crenellated two-row "battlement" on
their side of the board (columns come in pairs; alternate pairs sit one rank
higher). White (player 0) starts at the bottom and moves first; Black (player 1)
starts at the top. This is one single, diagonally-connected group for each side.
Players may not pass.

## The group — the connection rule

Your **group** is *all* of your men. It must always be connected in **one sole
group** by 8-connectivity — men count as joined if they are orthogonally *or*
diagonally adjacent. **After every move of yours, your men must form one
connected group.** A single lone man counts as a connected group.

A move that would leave your men in two or more separate clusters is illegal.

## Moves

There are two kinds of move.

### Singleton move

A single man slides any number of **empty** squares in a straight line —
**forward or sideways**, orthogonally or diagonally. That is the five directions:
straight forward, left, right, forward-left, and forward-right. It may finish on
an empty square, or on an **opponent's man, which is captured** and removed from
the board. Only a singleton may capture, and it may not slide *past* a man.

### Ordo move

An **ordo** is two or more of your men standing in an uninterrupted straight
**horizontal or vertical line**. The whole ordo slides together, keeping its
formation, any number of **empty** squares — orthogonally only, and only
**perpendicular to its own axis**:

- a **horizontal** ordo moves **forward** (advancing in the rank direction);
- a **vertical** ordo moves **sideways** (left or right).

All squares the ordo passes over must be empty. An ordo **may not capture** and
**may not move "single file"** (along its own line). Any contiguous sub-line of
2+ men also counts as an ordo.

## Backward moves & reconnection

Normally men and ordos only move forward or sideways — never backward. The single
exception is **reconnection**: if the opponent's capture splits your group so that
you begin your turn **disconnected**, you must make a move that reconnects it, and
for that move **backward directions become available** (backward, backward-diagonal,
and backward ordo slides). You must restore a single connected group in **one
move**. If no move can reconnect your group, you **lose immediately**.

## Winning

You win when any of the following happens:

1. **You land a man on the opponent's home row** (the primary goal).
2. **You capture the opponent's last man.**
3. **The opponent cannot reconnect** — your move leaves them disconnected with no
   move that rejoins their group.

A player with no legal move loses (there is no passing).

## Termination (this implementation)

Ordo has no natural draw, but non-capturing shuffling could loop forever, so a
**hard cap of 300 plies** declares a draw. This only exists to guarantee
termination for automated/random play; real games end well before it.

## Move notation

- **Singleton:** `from>to`, e.g. `4,3>4,5` (files `a`–`j` → columns `0`–`9`,
  ranks `1`–`8` → rows `0`–`7`).
- **Ordo:** `end1>end2>dest` — the two endpoints of the line, then where the
  first endpoint lands (which fixes the shared shift vector), e.g. `3,2>5,2>3,3`
  slides the horizontal ordo `c3–e3` one rank forward. To select an ordo by
  clicking, click its lower-left endpoint first, then the other endpoint, then
  the destination.

## Notes on sources / interpretation

- The starting position, board size (10 × 8) and piece count (20 each) are taken
  verbatim from the designer's rules and match the Zillions of Games port
  (`Ordo.zrf`, board-setup section).
- **Ordo direction — perpendicular only.** The official rules state an ordo "may
  only move orthogonally … forward (if horizontally aligned) or sideways (if
  vertically aligned)" and explicitly forbid moving "single file". The Zillions
  port additionally generates *along-axis* ordo slides; per the designer's rules
  (the authority) this implementation restricts ordo moves to the perpendicular
  direction only.
- Only the reconnection exception (being split by the opponent's capture) allows
  backward movement, exactly as in the official rules; there is **no** "voluntary
  disconnect now, reconnect later" — every move must leave you connected.
