# Courier Chess (Kurierspiel)

A medieval German chess variant (c. 1200, played into the early 19th century),
on a **12×8** board. Famous for introducing the **Courier** — a piece that
moves exactly like the modern bishop — roughly three centuries before that move
entered standard chess. This package implements the rules **as listed below**
(historical sources disagree on a few minor points; the choices made here are
documented in *Ruleset choices*).

## Objective
Checkmate the opponent's **King**. (The King is the only royal piece — the
king-like *Mann* is **not** royal and may be safely captured.)

## Board & setup (12 files × 8 ranks)
Files run **a–l** (12 columns); each side has a 12-piece back rank plus 12
pawns on the **third** rank. The standard array (after H. J. R. Murray,
*A History of Chess*, 1913, and the Lucas van Leyden painting *The Chess
Players*), from each player's left to right, is:

```
R  N  A  C  K  M  F  W  C  A  N  R
```

- **R** Rook, **N** Knight, **A** Alfil (medieval "Bishop"), **C** Courier,
  **K** King, **M** Mann (Sage), **F** Ferz (the medieval Queen),
  **W** Schleich (Wazir).
- Black's array is the **left–right mirror** of White's, so the central
  King / Mann / Ferz / Schleich block of one side faces the other's. With files
  a = 0 … l = 11: White King on **e**, Mann **f**, Ferz **g**, Schleich **h**;
  Black Schleich **e**, Ferz **f**, Mann **g**, King **h**.
- Pawns fill the **third rank** (White rank 3, Black rank 6).

## The pieces
| Piece | Symbol | Move |
|---|---|---|
| **King** | K | One square any direction. **Royal** (checkmate target). |
| **Queen / Ferz** | F | One square **diagonally** (the weak medieval queen). |
| **Rook** | R | Any distance orthogonally (as modern chess). |
| **Knight** | N | The (1,2) leaper (as modern chess). |
| **Bishop / Alfil** | A | The Shatranj **elephant**: a **(2,2) leaper** — jumps exactly two squares diagonally, **leaping over** any piece between. |
| **Courier** | C | **Unlimited diagonal slider** — i.e. **exactly the modern bishop**. This is the piece the game introduced. |
| **Mann / Sage** | M | Like a King (one square any direction) but **not royal**: it can be captured and is never "in check". |
| **Schleich / Wazir** | W | One square **orthogonally** only. |
| **Pawn** | P | One square straight forward; captures one square diagonally forward. |

The Courier (modern bishop) and the Alfil (Shatranj elephant) are different
pieces with different reach, so each side has *both* — two Couriers **and** two
Alfils, plus the orthogonal-only Schleich and the diagonal-only Ferz.

## Play
- **Pawns** step a **single** square — there is **no two-square first move** and
  therefore **no en passant**. A pawn promotes on reaching the last rank, and
  may promote **only to a Ferz** (the only available promotion in the medieval
  game, since the Ferz was the "promoted pawn" piece).
- **No castling.**
- Checkmate wins. **Stalemate is a draw.**

## Ruleset choices (where sources differ)
- **Opening ritual omitted.** Historically the first moves were a fixed,
  ceremonial advance (each player pushed both rook-pawns and the queen-pawn two
  squares, then moved the Schleich) before free play began. Because pawns here
  have no double step, that ritual is **not** implemented; play is free from
  move one. This affects only the first few moves, not the piece rules.
- **Pawn double step / en passant: off** (faithful to the medieval single-step
  pawn).
- **Promotion to Ferz only** (no choice of piece).
- **Stalemate = draw** (modern convention; the medieval treatment is unclear).
  Threefold repetition, a 50-move (100-ply) counter, and a hard ply cap also draw,
  to guarantee the game terminates — the Ferz, Alfil and Schleich are short-range,
  so play can otherwise grind on for a long time. Only **bare king vs bare king**
  is treated as insufficient material; the short-range pieces are real mating
  material (e.g. K + two Manns can checkmate), so such endgames are played out
  (and draw by the ply cap only if genuinely dead).
- **Mann is non-royal** (it moves like a king but losing it does not lose the
  game and it is not subject to check). The **King** is the sole royal piece.

## Notes / source
Official reference: <https://en.wikipedia.org/wiki/Courier_chess>
