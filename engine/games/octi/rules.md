# Octi

*Octi* (Don Green, 1999; MENSA Select) is an abstract strategy game played with
**pods** (octagonal pieces) that gain movement directions when you insert
**prongs** (arrows) into them. This package implements the well-documented
**basic 2-player game** (the 6×7 board, 4 pods and 12 prongs per side).

## Board and setup

- A **7 wide × 6 tall** grid (columns 0–6, rows 0–5). Row 0 is drawn at the
  bottom; rows increase upward.
- Each player has **4 base squares** ("Octi squares"), shown tinted:
  - **Red (player 0):** column 1, rows 1–4 (left side).
  - **Blue (player 1):** column 5, rows 1–4 (right side).
- Each player starts with **one pod on each of its 4 base squares** and **12
  prongs in reserve**. Pods start with **no prongs**.

## A turn — do exactly ONE of:

### Add a prong
Take one prong from your reserve and add it to one of your pods, in any of the 8
compass directions that pod does not already have. A pod can hold at most 8
prongs (one per direction). A prong gives the pod the ability to **move** and
**jump** in that direction.

### Move a pod
Move one of your pods **one square** in a direction it **has a prong**, onto an
**empty** square.

### Jump
In a direction the pod **has a prong**, if the **adjacent** square holds a pod
(yours or the enemy's) and the square **beyond** (same direction) is **empty**,
the pod **jumps over** it to that empty square. A jump may **chain**: from the
landing square the pod may immediately jump again in any of its pronged
directions, and so on. You may **stop the chain** at any landing square.

**Capturing is optional.** After a jump path that passed over at least one
**enemy** pod, you choose whether to **capture** all jumped enemy pods (remove
them — their prongs return to your reserve) or **keep** them on the board.
Friendly pods that you jump are never removed. (In this implementation the
capture choice applies to the whole jump path: capture all jumped enemy pods or
none.)

## Winning

You win immediately if either:

1. you land one of your pods on **any enemy base square**, or
2. you **capture all** of the opponent's pods (they have none left).

## Draws / termination

Adding prongs is finite (each comes from the reserve). Pure movement could cycle,
so if **80 plies** pass with **no prong added and no pod captured**, the game is a
**draw**. (Real games end long before this; the cap only guards against
pathological loops.)

## Move encoding

Moves are strings the board UI turns into clicks:

- **Add a prong:** click your pod, then pick a direction — `"c,r=DIR"` where DIR
  is one of `N NE E S SE SW W NW`, e.g. `"1,2=N"`.
- **Move a pod:** `"from>to"`, e.g. `"1,2>2,2"` — click the pod, then the target.
- **Jump:** a `>`-separated path of landing squares, e.g. `"1,2>3,2"` (single
  jump) or `"1,2>3,2>3,4"` (chain). When the path jumps an enemy pod, a
  `=CAP` / `=KEEP` suffix chooses whether to capture (the UI offers both).

### Direction → board mapping

Prong directions are **screen-oriented**: `0`=N points **up**, then clockwise.
On the board (row 0 at the bottom) up = the **+row** direction:

| dir | name | (Δcol, Δrow) |
|-----|------|--------------|
| 0 | N  | (0, +1)  |
| 1 | NE | (+1, +1) |
| 2 | E  | (+1, 0)  |
| 3 | SE | (+1, −1) |
| 4 | S  | (0, −1)  |
| 5 | SW | (−1, −1) |
| 6 | W  | (−1, 0)  |
| 7 | NW | (−1, +1) |

## Interpretations / notes

- **Board choice:** Octi has a 9×9 "full" game (7 pods, 25 prongs, 3 bases each)
  and a 6×7 **basic game** (4 pods, 12 prongs, 4 bases each). This package
  implements the basic game, which is the most documented small variant and the
  one used by the FoxMind beginner rules. Base positions follow the published
  basic-game layout (one column in from each side edge, the four central rows).
- **Optional capture** is modeled per jump-path (capture all jumped enemy pods,
  or none) rather than per individual jump; this keeps the move clickable while
  preserving the strategic "you may decline a capture" rule.
- **Captured prongs** return to the capturing player's reserve (re-usable), as in
  the published rules.
