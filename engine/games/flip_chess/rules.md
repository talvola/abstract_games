# Flip Chess / Flip Shogi

A pair of chess variants by **John William Brown (1998)**, described in his book
*Meta-Chess* and entered (winning second prize) in Hans Bodlaender's *38-square
challenge*. Thomas E. Havel collaborated. This page documents the ruleset **as
implemented**; the "official source" button links to the Chess Variant Pages
write-up. Flip Chess and Flip Shogi are the same game on the same board with the
same pieces — Flip Shogi just adds drops — so they are one package with a
**Variant** option (default *Flip Chess*).

## The board

A rectangle of **7 files (a–g) × 6 ranks (1–6) with its four corners removed**
(a1, a6, g1, g6), leaving **38 squares**. White's home rank is rank 1 (bottom of
the screen) and Black's is rank 6 (top); White advances toward higher ranks,
Black toward lower. Every piece moves by ordinary chess geometry on this grid —
there is no loop-effect or bridging (that belongs to *Crazy 38's*, a different
38-square game).

## Flip pieces

Every piece is a **double-sided counter**. The starting side-up is the first of
each pair:

| Front | Back | |
|---|---|---|
| **Pawn (P)** | **Berolina Pawn (X)** | pawn family |
| **Bishop (B)** | **Rook (R)** | major family |
| **Ferz (F)** | **Knight (N)** | minor family |
| **King (K)** | — | royal, never flips |
| **Prince (Pc)** | — | promotion piece, never flips |

**Rule 1 — flipping.** A non-King piece may flip to its other side **at the close
of its move**, *or* **flip in place as a whole move** (spending the turn without
moving). Flipping in place is only possible when you are not in check.

**Rule 2 — promotion.** A Pawn or Berolina Pawn that reaches the last rank
**promotes (forced) to a Prince**.

**Rule 3 — a bare King loses.** Reducing your opponent to a lone King wins the
game at once (in Flip Shogi, also with an empty reserve).

### How the pieces move

- **Pawn (P)** — steps one square straight forward (no capture) and captures one
  square diagonally forward. (No initial double step, no en passant — the
  reference implementation has neither.)
- **Berolina Pawn (X)** — the mirror pawn: steps one square **diagonally** forward
  (no capture) and captures one square **straight** forward.
- **Ferz (F)** — steps one square diagonally.
- **Knight (N)** — the ordinary chess knight leap.
- **Bishop (B)** — slides any distance diagonally.
- **Rook (R)** — slides any distance orthogonally (no castling).
- **King (K)** — steps one square in any direction; may not move into check (royal).
- **Prince (Pc)** — steps one square in any direction, but is **not royal** — it is
  purely a promotion piece with no reverse side.

## Object of the game

Win by **checkmating** the enemy King **or** by **baring** it (rule 3). Stalemate
(no legal move while not in check) is an honest **draw**; four-fold repetition and
a hard ply cap (300) also draw, since flips and drops recycle material.

## Flip Shogi (the *shogi* option)

All of the above, plus shogi-style drops:

- **Rule 4–5.** A captured piece switches sides into the capturing player's
  reserve; on your turn you may **drop** a reserved piece onto an empty square
  instead of moving. A drop is a full move.
- **Rule 6.** A piece may be dropped with **either side up** (a captured
  Bishop/Rook token may re-enter as a Bishop *or* a Rook, etc.). A captured
  Prince re-enters as a Pawn token.
- **Rule 7.** A drop may be made **only to attack** — the dropped piece must
  threaten at least one enemy piece from its landing square.
- **Rule 8.** Pawn / Berolina drops are limited to **your own first two ranks**.

A dropped piece must, as always, leave your own King safe. Because reserve
tokens are double-sided, the drop tray shows the **same token count under both of
its faces** — dropping one face spends the token for the other, too.

## Documented interpretations

The 1998 rules are terse; a few points are resolved here, anchored to the
author-sanctioned Zillions file (`flip.zip` / `Flip3.zrf`, by Hans Bodlaender):

- **No double step / en passant.** The reference ZRF defines both but attaches
  them to an unreachable "third rank" zone / to no piece, so a forward-moving
  pawn never triggers them. Implemented as a plain one-step pawn.
- **Flip in place** is included because the primary CVP rules text explicitly
  allows a flip "as a move in itself", even though the reference ZRF omits it.
- **Drop-attacks (rule 7)** is read as *threatening an enemy piece* (a friendly
  piece being defended does not qualify). Attacking the enemy King (a drop that
  gives check) counts.
- **Stalemate** and **repetition** are scored as honest draws.
