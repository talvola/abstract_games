# Mak-yek

**Mak-yek** (Thai: หมากแยก; also spelled **Apit-sodok** in Cambodian/Malay
tradition) is a two-player abstract capture game played in Thailand, Myanmar,
and Cambodia. Two identical capture mechanics — *custodial* and *intervention* —
make it a close cousin of the Tafl family and of Hasami Shogi.

## Equipment

- An **8×8** board.
- Each player has **16 identical men** (no piece types, no kings).

## Setup (as implemented)

The standard opening places each side's men on the **first and third rank from
that player's side** — i.e. on the player's own back rank and the rank two rows
in front of it (the 1st and 3rd ranks). This is the layout described on
Wikipedia ("Men are laid out on the first and third row from the player").

In this package's coordinates (`col,row`, row 0 at the bottom):

- **Player 0** fills **rows 0 and 2** (16 men).
- **Player 1** fills **rows 5 and 7** (16 men).

The two middle ranks of each half (rows 1 and the gap) start empty, giving the
familiar two-bands-each opening.

> *Ruleset note.* Some sources instead describe two *adjacent* full back rows
> (rows 0–1 / 6–7). The "first and third rank" layout above is the one given in
> the primary English reference (Wikipedia), so it is the one implemented here.

## Movement

A turn is moving **one** man like a **rook in chess**: any number of empty
squares **orthogonally** (horizontally or vertically). A man may **not** move
diagonally and may **not** jump over any piece (friendly or enemy). You must
move on your turn if you have any legal move.

## Capture

All capture is **active**: it happens **only as a result of your own move**, and
only from the square your man just moved to. A man that *moves into* a flanked
or sandwiched position is **never** captured — capture belongs to the mover.

A single move resolves **all** of the following in **every** orthogonal
direction simultaneously, so one move can capture several lines at once.

### 1. Custodial (flanking) capture

After you move a man, look outward in each of the four orthogonal directions
from its destination. If one or more **contiguous** enemy men lie in a straight
line — with **no gap** and **no friendly man** among them — and the square just
beyond the run holds a **friendly** man, then **every** enemy man in that run is
captured (removed from the board).

- A gap (empty square) or a friendly man inside the run breaks the bracket and
  nothing is captured in that direction.
- This captures a single enemy man or an unbroken line of several enemy men.

### 2. Intervention capture

If your move lands your man in the single **empty** square **between two enemy
men** that are one square apart on a row or column (pattern: *enemy – YOU –
enemy*), **both** of those enemy men are captured.

This is the inverse of custodial capture — you are the meat of the sandwich, but
because capture is the mover's, you are safe and instead capture the two
flanking enemies.

### Both modes on one move

Because every direction is resolved from the destination square, a move can
trigger custodial captures outward in some directions and an intervention
capture across an axis at the same time; all captured enemies are removed
together. (Where a custodial and an intervention capture would claim the same
men along one line, the same enemies are removed either way; traditional sources
note the custodial reading "takes precedence," which has no different effect on
which pieces leave the board.)

## Winning

You **win by annihilation**: the first player left with **no men** loses.
Capturing the opponent's last man wins immediately.

To guarantee the game terminates (rook-shuffling without captures could loop
forever), a hard cap of **300 plies** without a result ends the game as a
**draw**.

## Coordinates & notation

Cells are `col,row` with `0,0` at the bottom-left. A move is written
`from>to`, e.g. `3,2>3,6`. The move log shows algebraic-style notation
(`a3-d3`).
