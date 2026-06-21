# Brazilian Draughts

Brazilian draughts is **International (Polish) draughts rules played on the
smaller 8×8 board** (the standard checkers board), with **12 men per side**. The
rules below are *identical* to International Draughts — only the board size and
starting setup differ. (Brazilian draughts is also essentially the same as
"pool checkers" with the international flying-king/majority rules.)

Played on the **dark squares** only.

## Objective
Leave your opponent with no legal move — either by capturing all of their pieces
or by blocking them so none can move. That player loses.

## Board & setup
Dark squares are those where `(col + row)` is odd. Each side starts with **12
men** on the three ranks nearest them: **White** on rows 0–2 (moves toward row 7)
and **Black** on rows 5–7 (moves toward row 0). White moves first.

## Movement (no capture)
- **Men** move one square diagonally **forward** to an adjacent empty square.
- **Kings are flying:** a king slides any distance along a clear diagonal to any
  empty square.

## Capturing
- **Men capture both forward and backward:** a man jumps an adjacent enemy piece,
  landing on the empty square immediately beyond it, in any of the four diagonal
  directions. (Men still *move* forward only.)
- **Flying kings capture by flying:** a king slides along a diagonal over empty
  squares, jumps a single enemy piece that has at least one empty square beyond
  it, and lands on **any** empty square past it along that same diagonal — then
  may continue.
- **Capture is mandatory**, and you must keep capturing until the moving piece
  can capture no more.

### Maximum-capture (majority) rule
Among all possible capture sequences you **must play one that captures the
greatest number of pieces**. If several different sequences tie for the maximum,
you may choose any of them. (This is the standard international/FMJD majority
rule, counting *number of pieces*, not their value — a man and a king count the
same.)

### Removal & the "no jumping twice" rule
Captured pieces are **removed only at the very end** of the full move, not as you
go. Consequently a piece may **not be jumped twice** in one sequence — in
particular a flying king may not leap the same enemy piece a second time. The
captured pieces remain on the board (as blockers you cannot land on or pass
through) until the sequence is complete.

## Promotion
A man becomes a **king** only if it **ends its move on the far rank** (row 7 for
White, row 0 for Black). Merely passing over the last rank during a capture does
**not** promote it, and the man continues capturing as a man.

## Winning & draws
You **win** when the opponent has no legal move on their turn.

For guaranteed termination this implementation adds two draw rules:
- a **50-ply no-progress** rule — 50 consecutive plies with no capture and no
  man move (i.e. only kings shuffling) is a draw; and
- a hard **400-ply cap**.

(These are pragmatic engine draw rules; official play uses other draw
conventions, e.g. king-vs-king endgame and repetition rules, which are not
modelled here.)

## Ruleset choice
This package implements the **international ruleset on 8×8**: men capture
forward *and* backward, kings are *flying*, and capture follows the *maximum*
(majority) rule. This is what "Brazilian draughts" means, and it is the only
difference from English/American checkers (which use forward-only men capture,
short kings, and any-capture-suffices). The implementation is the shipped
**International Draughts** engine with the board size set to 8 and the three-rank
12-men-per-side setup.

## Move notation
Moves are `>`-separated paths of the squares the moving piece visits, e.g.
`3,4>5,2` (a single capture) or `3,4>5,2>3,0` (a chain). Since only maximal
capture sequences are legal, clicking through a chain naturally forces it to
completion.
