# Horde Chess

Horde is an asymmetric chess variant (the [lichess](https://lichess.org/variant/horde)
ruleset). One side is a normal chess army; the other is a swarm of pawns with no
king. This package implements the standard lichess Horde.

## The armies

* **Black** has the ordinary 16-piece chess army in its normal starting position
  (back rank + eight pawns) and the ordinary goal.
* **White** has **no king**. Instead White fields **36 pawns** filling the bottom
  of the board.

The starting position is the official lichess Horde FEN:

```
rnbqkbnr/pppppppp/8/1PP2PP1/PPPPPPPP/PPPPPPPP/PPPPPPPP/PPPPPPPP w kq - 0 1
```

That is: White pawns fill ranks 1-4 completely, plus four extra pawns on rank 5
(files b, c, f, g); Black has its standard army on ranks 7-8. **White moves first.**

## Movement

All pieces move exactly as in standard chess. In particular:

* Pawns move one square forward, capture one square diagonally, may promote on
  the far rank (to Q, R, B or N), and may be captured *en passant*.
* **White's special rule:** a White pawn may take the two-square first move not
  only from its 2nd-rank home square but also **from the 1st rank**. (In ordinary
  chess no pawn ever stands on its own first rank; in Horde the back two ranks are
  full of pawns, and the rearmost ones still get the double step.) En passant
  applies to these double steps exactly as usual — if a White first-rank pawn
  jumps two squares past an enemy pawn's capture square, it can be taken en
  passant on the very next move.
* **Castling:** only Black can castle (Black is the only side with a king and
  rooks on their home squares). The lichess start FEN advertises Black's rights
  as `kq`; White has none.
* Because White has no king, White is **never in check** and can **never be
  checkmated or "pinned" to a king** — every pseudo-legal White move is legal.

## Win conditions

* **Black wins** by **capturing the entire horde** — i.e. the moment White has no
  pieces left on the board.
* **White wins** by **checkmating Black's king** in the ordinary way.

## Draws

* **Stalemate is a draw.** If the side to move has no legal move and is not in
  check, the game is drawn. This covers both a stalemated Black king and a White
  horde that still has pieces but no legal move available.
* The usual chess draws also apply: the fifty-move rule (100 half-moves without a
  pawn move or capture), threefold repetition, and insufficient mating material.
* A hard ply cap (600 plies) forces a draw to guarantee termination; in practice
  a real game ends long before this.

## Ruleset choices / interpretations

* **Annihilating the horde is decided as a board fact**, not inferred from "White
  has no move." When Black captures the last White piece it becomes White's turn
  with an empty army; rather than scoring that as a stalemate draw, this package
  detects "White has zero pieces" and awards the game to Black. A White position
  that still has at least one piece but no legal move is a genuine stalemate and
  is scored as a **draw**, matching lichess.
* **Insufficient material:** the shared chess core's draw test is used. Pawns
  count as mating material, so as long as the horde has pawns the game is never
  declared an insufficient-material draw; this is consistent with Horde, where a
  lone surviving pawn means the horde is not yet annihilated and Black has not yet
  won.
* All other rules (promotion choices, en passant, fifty-move, repetition) follow
  standard chess as provided by the platform's shared chess engine.

## Correctness anchor

The opening-position perft (legal-move tree node counts) matches the published
Stockfish / lichess Horde variant values: depth 1 = 8, depth 2 = 128,
depth 3 = 1274, depth 4 = 23310. See `selftest.py`.
