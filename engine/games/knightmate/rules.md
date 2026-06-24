# Knightmate

**Knightmate** (also called *Mate*) is a chess variant invented by **Bruce Zimov** in
1972. It plays exactly like chess **except that the royal piece is a Knight** and the
ordinary knights are replaced by non-royal **Commoners**. White (player 0) moves first.

## The two substitutions

| Orthodox chess | Knightmate | Moves like | Royal? |
|----------------|------------|-----------|--------|
| King (e1/e8) | **Royal Knight** | a Knight — the (1,2) "L" leap | **Yes** — you win by checkmating it |
| Knight (b/g files) | **Commoner** | a King — one square any direction | No — captured like any other piece |

- The **Royal Knight** sits on the king's home square (**e1 / e8**) and moves as a
  knight. It is the royal piece: "check" / "checkmate" / "stalemate" are defined
  against it. You win by checkmating the opponent's Royal Knight.
- A **Commoner** sits on a knight's home square (**b1, g1 / b8, g8**) and moves like a
  king (one step in any of the eight directions). It is **not** royal: it can capture
  and be captured like any other piece, and an attack on a Commoner is *not* check.

So the back rank is: **Rook, Commoner, Bishop, Queen, Royal Knight, Bishop, Commoner,
Rook**. Pawns are normal and start on the second/seventh ranks.

## Standard chess rules that still apply

- **Pawns** move, capture, double-step from home, and take *en passant* exactly as in
  chess.
- **Castling** is present. The Royal Knight castles with a rook under the same
  conditions as a king in chess (neither has moved, the squares between are empty, and
  the knight does not start, pass through, or land on an attacked square). In castling
  the Royal Knight makes the **king's two-square horizontal jump** (not a knight move),
  so the result is the usual chess castle. King-side O-O: `e1→g1`, rook `h1→f1`;
  queen-side O-O-O: `e1→c1`, rook `a1→d1` (and the mirror for Black).
- **Draws:** stalemate (Royal Knight not in check but no legal move), the fifty-move
  rule, threefold repetition, and insufficient material.

## Pawn promotion

A pawn reaching the far rank promotes to **Queen, Rook, Bishop, or Commoner** —
**but NOT to a (royal) Knight**. (Promoting to a second royal knight is not allowed;
the Commoner is the king-mover you may promote to.)

## How royalty is wired (implementation note)

The shared chess engine (`agp.chesslike`) locates "the king" — the piece whose attack
is *check* — purely by the piece **letter `"K"`**. Knightmate therefore keeps the royal
piece's letter as `"K"` but gives that letter **knight movement**, and adds a separate
Commoner piece (letter `"C"`) with **king movement** and no royal status:

- `"K"` → `([], KNIGHT)` — the Royal Knight (leaps as a knight, *is* royal).
- `"C"` → `([], ALL8)` — the Commoner (steps as a king, ordinary capturable piece).

Castling reuses standard 8×8 geometry (the Royal Knight sits on the king's home square),
with one Knightmate-specific guard: a genuine castle is the royal piece's two-square move
on the **same rank**, whereas a knight's `(2,1)` leap also shifts two files but changes
the rank — so only same-rank two-file moves are treated as castles. Insufficient-material
draws are kept conservative: only a position with nothing but the two Royal Knights is
declared a draw.

## Move notation

Moves are clickable cell paths `"fc,fr>tc,tr"` (e.g. the opening royal-knight move
`e1→f3` is `4,0>5,2`); castling is the royal knight's two-square move (`4,0>6,0` for
O-O); a promotion appends `=Q`, `=R`, `=B`, or `=C`.

## Correctness anchor (engine-derived perft)

There is no standard published Knightmate perft, so these opening node counts are
derived from this engine's move generator and frozen as a regression lock
(`selftest.py`). Depth 1 = **18** is hand-verifiable: 8 pawns × 2 steps = 16, plus the
Royal Knight on e1 reaching d3 and f3 = 2; every other piece is blocked at the start.

| depth | nodes |
|------:|------:|
| 1 | 18 |
| 2 | 324 |
| 3 | 6 765 |
| 4 | 139 774 |

## Sources

- chessvariants.com — Knightmate (the "different objectives" page): the official source
  linked from this game.
- Wikibooks *Chess Variants/Knightmate*; chess.com "Variant of the week: Knightmate".

These sources agree that Knightmate **has** castling (royal knight + rook) and that
pawns promote to a Commoner but never to a knight — overriding the common assumption
that a knight-royal variant must drop castling.
