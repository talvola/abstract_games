# Antichess

Antichess (also called **Losing Chess** or **Giveaway**) on an 8×8 board — the
**lichess variant**. The goal is *inverted*: you are trying to **lose**.

## Objective
You **win** as soon as one of these happens:
- You have **no pieces left** (you have given everything away), or
- It is your turn and you have **no legal move** (so being "stalemated" is a
  **win** here, not a draw).

## Board & setup
The usual chess array: pawns on the second rank and `R N B Q K B N R` behind
them. White is player 1 and moves first; Black is player 2.

## How it differs from standard chess
- **The king is not royal.** There is **no check, no checkmate and no
  castling**. The king is an ordinary one-square piece that can be captured like
  any other, and a pawn may even **promote to a king**.
- **Capturing is compulsory.** If you have *any* capture available you **must**
  make a capture this turn. If several captures are available you may choose
  which one to make; only when no capture exists at all may you make a quiet
  (non-capturing) move.
- Pawns, knights, bishops, rooks and queens move exactly as in standard chess
  (the king moves one square in any direction).
- **En passant** is kept, and counts as a capture — so it is forced when it is
  your only capture.
- **Promotion** on reaching the far rank may be to **Q, R, B, N, or K** (king
  promotion is legal in Antichess).

## Winning & draws
- First player to **lose all pieces** or to be left with **no legal move** wins.
- Note that capturing your opponent's *last* piece makes **them** win (they now
  have no pieces) — so capturing is not always good, even though it is forced.

### Draws (for guaranteed termination)
Antichess games normally end quickly by annihilation, but to guarantee the game
always terminates this implementation also draws by:
- the **fifty-move rule** (100 half-moves with no capture and no pawn move),
- **threefold repetition** of the position, and
- a hard **ply cap** of 600 half-moves.

## Ruleset choices in this implementation
There are several published Antichess variants that differ on edge cases; this
package follows the **lichess** ruleset:
- **King promotion is allowed** (some "Suicide chess" rules forbid it).
- **Stalemate / no-legal-move is a WIN** for the player who cannot move (lichess
  rule). Some older "Losing Chess" rules instead score it for the player *with
  fewer pieces*, or as a draw — this package does **not** use those.
- Captures are **compulsory but free choice** among available captures (there is
  no priority ordering such as "must capture the most valuable").
- The perft node counts from the opening position
  (20 / 400 / 8067 / 153299 for depths 1–4) match lichess/shakmaty and
  python-chess's Antichess board, confirming the move generator and the
  forced-capture rule.

## In this implementation
- Moves are entered as the clickable cell path `from>to` (e.g. `e2-e4`); when a
  capture is available the UI offers only capturing moves. Promotion shows a
  Q/R/B/N/K picker.
- Antichess is weakly solved — `1. e3` is a win for White — but that is not
  something this package tries to enforce or verify; correctness rests on the
  perft anchor plus the rule-specific positions in `selftest.py`.
