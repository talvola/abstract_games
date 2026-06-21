# Frisian Draughts (Frysk dammen)

Frisian draughts on a **10×10** board, played on the dark squares only. It is in
the same family as International (Polish) draughts, but with a distinctive
capture geometry: pieces capture **orthogonally as well as diagonally**.

## Objective
Leave your opponent with no legal move — either by capturing all of their pieces
or by blocking them so none can move. That player loses.

## Board & setup
Dark squares are those where `(col + row)` is odd. Each side starts with **20
men** on the four ranks nearest them: **White** on rows 0–3 (moves toward row 9)
and **Black** on rows 6–9 (moves toward row 0). White moves first.

## Movement (no capture)
- **Men** move one square diagonally **forward** to an adjacent empty square
  (forward = toward the far rank). Men never make a quiet *orthogonal* move —
  orthogonal play is for capturing only.
- **Kings are flying:** a king slides any distance along a clear line — a
  diagonal **or** an orthogonal (horizontal/vertical) — to any empty square.

## Capturing — the Frisian rule
- **Men capture in all 8 directions:** a man jumps an adjacent enemy piece,
  landing on the empty square immediately beyond it, in any of the four diagonal
  **or** four orthogonal directions. (Men still *move* diagonally forward only;
  the extra freedom is purely for captures.)
- **Flying kings capture along all 8 lines:** a king slides along a diagonal or
  orthogonal over empty squares, jumps a single enemy piece that has at least one
  empty square beyond it, and lands on **any** empty square past it along that
  same line — then may continue.
- **Capture is mandatory**, and you must keep capturing until the moving piece
  can capture no more.

### Weighted maximum-capture rule
Among all possible capture sequences you **must play one of greatest value**.
Frisian draughts uses the official **summed point value** where a **king is worth
1.5 men**:

- value of a sequence = (men captured) + **1.5** × (kings captured).

A sequence is legal exactly when its summed value is maximal. (Internally this is
computed with integer weights man = 2, king = 3 — the same 1 : 1.5 ratio — so the
value is `2 × pieces + kings`.) If several sequences tie on value, any of them may
be chosen.

Worked examples (these are where the summed rule differs from a naive
count-first rule): capturing **2 kings** (value 3.0) **ties** capturing **3 men**
(value 3.0) — both are legal; capturing **3 kings** (4.5) **beats** **4 men**
(4.0) — the 3-king capture is forced; but **2 men** (2.0) beats **1 king** (1.5),
so a king does not outweigh two men.

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

## Omitted / simplified rules
For a clean, self-contained implementation, some finer points of competition
Frisian draughts are **deliberately omitted**:

- The subtle "a man may not capture by landing on the square a king just
  vacated" and similar advanced edge-case restrictions are **not** modelled; the
  only landing restriction is the standard one (you cannot land on, or fly
  through, an occupied square, including not-yet-removed captured pieces).
- The official Frisian **draw conventions** (e.g. the king-vs-king and 2-vs-1
  endgame move limits, threefold repetition) are replaced below by pragmatic
  engine draw rules.

## Winning & draws
You **win** when the opponent has no legal move on their turn.

For guaranteed termination this implementation adds two draw rules:
- a **50-ply no-progress** rule — 50 consecutive plies with no capture and no
  man move (i.e. only kings shuffling) is a draw; and
- a hard **400-ply cap**.

## Move notation
Moves are `>`-separated paths of the squares the moving piece visits, e.g.
`3,6>5,4` (a single diagonal capture), `4,4>6,4` (a single orthogonal capture),
or `4,4>6,4>6,6` (an orthogonal-then-diagonal chain). Since only maximal capture
sequences are legal, clicking through a chain naturally forces it to completion.
