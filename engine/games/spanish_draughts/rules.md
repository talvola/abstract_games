# Spanish Draughts (Damas Españolas)

The traditional Spanish/Portuguese 8×8 draughts game (*dama*), implemented from
**ludoteka.com** and **mindsports.nl** (Ed van Zon, *On the evolution of draughts
variants*). Played on **one colour of the board only**, 12 men per side. Also
played in parts of South America and North Africa.

## Objective
Leave your opponent with **no legal move** — by capturing all their pieces or by
blocking them. That player loses.

## Board & setup
The playing squares are those where `(col + row)` is **even**. This parity puts
each player's **near-right square on a light (non-playing) square** and the
**double corner on the player's left** — the Spanish orientation, the **mirror of
Italian** (whose near-right square is dark). Each side starts with **12 men** on
the three ranks nearest them: **White** on rows 0–2 (moves toward row 7) and
**Black** on rows 5–7 (moves toward row 0). **White moves first.**

## Movement (no capture)
- **Men** move one square diagonally **forward** to an adjacent empty square.
- **Kings are FLYING** ("long" kings): a king slides **any distance** along a
  clear diagonal to any empty square, forward or backward.

## Capturing
- **Men capture FORWARD only** — a man jumps an adjacent enemy piece and lands on
  the empty square immediately beyond it, in a **forward** diagonal only. Men
  never capture backward. **A man CAN capture a king** (a man may jump *any*
  enemy piece, man or king).
- **Flying kings capture by flying:** a king slides along a diagonal over empty
  squares, jumps a single enemy piece that has at least one empty square beyond
  it, and lands on **any** empty square past it along that same diagonal —
  **forward or backward** — then may continue.
- **Capture is mandatory** and continues while the moving piece can jump again.
  Captured pieces are **removed only at the end** of the sequence, and a piece may
  **not be jumped twice** in one sequence (jumped pieces stay on the board as
  blockers until the move is done).

### Maximum-capture with the quantity → quality priority
When several capture sequences are available you must play one selected by this
priority order:

1. **Quantity — most pieces:** capture the greatest *number* of pieces.
2. **Quality — most kings:** among the sequences tied on piece count, capture the
   greatest *number of kings*.
3. **Free choice:** any sequences still tied may be chosen freely.

Spanish has **no** Italian-style "must capture *with* a king" or "king encountered
earliest" sub-rules — only quantity then number-of-kings.

## Promotion
A man becomes a **king** only if it **ends its move on the far rank** (row 7 for
White, row 0 for Black). A man that reaches the last rank during a capture **stops
there** and promotes — it does not continue jumping as a king that turn. Because
men capture forward only, reaching the last rank is always the end of a sequence.

## Winning & draws
You **win** when the opponent has no legal move on their turn.

For guaranteed termination this implementation adds two pragmatic draw rules:
- a **50-ply no-progress** rule — 50 consecutive plies with no capture and no man
  move (only kings shuffling) is a draw; and
- a hard **400-ply cap**.

(Official play uses other draw conventions — king-endgame counters and repetition
— which are not modelled here.)

## How Spanish differs from its 8×8 siblings
All are 8×8 with 12 men. The load-bearing differences:

| Rule | **Spanish** | Italian | English Checkers | Brazilian |
|---|---|---|---|---|
| Man capture direction | **forward only** | forward only | forward only | forward **and** backward |
| Man may capture a king | **yes** | **no** | yes | yes |
| King type | **flying** | **short** | short | flying |
| Capture is maximal? | **yes** | yes | no (any) | yes |
| Capture priority | **pieces, then kings** | pieces → with-king → most-kings → earliest-king | — | pieces only |
| Orientation | near-right **light** (double corner left) | near-right dark | lower-left dark | lower-left dark |

**Distinctness statement.** Spanish is *not* a clone of any existing package:

- **vs Italian Draughts** — the two decisive Italian rules are inverted:
  Italian men **can never capture a king** and Italian kings are **short
  (non-flying)**; **Spanish men CAN capture kings and Spanish kings are flying.**
  Spanish also drops Italian's extra "capture-with-a-king" and "earliest-king"
  priority sub-rules, using only *quantity then number-of-kings*.
- **vs Brazilian Draughts** — Brazilian **men capture backward as well as
  forward**, and its capture rule is *quantity only* (a king and a man count the
  same); **Spanish men capture forward only** and Spanish adds a *most-kings*
  quality tiebreak.
- **vs English Checkers** — checkers has **short kings** and does not force the
  maximum capture; Spanish has **flying kings** and mandatory maximum-with-quality
  capture.

So Spanish is the unique combination *forward-only capturing men that can take
kings + flying kings + max-capture ranked by pieces-then-kings*.

## Move notation
Moves are `>`-separated paths of the squares the moving piece visits, e.g.
`0,2>2,4` (a single capture) or `3,3>5,5>7,3` (a chain). Since only the maximal,
highest-priority capture sequences are legal, clicking through a chain naturally
forces it to completion.
