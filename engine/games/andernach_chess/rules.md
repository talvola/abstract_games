# Andernach Chess

Andernach Chess is **standard chess** with a single extra rule about captures.
It is named after the German town of Andernach, where it was played at a 1993
problemists' meeting.

## The Andernach rule

> **A piece that makes a capture changes to the opponent's colour** and stays on
> the square it captured on.

So if **White** captures an enemy piece with a knight, that square afterwards
holds a **Black** knight. The captured piece is removed as usual; it is the
*capturing* piece that switches sides.

- **Non-capturing moves are completely normal** — no colour change.
- **Kings are the sole exception.** A king that captures does **not** change
  colour, and a king is **never** produced by a colour change (you can never gain
  or lose a king through this rule). Each side always has exactly one king.

## How the standard rules still apply

Everything else is orthodox chess:

- **Movement** of every piece is identical to standard chess.
- **En passant** counts as a capture, so the capturing pawn **changes colour**
  (it ends on its diagonal landing square as an enemy pawn).
- **Promotion**: a pawn that captures onto the last rank first **promotes**
  (to Q/R/B/N) and then **changes colour** — it becomes the *opponent's* promoted
  piece on that square. (Non-capturing promotions are normal.)
- **Castling** never involves a capture, so it never triggers a colour change; it
  works exactly as in standard chess.
- **Check / checkmate / stalemate** are standard, computed on the resulting
  board. Because a capture hands the capturing piece to the opponent, a capture
  can expose your own king (the piece you captured with is now an enemy piece) —
  such a move is **illegal**, just like any move that leaves your king in check.
- **Draws**: the fifty-move rule, threefold repetition and insufficient material
  all apply as in standard chess.

White (player 0) moves first.

## Moves

Moves use the platform's clickable cell-path notation, e.g. `4,1>4,3`. Castling
is the king's two-square move (the rook follows automatically). A promotion
appends the chosen piece, e.g. `=Q`.

## Implementation notes (rules as implemented)

- The colour-flip-on-capture is applied in a single board transform that is used
  both by the move-legality filter and by the actual move application, so a
  capture that would leave your own king in check (because the capturing piece
  became an enemy piece) is correctly rejected as illegal.
- Order at the last rank: **promote, then flip colour** — the capturing pawn
  becomes the opponent's promoted piece. Promotion targets remain Q/R/B/N (never
  a king), so the king-exemption is unaffected.

## Opening perft (engine-derived correctness anchor)

| depth | nodes  | vs. standard chess |
|------:|-------:|--------------------|
| 1     | 20     | same               |
| 2     | 400    | same               |
| 3     | 8902   | same               |
| 4     | 197410 | differs (197281)   |

Depths 1–3 match standard chess because no capture is available until move 3, and
a colour-flip on a leaf capture does not change the number of legal moves at that
ply; the rule first changes the node count at depth 4, where a flipped piece
alters the descendants.
