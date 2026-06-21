# Turkish Draughts (Dama)

Turkish draughts, played on **all 64 squares** of an 8×8 board with **orthogonal**
(straight-line) movement instead of the diagonal movement of standard checkers.

## Objective
Capture all of the opponent's pieces, or leave them with no legal move.

## Board & setup
All 64 squares are used. Each side has **16 men** on its 2nd and 3rd ranks:

- **White** (player 0) on rows 1–2 (its back/1st rank, row 0, stays empty) and moves toward row 7.
- **Black** (player 1) on rows 5–6 (its back rank, row 7, stays empty) and moves toward row 0.

White moves first.

## Movement
- **Men** move **one square orthogonally — forward or sideways (left/right)** — to an
  empty square. They never move diagonally and never move backward.
- **Kings** move **any distance orthogonally** along a rank or file over empty squares
  (a flying rook). Kings have no diagonal movement.

## Capturing
- **Men capture** by jumping an **adjacent** enemy piece orthogonally (forward or
  sideways, never backward) to the empty square immediately beyond it.
- **Kings capture** by sliding along a rank or file over empty squares to a single
  enemy piece, then landing on **any** empty square beyond it in the same line.
- Captured pieces are **removed immediately** during the sequence (the Turkish rule):
  a square freed by an earlier capture in the same chain can be flown over or landed
  on later in that chain.
- **Capture is mandatory**, and the **maximum-capture rule** applies: among all
  possible capturing sequences you must play one that removes the **greatest number**
  of enemy pieces. (Only piece count is compared — there is no king-priority tie-break;
  any maximal sequence is allowed.)
- A multi-capture chain continues until the moving piece can capture no more.

## Promotion
A **man** that ends its move on the opponent's back rank (row 7 for White, row 0 for
Black) is **promoted to a king**. Promotion **ends the turn**: a man that reaches the
last rank during a capture does not continue capturing as a king on that move.

## Winning & draws
You **win** when the opponent has no pieces left, or has no legal move on their turn.

For guaranteed termination the game is **drawn** by a **60-ply no-progress rule** (no
capture and no man move — i.e. only king moves — for 60 consecutive plies) and by a
hard **400-ply cap**.

## Ruleset choices / omissions
- **King-vs-single-man:** the common rule that a lone king automatically wins against a
  single remaining man is **omitted**. Such an endgame is played out normally (and may
  reach a draw via the no-progress / ply-cap rules).
- **Maximum-capture tie-break:** only the number of captured pieces is maximized; the
  variant rule that prefers capturing with a king, or capturing kings, is not applied.
