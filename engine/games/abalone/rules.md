# Abalone

A two-player abstract game by **Michel Lalet & Laurent Levi (1987)**. Push your
opponent's marbles off the edge of the board: the first player to eject **6**
enemy marbles wins.

## The board

A **hexagon of hexagons** ("hexhex") of **side 5 = 61 cells**. Cells use axial
coordinates `(q, r)`; the third cube coordinate is `s = -q-r`. A cell is on the
board iff `max(|q|, |r|, |q+r|) <= 4`. Each cell has up to **6** neighbours.

## Marbles & the standard starting position

Each player has **14 marbles** (Black moves first). The game uses the **standard
Abalone layout** — the two armies facing each other across the board (not the
Belgian Daisy variant). Black fills its back two rows plus the centre of the
third row; White is the exact 180° rotation:

- **Black:** all of row `r = -4` (5 cells), all of row `r = -3` (6 cells), and
  the **middle 3 cells** of row `r = -2` (`q = 0,1,2`). 14 marbles.
- **White:** all of row `r = 4`, all of row `r = 3`, and the middle 3 cells of
  row `r = 2` (`q = -2,-1,0`). 14 marbles.

White's marbles are exactly `(-q, -r)` of Black's, so the position is point-
symmetric.

## Moving

On your turn you move an **in-line group** of **1, 2, or 3** of your own
adjacent marbles (a straight column along one of the three board axes) one cell,
in one of two ways:

### In-line move
The group slides one cell **along its own axis** (the direction the column
points). The destination lead cell must be **empty**, or it is a **sumito
(push)**:

- The cell(s) directly ahead hold a **strictly shorter** line of **enemy**
  marbles. Only **2-push-1**, **3-push-1**, and **3-push-2** are legal — you can
  never push an equal or larger enemy line, and never push *through* one of your
  own marbles.
- The cell immediately **behind** the enemy line must be **empty or off the
  board**.
- On a push the whole enemy line is shoved one cell along the same axis. An
  enemy marble shoved **off the board edge is ejected** (removed — a capture).

### Broadside (side-step) move
A group of **2 or 3** in-line marbles all step one cell in a direction
**perpendicular to** (i.e. not along) their axis. Every destination cell must be
**empty** — you can **never push on a broadside**. (A single marble simply steps
to any empty adjacent cell.)

## Winning

The first player to **eject 6** of the opponent's marbles wins. The result is
recorded as an event in the game state.

## Move encoding (for the click UI)

A move is a `>`-separated path of cell ids (each `"q,r"`). The encoding is:

> the moving group's source cells, in **canonical sorted order**, followed by the
> **destination of the first (lowest-sorted) source marble**.

- A single marble is `"src>dst"` (e.g. `"0,-2>0,-1"`).
- A 2/3-marble group lists all its source cells then the new position of the
  anchor (lowest) cell, e.g. `"0,-2>1,-2>2,-2>0,-1"`.

From the sorted source cells plus the anchor's destination, the engine
reconstructs the group, its axis, the step direction, whether the move is
in-line or broadside, and any push — each legal move maps to one distinct string.

**UX note:** for a multi-marble move the click path is *source cells then one
destination cell*. The generic from-to UI handles the single-marble and in-line
cases naturally (click the marbles in order, then the lead destination). A
3-marble broadside requires clicking all three source cells then the anchor's new
cell; this is fully legal and unambiguous but is a slightly longer click path
than a typical two-click move.

**Selecting & previewing a group move:** click your marbles one at a time to
build the line (they highlight together), then **hover a destination** — the
board ghosts where the *whole group* will land (not just the one encoded cell),
so a broadside reads as the entire set shifting. Click the destination to commit.

**Move-log notation:** cells are shown as **row + file** — rows **A–I top to
bottom**, files **1…n left-to-right within each row** (so the centre is `E5`).
A move reads `group→destination (type direction)`, e.g. `C3-C5→D4-D6
(broadside SE)` or `B5→C5 (push 2 NW — EJECT)`. Because the hex rows are offset,
the same column shifts file number between adjacent rows — that is expected.

## Termination safeguard (non-original)

Real Abalone can stall indefinitely (players shuffling marbles without
captures), which is fine for humans but would let random self-play loop forever.
This implementation therefore adds two **non-original** safeguards so the engine
always terminates:

- **No-progress draw:** if **200 plies** pass with **no ejection**, the game is a
  draw.
- **Hard ply cap:** an absolute cap (4000 plies) also ends the game as a draw.

Neither limit affects normal decisive play.
