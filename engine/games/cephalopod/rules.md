# Cephalopod

A two-player dice-capture **majority** game invented by **Mark Steere**
(February 25, 2006). There is **no actual randomness** — every die's value is
*determined* by play, never rolled.

## Board

A square grid, **5×5** by default (a `size` option offers 3, 5, or 7). It starts
empty. Cells are addressed `c,r` with `c` the column and `r` the row, both
0-based. Each cell is either empty or holds a single **die** showing a pip value
**1..6** in one player's colour. Player 0 is **Red**, player 1 is **Blue**; Red
moves first.

## A turn

On your turn you **add one die of your colour to a vacant square** (you cannot
pass — a placement is always available while squares remain). A die, once
placed, never moves. The value it shows is fixed by the resolution below.

### Capturing placement (mandatory when possible)

Look at the dice on the cells **orthogonally adjacent** (up/down/left/right) to
the square you played on. If **two, three, or four** of those adjacent dice have
a **pip sum of six or less**, then capturing is **mandatory**:

- You **choose** one qualifying subset of **≥2** adjacent dice whose pip sum is
  ≤ 6,
- **remove** those dice from the board, and
- your newly placed die shows a pip value equal to that **sum** (so 2..6), in
  your colour.

If several different qualifying subsets exist, **each is a distinct legal move**
and you pick which one to take — you are **not** required to capture the maximum
number of dice (Steere's Fig. 4: a player surrounded by capturable dice may
choose to capture only some of them). Because the sum must be ≤ 6, the placed
die's value never exceeds 6.

### Plain placement

If **no** subset of two-or-more adjacent dice sums to ≤ 6 (including the case of
fewer than two adjacent dice), the placement is **non-capturing** and your new
die simply shows a **one** in your colour.

## Winning

Play continues until the board is **completely full**. The player whose dice
occupy the **majority** of the squares **wins**. The board has an **odd** number
of cells (25 on 5×5), so the counts can never be equal — **draws and ties cannot
occur**.

## Move notation (this implementation)

- **Plain one-placement:** the target cell, e.g. `"2,3"` — a single click.
- **Capturing placement:** the target cell with an `=`-suffix listing the
  captured cells, sorted and `;`-separated, e.g. `"2,2=1,2;3,2"`. When more than
  one capturing subset lands on the same target cell, the UI's choice picker
  disambiguates them (each subset is its own legal move).

## Ruleset notes / choices

- **Source:** Mark Steere's official rules
  ([PDF](https://www.marksteeregames.com/Cephalopod_rules.pdf),
  [HTML](https://marksteeregames.com/Cephalopod_rules.html)) and
  [BoardGameGeek #22790](https://boardgamegeek.com/boardgame/22790/cephalopod).
- **Mandatory capture / choice of subset:** the official rule is *"Captures are
  mandatory only when placing a die onto a square from which captures are
  possible,"* and the player **chooses** which qualifying subset to remove (need
  not be the maximum). This implementation follows that reading exactly: every
  qualifying subset is enumerated as its own legal move, so the player chooses.
- **`size` option:** the official game is 5×5. The 3 and 7 options are provided
  for variety (the rules are size-agnostic); all sizes are odd so no tie is
  possible.
- **Termination.** The game ends **exactly when the board is full**. The board
  does **not** monotonically fill: a plain "1" placement is net +1 die, but a
  **capture removes ≥2 dice and adds 1**, so a capturing turn actually *increases*
  the number of empty cells. Filling therefore takes many more plies than there
  are cells. Termination is still guaranteed: the total **pip-sum** on the board
  is bounded above by 6 × cells and is **non-decreasing** (a capture replaces dice
  summing *S* with one die showing *S* — sum unchanged; a plain "1" raises the sum
  by exactly 1), so there can be at most 6 × cells plain placements, and each
  capture strictly reduces the live-dice count, so captures are bounded too — the
  game provably reaches a full board. (The implementation keeps a defensive ply
  cap of 12 × cells as a pure backstop that never fires in legal play.)
