# Tak

**Tak** (James Ernest & Patrick Rothfuss, 2016) is a two-player game of building
a **road** — an unbroken line of your pieces joining two opposite edges of the
board. These are the rules **as implemented** here.

## Board and pieces

Tak is played on an **N×N** board (the `size` option: 3, 4, 5, 6 or 8; default
**5**). Squares are named by their `c,r` coordinate.

Each player has a **reserve** of stones and capstones, by board size:

| Board | Flats (stones) | Capstones |
|------:|:--------------:|:---------:|
| 3×3   | 10             | 0         |
| 4×4   | 15             | 0         |
| 5×5   | 21             | 1         |
| 6×6   | 30             | 1         |
| 8×8   | 50             | 2         |

The same reserve count covers both flats **and** standing stones — a wall is just
a stone stood on its edge, so it is drawn from the flat reserve.

There are three piece kinds:

- **Flat stone** — lies flat. **Counts toward roads** and can be stacked upon.
- **Standing stone / wall** — stood on edge. **Counts for nothing** (a road can
  never pass through it) and **cannot be stacked upon** — with one exception
  below. It is the way to block your opponent's road.
- **Capstone** — **counts toward roads**, can **never be covered** by any piece,
  and when moving **alone** onto a wall it **flattens** that wall into a flat
  stone (its only way to end on a wall). A capstone cannot itself be stacked upon
  and is never a flat for road or scoring purposes — but it does count for roads.

A square may hold a **stack** of pieces. You **control** a stack if your piece is
the **top** one; only the top piece's kind matters for roads and movement. Every
*covered* piece behaves as a plain flat.

## A turn

### The opening double-move

On each player's **very first turn** they must **place a single flat stone of the
OPPONENT's colour** on any empty square — no other move type is allowed. (So the
first two stones on the board are "swapped": Player 1 places a Player-2 flat, then
Player 2 places a Player-1 flat.) These opening stones are free and are not charged
to anyone's reserve.

### Every later turn — do exactly one of:

**(A) Place** one piece from your reserve onto an **empty** square, as a flat, a
wall, or (if you still have a capstone) a capstone. Notation: the cell id with a
type suffix — `2,3=F` (flat), `2,3=S` (standing stone / wall), `2,3=C` (capstone).

**(B) Move a stack you control** (a "spread"):

1. **Lift** between 1 and `min(stack height, N)` pieces off the **top** (the
   carry limit equals the board size N).
2. Move in one straight **orthogonal** direction.
3. **Drop at least one** piece on **each consecutive** square along the path — you
   may not skip a square.
4. You may not drop onto a **wall** or a **capstone** — **except** a lone capstone
   (a single-piece carry) may, as its **final** drop, land on a wall and flatten
   it. A capstone can never be covered.

Notation for a spread is a `>`-path of the squares entered, with a drop-count
suffix giving how many pieces are dropped on each square (the digits sum to the
number lifted). For example `3,3>4,3>5,3=12` means: lift 3 from `3,3`, drop 1 on
`4,3`, then 2 on `5,3`. The pieces are dropped **bottom-of-the-lifted-column
first**, so the original top piece (and its kind) ends up on the final square.
Every legal (direction, lift, drop-distribution) is generated as its own move, so
when several distributions share the same path the app's choice picker
disambiguates them.

## Winning

A win is checked **after every move**.

1. **Road win.** If the mover now has a **connected orthogonal chain** of squares
   they control with a **flat or capstone on top** (walls never count) that
   spans **two opposite edges** — top↔bottom OR left↔right — they **win
   immediately**. (Connectivity is a breadth-first search over road squares.)
   *Tie-break:* if a single move were ever to complete a road for **both**
   players at once, the **player who just moved wins**. (Two opposite-direction
   roads must cross at a shared cell owned by one player, so a genuine double
   road cannot actually arise; the rule is stated for completeness and the
   engine resolves it mover-first.)

2. **Flat win.** If **no empty square remains**, **or** the player who just moved
   placed their **last reserve piece**, the game ends and is scored: whoever
   controls **more flat-topped squares** wins. **Capstone-topped and wall-topped
   squares do NOT count.** Equal flat counts is a **draw**.

## Draw safety

Stacks can shuffle back and forth without ever depleting a reserve, so as a
defensive guarantee of termination the game is scored as a **flat win (draw if
tied)** if it reaches a hard cap of 400 plies. In normal play one of the two win
conditions above always fires first.
