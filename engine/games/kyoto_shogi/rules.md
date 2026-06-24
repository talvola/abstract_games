# Kyoto Shogi (京都将棋)

Kyoto Shogi, devised by **Tamiya Katsuya around 1976**, is a tiny 5×5 member of
the Shogi family. Its signature is the **flip**: every piece is a single token
with two faces, and a piece **flips to its other face every time it moves** — so
each piece alternates between two roles, turn after turn. The flip replaces
promotion entirely; there is no promotion zone.

## Board & setup

A **5×5** board. Each player has **five** tokens on their back rank. From each
player's own left, the back rank is:

```
T S K G P     ← White (Gote), top   (a 180° rotation)
. . . . .
. . . . .
. . . . .
T S K G P     ← Black (Sente), bottom
```

All five tokens start showing the face listed above (Tokin, Silver, King, Gold,
Pawn). **Black (Sente) moves first.**

## The flipping pairs and how each face moves

Every token has two faces (a *pair*). Both faces use the standard Shogi moves
("forward" is toward the far side, for each player):

| Pair | Face A | moves | Face B | moves |
|------|--------|-------|--------|-------|
| **T ↔ L** | **Tokin** (T) | as a **Gold general** | **Lance** (L) | slides any distance straight **forward** |
| **S ↔ B** | **Silver** (S) | Silver general | **Bishop** (B) | slides any distance **diagonally** |
| **G ↔ N** | **Gold** (G) | Gold general | **Knight** (N) | the Shogi **Knight**: jumps two squares forward then one sideways (forward only) |
| **P ↔ R** | **Pawn** (P) | one step straight **forward** | **Rook** (R) | slides any distance **orthogonally** |
| **King** | **King** (K) | one step in any of the 8 directions — **never flips** | — | — |

- **Gold general:** one step forward, diagonally-forward (both), sideways (both),
  or straight back — six directions (no backward diagonals).
- **Silver general:** one step forward, diagonally-forward (both) or
  diagonally-back (both) — five directions (no sideways, no straight back).

**Letter legend:** T=Tokin, L=Lance, S=Silver, B=Bishop, G=Gold, N=Knight,
P=Pawn, R=Rook, K=King. The board glyph and the reserve-tray chip use the same
letter, so a piece reads the same on the board and in hand.

## The flip (the signature rule)

**Every move flips the moving token to its other face, except the King.** A piece
moves *as its current face* — that face is what reaches the destination — and the
token then flips. The flipped board is exactly what the opponent then faces, so
**check, escape from check and checkmate are all judged on the board as it stands
after the flip.**

Example: a Silver (S) that moves lands and becomes a Bishop (B); if that Bishop
now attacks the enemy King, it is check — delivered by the post-flip Bishop, not
the Silver that made the move.

Unlike ordinary Shogi, a piece **may** move into a square from which its new face
could never move again (e.g. a Rook moving onto the far rank, where it becomes a
Pawn with nowhere to go) — that is legal here.

## Drops

A captured token switches sides and joins your hand. On a later turn you may
**drop** it onto any empty square — and you **choose which face it lands showing**
(the drop is the face-choice). A dropped token does **not** flip; it simply
enters showing your chosen face. There are **no** drop restrictions (no two-pawns
rule, no last-rank rule, no promotion zone) — the only requirement is that the
target square is empty. In the reserve tray, each held token appears as **both**
of its faces; click the face you want, then click an empty square to drop it.

## Winning & draws

You win by **checkmating** the enemy King (the King is attacked and the opponent
has no legal reply). As an implementation safeguard against endless games, a
position repeated four times, or reaching the ply cap (300), is scored a **draw**.

## Notes / interpretations

- Rules verified against **Wikipedia "Kyoto shogi"** and the **pychess.org** and
  **lishogi.org** Kyoto-shogi implementations. The piece pairs (Tokin/Lance,
  Silver/Bishop, Gold/Knight, Pawn/Rook), the flip-every-move rule, the King
  never flipping, the face-choosing drop, and the absence of any promotion
  zone/drop restrictions are all from those sources.
- The post-flip timing of check (the flipped board is the position the opponent
  faces) is the standard digital implementation; it is the only consistent
  reading of "you flip the piece over after it moves."
