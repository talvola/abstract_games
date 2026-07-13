# Russian Draughts (Shashki)

Russian draughts (Russian *шашки*, shashki) is the traditional **8×8** national
variant, played on the **dark squares** with **12 men per side**. The moving
geometry is the same as International/Brazilian draughts; Russian is defined by
two rules — **choice of capture** and **promotion during a capture** — that
distinguish it from every other 8×8 sibling in the library.

## Objective
Leave your opponent with **no legal move** — either by capturing all of their
pieces or by blocking them so none can move. That player loses.

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
- **Capture is mandatory:** if a capture is available you must capture, and once
  a capture chain has started you must **finish the whole chain** — you keep
  jumping with the moving piece until it can capture no more.

### Choice of capture ("any", NOT maximum) — defining rule #1
When several different capture sequences are available you may play **any** of
them. You are **not** forced to take the longest sequence or the one that
captures the most pieces. (Only *finishing* a started chain is compulsory — you
may not stop a chain early, but you may choose *which* chain to start.) This is
the opposite of the international/Brazilian **maximum (majority)** rule.

### Removal & the "no jumping twice" rule
Captured pieces are **removed only at the very end** of the full move (Turkish
strike), not as you go. Consequently a piece may **not be jumped twice** in one
sequence — in particular a flying king may not leap the same enemy piece a second
time. The captured pieces stay on the board as blockers (you cannot land on or
pass through them) until the sequence is complete.

## Promotion — defining rule #2 (promotion *during* a capture)
A man that lands on the opponent's back rank (row 7 for White, row 0 for Black)
**during a multi-capture promotes to a king immediately and continues the capture
as a flying king** — it may now jump backward and any distance for the rest of
the chain. If no further capture is possible after the promotion, the turn simply
ends there (the man stays a freshly-made king). A man also promotes if it ends a
normal (non-capturing) move on the last rank.

*(Worked example from PlayStrategy: a Black man on `a3` does not merely promote by
capturing `a3:c1`; it lands on the back rank at `c1`, becomes a king, and sweeps
`c1:g5:d8:a5`, winning by capturing all enemy pieces in one turn.)*

## Winning & draws
You **win** when the opponent has no legal move on their turn (all pieces
captured, or all blocked).

For guaranteed termination this implementation adds two pragmatic draw rules:
- a **50-ply no-progress** rule — 50 consecutive plies with no capture and no
  man move (only kings shuffling) is a draw; and
- a hard **400-ply cap**.

(Official Russian play uses other draw conventions — threefold repetition,
king-endgame move counters, the "3-kings-vs-1" 15-move rule — which are not
modelled here.)

## How Russian differs from every 8×8 sibling in the library
All are 8×8 with 12 men on the dark squares. The load-bearing differences:

| Rule | **Russian** | Brazilian | Checkers | Italian |
|---|---|---|---|---|
| Man capture direction | fwd **and** back | fwd and back | forward only | forward only |
| King type | **flying** | flying | short (1 sq) | short (1 sq) |
| Forced maximum capture? | **no — any** | **yes** (majority) | no (any) | yes + priority |
| Promote & continue mid-capture? | **YES** | no | no | no |
| Man may capture a king | yes | yes | yes | **no** |

So the two rules unique to Russian among these are **(1)** capture is mandatory
but **any** — not the forced maximum — and **(2)** a man **promotes mid-capture
and keeps jumping as a flying king**. Together they clearly separate it from:

- **Brazilian draughts** — same flying kings and backward men capture, but
  Brazilian *forces the maximum-count sequence* and does **not** promote-and-
  continue (a Brazilian man passing over the back rank keeps going as a man).
- **Checkers (English/American)** — short (non-flying) kings and forward-only men
  capture; no promote-and-continue.
- **Italian draughts** — short kings, forward-only men, forced *maximum with a
  quality priority chain*, and men may never take a king.

It is also distinct from **Pool checkers**, its closest relative, which shares
the "any capture" rule but **defers** promotion: a Pool man that reaches the back
rank mid-capture keeps jumping **as a man** (no flying backward jumps) and only
becomes a king when the sequence ends. Russian promotes **immediately** and
continues as a flying king — the single rule that separates the two.

## Move notation
Moves are `>`-separated paths of the squares the moving piece visits, e.g.
`3,4>5,2` (a single capture) or `3,4>5,2>3,0` (a chain). Because a started chain
must be finished, clicking through a chain naturally forces it to completion.
