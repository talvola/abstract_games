# Pool Checkers

**Pool checkers** (American Pool draughts) is the popular North-American pool
variant of Russian draughts. It is played on the **8×8** board on the **dark
squares**, with **12 men per side**. Men capture forward *and* backward, kings
are **flying**, and capture is **mandatory but any** (you are *not* forced to
take the maximum). Its one defining feature is **deferred promotion** during a
capture chain (see below).

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
- **Capture is mandatory:** if any capture exists you must play a capture.
- **Once a chain starts you must finish it:** you keep capturing with the moving
  piece until it can capture no more.
- **Removal / no jumping twice:** captured pieces are removed only at the **very
  end** of the full move; consequently a piece may **not be jumped twice** in one
  sequence (they stay on the board as blockers until the sequence completes).

### Choice of capture — ANY, not maximum
When several captures are available you may choose **any** of them. You are **not**
required to capture the greatest number of pieces or the longest sequence — only
to finish whatever chain you begin. (This is the Russian/Pool "choice of
capture" rule.)

## Promotion — the defining rule: DEFERRED promotion
A man becomes a **king** only if it **ends its whole move on the far rank**
(row 7 for White, row 0 for Black).

Crucially, if a man **reaches the king row *during* a capture chain**, it does
**NOT** become a king yet. It keeps jumping **as a man** for the rest of that
turn — so it can only make ordinary short man-jumps, never a king's flying or
long-range jump — and it promotes to a king **only at the very end**, and only
if it is still standing on the last rank when the chain finishes. If a man
reaches the king row mid-chain and then jumps back off it, it finishes as a
plain man.

## Winning & draws
You **win** when the opponent has no legal move on their turn.

For guaranteed termination this implementation adds two draw rules:
- a **50-ply no-progress** rule — 50 consecutive plies with no capture and no
  man move (i.e. only kings shuffling) is a draw; and
- a hard **400-ply cap**.

(PlayStrategy's official Pool ruleset uses richer draw conventions — threefold
repetition, the 3-kings-vs-1 15-move rule, and king-ending move counts — which
are not modelled here; the two pragmatic rules above only guarantee the engine's
random-play conformance terminates.)

## What makes Pool distinct

Pool sits between two shipped siblings and differs from each by exactly one rule:

- **vs Russian draughts** — *the promotion rule.* Russian promotes a man
  **immediately** the instant it touches the king row mid-capture, and it
  **continues the chain as a flying king** (gaining backward, long-range king
  jumps for the rest of that turn). Pool **defers** promotion: the man keeps
  jumping as a man and only becomes a king when the sequence ends. This is the
  single, defining difference between the two games.
- **vs Brazilian draughts** — *the choice of capture.* Brazilian enforces the
  **maximum-capture (majority) rule** — you must take the sequence capturing the
  most pieces. Pool lets you take **any** available capture. (Both games already
  defer promotion at end-of-move, so this capture rule is the distinction here.)
- **vs English/American checkers** — checkers uses **short** (non-flying) kings
  and men that capture **forward only**; Pool has flying kings and men that
  capture forward and backward.

## Move notation
Moves are `>`-separated paths of the squares the moving piece visits, e.g.
`3,4>5,2` (a single capture) or `3,4>5,2>3,0` (a chain). Because a started chain
must be finished, clicking through a chain naturally forces it to completion.
