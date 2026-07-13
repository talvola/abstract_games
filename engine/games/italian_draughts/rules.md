# Italian Draughts (Dama Italiana)

The traditional Italian 8×8 draughts game, implemented from the **Federazione
Italiana Dama (FID)** official rulebook (*Regolamento Tecnico di Gioco della Dama
Italiana*, Capo I). Played on the **dark squares** only, 12 men per side.

## Objective
Leave your opponent with **no legal move** — by capturing all their pieces or by
blocking them. That player loses.

## Board & setup
Dark (playing) squares are those where `(col + row)` is odd. This parity places
each player's **bottom-right square on a dark cell** — the Italian orientation
(a **light square in the lower-left**, double corner on the left) [FID 2.3].
Each side starts with **12 men** on the three ranks nearest them: **White** on
rows 0–2 (moves toward row 7) and **Black** on rows 5–7 (moves toward row 0).
**White moves first** [FID 3.4].

## Movement (no capture)
- **Men** move one square diagonally **forward** to an adjacent empty square
  [FID 4.1].
- **Kings** move one square diagonally **forward or backward** to an adjacent
  empty square [FID 4.7]. Italian kings are **short ("non-flying") kings** — a
  king moves only ONE square and may **not** slide any distance.

## Capturing
- **Men capture FORWARD only, and only over an enemy MAN** — a man jumps an
  adjacent enemy man, landing on the empty square immediately beyond it. **A man
  may never capture a king** [FID 5.3a, 5.3b].
- **Kings capture in all four diagonals, over any enemy piece** (man or king): a
  king jumps an adjacent enemy piece and lands on the **first square immediately
  beyond** it [FID 5.8]. The jump is **short** — the enemy must be adjacent (no
  flying capture from a distance).
- **Capture is mandatory** and continues while the moving piece can jump again
  [FID 6.1]. Captured pieces are **removed only at the end** of the sequence, and
  a piece may **not be jumped twice** in one sequence [FID 5.12, 6.4] — so the
  pieces you are capturing stay on the board as blockers until the move is done.

### Maximum-capture with the quality priority chain
When several capture sequences are available you must play one selected by this
strict priority order [FID 6.6–6.10]:

1. **Most pieces** — capture the greatest *number* of pieces [6.6].
2. **With a king** — among those, if you can capture *with* a king rather than a
   man, you must [6.7].
3. **Most kings** — among those, capture the greatest *number of kings* [6.8].
4. **Earliest king** — among those, take the sequence in which a king is
   *encountered first* (compare the sequences piece-by-piece; the higher-value
   captured piece must appear earlier) [6.9].
5. **Free choice** — any sequences still tied may be chosen freely [6.10].

## Promotion
A man becomes a **king** only if it **ends its move on the far rank** (row 7 for
White, row 0 for Black) [FID 4.2]. A man that reaches the last rank via a capture
**stops there** and does not act as a king until the following move [FID 6.5];
because men capture forward only, reaching the last rank is always the end of a
capture, so it never "passes through" the back rank and keeps going.

## Winning & draws
You **win** when the opponent has no legal move on their turn (all pieces
captured, or blocked).

For guaranteed termination this implementation adds two pragmatic draw rules:
- a **50-ply no-progress** rule — 50 consecutive plies with no capture and no
  man move (only kings shuffling) is a draw; and
- a hard **400-ply cap**.

(Official FID play uses other draw conventions — e.g. a king-endgame move counter
and repetition — which are not modelled here.)

## How Italian differs from Checkers and Brazilian Draughts
All three are 8×8 with 12 men. The load-bearing differences:

| Rule | Italian | English Checkers | Brazilian Draughts |
|---|---|---|---|
| Man capture direction | forward only | forward only | forward **and** backward |
| Man may capture a king | **no** | yes | yes |
| King type | **short** (1 square) | short (1 square) | **flying** (any distance) |
| Capture is maximal? | **yes** + priority chain | no (any capture) | yes (by count only) |
| Quality priority (king over man, etc.) | **yes** (6.6–6.10) | — | no |
| Orientation | dark on lower-**right** | dark on lower-left (convention) | dark on lower-left (convention) |

So Italian is closest to English checkers (forward-only men, short kings) but adds
two decisive rules — **men can never take a king**, and **captures are forced to
be maximal with a full king/quantity/quality priority chain** — which change the
strategy substantially. It is clearly distinct from Brazilian draughts, which has
backward-capturing men and flying kings.

## Move notation
Moves are `>`-separated paths of the squares the moving piece visits, e.g.
`2,2>4,4` (a single capture) or `2,2>4,4>6,6` (a chain). Since only the maximal,
highest-priority capture sequences are legal, clicking through a chain naturally
forces it to completion.
