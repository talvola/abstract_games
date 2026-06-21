# International Draughts

International (a.k.a. Polish) draughts on a **10×10** board, played on the dark
squares only.

## Objective
Leave your opponent with no legal move — either by capturing all of their pieces
or by blocking them so none can move. That player loses.

## Board & setup
Dark squares are those where `(col + row)` is odd. Each side starts with **20
men** on the four ranks nearest them: **White** on rows 0–3 (moves toward row 9)
and **Black** on rows 6–9 (moves toward row 0). White moves first.

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
A man becomes a **king** only if it **ends its move on the far rank** (row 9 for
White, row 0 for Black). Merely passing over the last rank during a capture does
**not** promote it, and the man continues capturing as a man.

## Winning & draws
You **win** when the opponent has no legal move on their turn.

For guaranteed termination this implementation adds two draw rules:
- a **50-ply no-progress** rule — 50 consecutive plies with no capture and no
  man move (i.e. only kings shuffling) is a draw; and
- a hard **400-ply cap**.

(These are pragmatic engine draw rules; official play uses the FMJD draw
conventions, e.g. the 25-move and 3-times-repetition rules, which are not
modelled here.)

## Move notation
Moves are `>`-separated paths of the squares the moving piece visits, e.g.
`3,6>5,4` (a single capture) or `3,6>5,4>7,6` (a chain). Since only maximal
capture sequences are legal, clicking through a chain naturally forces it to
completion.
