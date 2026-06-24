# Dunsany's Chess

Dunsany's Chess (also "Dunsany's Game") is an asymmetric chess variant invented by
**Lord Dunsany in 1942**. One side is a normal chess army; the other is a swarm of
**32 pawns** with no king. It is closely related to Horde Chess; this package
implements the standard Dunsany ruleset.

## The armies

* **Black** has the ordinary 16-piece chess army in its normal starting position
  (back rank + eight pawns, on ranks 7-8) and the ordinary goal.
* **White** has **no king**. Instead White fields **32 pawns** filling **ranks
  1-4** completely (the four ranks nearest White's side).

```
Rank 8:  r n b q k b n r   (Black back rank)
Rank 7:  p p p p p p p p   (Black pawns)
Rank 6:  . . . . . . . .
Rank 5:  . . . . . . . .
Rank 4:  P P P P P P P P   (White pawns)
Rank 3:  P P P P P P P P
Rank 2:  P P P P P P P P
Rank 1:  P P P P P P P P
```

**Black moves first.**

## Movement

All pieces move exactly as in standard chess, with these specifics:

* Pawns move one square forward, capture one square diagonally, and may promote on
  the far rank (to Q, R, B or N). White's pawns promote on rank 8; Black's on rank
  1.
* **Only Black's pawns get the initial two-square move.** White's pawns *always*
  single-step — they never get the double-step, even from rank 2. Because a White
  pawn never makes a two-rank jump, **no White pawn can ever be captured en
  passant.** (Black's pawns can still be captured en passant in the ordinary way
  after a Black double-step, but in practice the relevant interaction rarely
  arises.)
* **Castling:** only Black can castle (Black is the only side with a king and
  rooks on home squares). White has no castling rights.
* Because White has no king, White is **never in check** and can **never be
  checkmated or pinned to a king** — every pseudo-legal White move is legal.

## Win conditions

* **Black wins** by **capturing all 32 White pawns** — the moment White has no
  pieces left on the board.
* **White wins** by **checkmating Black's king** in the ordinary way.

## Draws

* **Stalemate is a draw.** If the side to move has no legal move and is not in
  check, the game is drawn. This covers both a stalemated Black king and a White
  pawn army that still has pieces but no legal move available ("White's pawns run
  out of moves").
* The usual chess draws also apply: the fifty-move rule (100 half-moves without a
  pawn move or capture), threefold repetition, and insufficient mating material.
* A hard ply cap (600 plies) forces a draw to guarantee termination; in practice
  a real game ends long before this.

## Ruleset choices / interpretations

* **Annihilating the pawn army is decided as a board fact**, not inferred from
  "White has no move." When Black captures the last White pawn it becomes White's
  turn with an empty army; rather than scoring that as a stalemate draw, this
  package detects "White has zero pieces" and awards the game to Black. A White
  position that still has at least one pawn but no legal move is a genuine
  stalemate and is scored as a **draw**.
* **Insufficient material:** the shared chess core's draw test is used. Pawns
  count as mating material, so as long as the army has pawns the game is never
  declared an insufficient-material draw; this is consistent with the win
  condition, where a lone surviving pawn means the army is not yet annihilated.
* All other rules (promotion choices, en passant, fifty-move, repetition) follow
  standard chess as provided by the platform's shared chess engine.

## Relationship to Horde Chess

Dunsany's and Horde are both "pawn army vs. normal army." The differences this
package implements:

| | Dunsany's | Horde (lichess) |
|---|---|---|
| Pawn count / shape | 32, full ranks 1-4 | 36 (ranks 1-4 plus four on rank 5) |
| First to move | **Black** (pieces) | **White** (pawns) |
| Pawn-army double-step | **Never** | From rank 1 *and* rank 2 |

## Sources

* [Dunsany's chess — Wikipedia](https://en.wikipedia.org/wiki/Dunsany%27s_chess)
* [Dunsany's Chess — chessvariants.com](https://www.chessvariants.com/unequal.dir/dunsany.html)

## Correctness anchor

The opening position and a small opening perft are frozen in `selftest.py`, along
with rule-specific positions (White pawns never double-step, White is never in
check, Black wins by annihilation, White wins by checkmate, stalemate is a draw).
