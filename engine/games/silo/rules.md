# Silo

**Designer:** Mark Steere (September 2021). A two-player stacking game inspired by
the Tower of Hanoi. Rules as implemented here; the official one-page rule sheet is
the *Silo* PDF at marksteeregames.com.

## Board and setup

A **1×6** strip of squares (cells `0`–`5`). It starts with alternating
single-colour stacks of **three** checkers each (18 in all):

- cells **0, 2, 4** — three **Red** checkers each
- cells **1, 3, 5** — three **Blue** checkers each

Larger setup option: **1×8**, alternating stacks of **4** (32 checkers).

## Sitting on opposite sides — "your right"

The two players sit on **opposite** sides of the board, so **"your right" is the
opposite direction for each player**:

- **Red** moves toward the **high** end (toward cell 5).
- **Blue** moves toward the **low** end (toward cell 0).

**Red moves first**, then players alternate.

## The move

On your turn, take your **highest** (topmost) own checker within any one stack and
move it **one square to your right**, **carrying with it any enemy checkers that
are stacked above it** (everything above your highest own checker is, by
definition, enemy). Drop that carried substack **on top** of the destination
square's stack — or onto the empty square if there is no stack there. Exactly one
substack moves per turn; the order of the carried checkers is preserved.

You cannot move a checker off the end of the board, so your highest own checker in
the cell at your far end has no move.

- **Passing is not allowed**, but if you have **no** legal move your turn is
  **skipped** and your opponent moves again.

## Pie rule

On **Blue's first turn only**, Blue may play **swap** instead of moving: Blue
switches colours and becomes Red, claiming the opening move. (Internally this is
the board's reflect-and-recolour symmetry, which swaps the two players' roles.)

## Object — how to win

Get **all** of your checkers into **one contiguous substack**: a single unbroken
run of your colour inside one cell. There may be enemy checkers above and/or below
your run. The first player to do so wins.

## Draws / termination

A genuine "both players stuck" position always coincides with a completed run (a
winner is detected first), so it is not a real draw. Because carried enemy
checkers can move backward, the game is not provably loop-free, so a hard **ply
cap** (45 × checkers-per-player) ends an unresolved game as an **honest draw**
rather than inventing a winner. Normal games finish well before the cap.

## Notation

A move is written as the path `c,0>d,0` (source→destination cell, `d = c±1`). The
pie action is the string `swap`. Stacks are drawn as towers (owner colours from
the bottom up).
