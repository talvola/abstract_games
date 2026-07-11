# Cannon

David E. Whitcher, 2003 (PyroMyth Games; republished by nestorgames). A war
game on the **points of a 10×10 grid**. Seat 0 = **Black** (bottom, moves
first), seat 1 = **Red** (top). Each side has **15 soldiers** and **1 Town**.

## Setup

- Black soldiers start in five columns of three on files a, c, e, g, i
  (ranks 2–4); Red soldiers on files b, d, f, h, j (ranks 7–9) — the official
  staggered array.
- **First two moves:** Black, then Red, places their **Town** anywhere on
  their own back rank (rank 1 for Black, rank 10 for Red) **excluding the
  corners**. A Town never moves. Play then continues with Black.

## Soldier moves

A soldier may:

1. **Advance** — one step **forward** straight or diagonally-forward to an
   *empty* point.
2. **Capture** — take an adjacent enemy piece (soldier or Town) one step
   **forward** (straight/diagonal) or **sideways**. Never backward, never
   sideways-diagonal.
3. **Retreat** — if it is adjacent (any of the 8 neighbouring points) to an
   enemy piece, it may jump exactly **two points backward**, straight-back or
   diagonally-back. Both the intermediate and the landing point must be empty.
   A retreat never captures.

## The cannon

Three **adjacent friendly soldiers in a straight line** (orthogonal or
diagonal) form a **cannon**. A Town never counts as part of a cannon. A cannon
may, in either direction along its line:

- **Slide** — the rear soldier jumps to the *empty* point directly beyond the
  front soldier (the whole formation shifts one step along its line). A slide
  never captures.
- **Shoot** — a capture *without moving*: if the point **directly in front of
  the cannon is empty**, the cannon may remove an enemy piece (soldier or
  Town) standing **2 or 3 points beyond its front soldier**. Only that first
  point must be empty — the long (3-point) shot passes over the second point
  even if it is occupied (rulebook + the author's own Zillions implementation;
  see Interpretations).

## Turn obligations and game end

- Each turn you **must** move a soldier or use a cannon — passing is not
  allowed.
- **You win** by capturing **or shooting the enemy Town**, or if your opponent
  has **no legal move** on their turn (stalemate — this includes an opponent
  whose soldiers are all captured or completely blocked).

## Draws (platform backstops)

The rulebook has no official repetition rule ("repeating of positions over and
over is rarely an issue"). To guarantee termination this implementation adds
two honest draw backstops:

- **Threefold repetition** of the same position with the same player to move
  (counted since the last capture) is a draw.
- A game reaching **1000 plies** is a draw.

## Move notation (click-to-move)

- Town placement: click the back-rank point (`"c,r"`).
- Everything else is `"from>to"` (click source, then destination). A **cannon
  slide** is entered from the cannon's **rear** soldier to the empty point
  beyond the front. A **cannon shot** is entered from the cannon's **rear**
  soldier to the enemy **target** (4 or 5 points away along the line); the
  soldiers do not move.

## Interpretations (source conflicts, documented)

- **Long-shot geometry:** the official rulebook and the author's Zillions file
  require only the point *immediately in front* of the cannon to be empty;
  iggamecenter's paraphrase ("one or two empty points between") would also
  require the middle point empty for the 3-point shot. This implementation
  follows the rulebook/author: only the first point must be empty.
- **Retreat trigger:** "adjacent to an enemy *piece*" (rulebook/Boardspace/
  Zillions) — adjacency to the enemy **Town** also enables a retreat
  (iggamecenter says "enemy soldier"). Rulebook followed.
- **Win condition:** the rulebook says the winner "captures the opposite Town
  … (as a checkmate in chess) or stalemates the opponent", and the author's
  readme states the object as "Capture your opponents Town ( Checkmate )" —
  capture is the winning event. As on iggamecenter, this implementation ends
  the game on the **actual capture** of a Town; there is no chess-style check
  restriction — you may ignore a threat to your Town, at your peril. (The one
  counter-reading: the author's Zillions file uses the check-enforcing
  `checkmated` loss-condition, under which leaving your Town en prise is
  illegal and the game ends at checkmate. The two readings differ only in
  mutual-threat races; the written rules and online play favour plain
  capture.)
