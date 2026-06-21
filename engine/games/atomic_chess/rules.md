# Atomic Chess

Atomic Chess is a chess variant in which **captures cause explosions**. Pieces
move exactly as in standard chess, but capturing is dangerous: it can wipe out a
cluster of pieces at once, including your own. The goal is not to checkmate but
to **blow up (or capture) the enemy king**.

This package implements the **lichess / standard Atomic** ruleset, cross-checked
move-for-move against `python-chess`'s `AtomicBoard`.

## How pieces move

All pieces move exactly as in ordinary chess. **Castling**, **en passant**, the
pawn **double-step**, and **promotion** (to Q, R, B, or N) are all included and
work normally.

## The explosion

When a piece makes a **capture**, an explosion occurs centred on the **square the
capture happens on** (the square the moving piece would land on). Removed by the
blast are:

1. the **captured** piece,
2. the **capturing** piece itself (it does *not* survive on the square — it
   detonates), and
3. **every non-pawn piece** standing on the **eight squares** orthogonally and
   diagonally adjacent to the capture square (both colours).

**Pawns are blast-proof**: a pawn adjacent to an explosion survives. The only
pawn removed is the one actually captured (on the target square, or the pawn
removed by an *en-passant* capture). A pawn that itself makes a capture still
explodes its surroundings.

**Non-capturing moves cause no explosion.** Quiet moves, castling, and a
double-step that is not a capture are perfectly safe.

### En passant

An en-passant capture explodes around the **square the capturing pawn lands on**
(the passed-over square), not around the captured pawn's square. The captured
pawn is removed as well.

## Winning, losing, check

* You **win immediately** when the opponent's king is destroyed — whether by an
  explosion or (in principle) a capture. The game ends the instant a king leaves
  the board; nothing else matters at that point.
* A **king may never capture**: capturing always detonates the capturing piece,
  which would blow up your own king — that is illegal (see below). For the same
  reason, the two **kings may stand on adjacent squares**.
* You may **never play a move that would blow up your own king.** A capture whose
  explosion would catch your own king is illegal.
* **Check** works as in normal chess *except* that **while the two kings are
  adjacent ("connected"), there is no check** — no enemy piece can capture your
  king without exploding its own, so your king is not considered attacked.
* You **may ignore being in check if your move explodes the enemy king** —
  destroying the enemy king wins the game outright, so it takes precedence over
  your own king being under attack.
* **No castling** out of, through, or into check (as in standard chess). Squares
  that are only "attacked" because they are next to the enemy king do not block
  castling (consistent with `AtomicBoard`).

## End of the game

* **King exploded / captured** → the side whose king is gone loses.
* **Checkmate** → if the side to move is in check and has no legal move (no way
  to save its king and no way to explode the enemy king), it loses.
* **Stalemate** → side to move has no legal move and is *not* in check: draw.
* **Draws**: the fifty-move rule, threefold repetition, the ply cap, and the
  "only the two bare kings remain" case all draw. (Atomic insufficient-material
  is otherwise very permissive — almost any piece can deliver a mating explosion
  next to the enemy king — so we only declare a material draw when **both** sides
  have nothing left but their king.)

## Ruleset choices / interpretations

* Modelled on **lichess Atomic**, validated against `python-chess`
  `chess.variant.AtomicBoard` (move generation and game outcomes are checked to
  agree over many random games in `selftest.py`).
* **Insufficient material** is deliberately conservative: a forced material draw
  is declared only when both sides are reduced to a lone king, matching the
  spirit (though not every micro-case) of `AtomicBoard.has_insufficient_material`.
  All decisive results agree with `AtomicBoard`.
* Explosions that remove a king or rook from its home square also **revoke the
  corresponding castling rights**.
