# Janggi (Korean Chess)

A two-player game on a **9-file × 10-rank** board — the Korean sibling of Xiangqi.
Player 0 is **Cho** (uppercase pieces, home rows 1–5) and moves first; player 1 is
**Han** (lowercase, rows 6–10). Pieces rest on the points of the grid. Each side has
a 3×3 **palace** with **diagonal lines** drawn from the palace centre to its four
corners; those diagonals are real movement paths for the pieces noted below.

> Rendering note: the board is drawn as a 9×10 grid of cells with lettered pieces.
> This is functionally identical to the traditional intersection board (same
> adjacency). The palace and its diagonals are enforced in the rules; the
> decorative palace diagonal lines are not yet drawn — a cosmetic touch for later.
> Unlike Xiangqi, **there is no river restriction** in Janggi.

## Starting setup

This package uses the standard **symmetric** opening (each side mirrors the other,
with no per-side horse/elephant swap):

```
R H E A . A E H R     ← rank 10 (Han back rank)
. . . . g . . . .     ← Han general on the centre file
. c . . . . . c .     ← Han cannons (files b, h)
s . s . s . s . s     ← Han soldiers
. . . . . . . . .
. . . . . . . . .
S . S . S . S . S     ← Cho soldiers
. C . . . . . C .     ← Cho cannons
. . . . G . . . .     ← Cho general on the centre file
R H E A . A E H R     ← rank 1 (Cho back rank)
```

The **general starts one row into the palace, on the centre file** — at (4,1) for
Cho and (4,8) for Han — *not* on the back rank. The horse/elephant placement is a
known **setup choice** in Janggi (each player may swap a horse and elephant before
play). This package ships the standard symmetric layout **R H E A . A E H R**; the
swap variant is not modelled.

## The pieces

| Letter | Piece | Moves |
|---|---|---|
| **G/g** | General | One step **orthogonally** *or* one step along a **palace diagonal**; confined to the 3×3 palace. |
| **A/a** | Guard | Exactly like the General (palace, orthogonal + palace diagonal). Two per side. |
| **H/h** | Horse | One step orthogonally **then** one step outward diagonally (a knight move). **Lame**: blocked if the orthogonal "leg" square is occupied. |
| **E/e** | Elephant | One step orthogonally **then two** steps outward diagonally (a 1+2 leap, longer than Xiangqi's elephant). Blocked if **any** square along the path is occupied. **Not** river-confined — crosses freely. |
| **R/r** | Chariot | Like a rook — any distance orthogonally, no jumping. **Also** slides along the **palace diagonal lines** while inside a palace. |
| **C/c** | Cannon | Moves **and** captures by jumping **exactly one** intervening "screen" piece (orthogonally any distance, or along a palace diagonal). See the cannon rules below. |
| **S/s** | Soldier | One step **forward** or **sideways** (never backward); no promotion. Inside the **enemy palace** it may also follow the palace diagonals (forward only). |

### Cannon rules (key Janggi differences from Xiangqi)

A Janggi cannon is more restricted than a Xiangqi cannon:

- It needs **exactly one screen** to move *or* capture (it cannot make quiet
  rook-style moves to empty squares without a screen).
- The screen **may not be a cannon** — a cannon cannot jump over another cannon.
- A cannon **may not capture a cannon**.
- (Consequently a cannon never interacts with another cannon at all.)

Cannons may also hop along the palace diagonal lines (one screen on the diagonal),
subject to the same restrictions.

## Check, bikjang, and winning

- Your move may not leave **your own general in check**.
- **Bikjang (facing generals).** This package implements bikjang as the
  Xiangqi-style **flying-general rule**: a move that would leave the two generals
  facing each other on an **open file** (no pieces between them) is **illegal**.
  This is a deliberate, documented simplification — the traditional tournament
  bikjang rule (the player who *creates* the facing offers a draw, which the
  opponent may decline by breaking it, otherwise the game is drawn) is **not**
  modelled here; instead the position simply cannot arise.
- A player with **no legal move loses** — both **checkmate** and **stalemate** are
  losses (as in Xiangqi).
- There are **no "points" / material-counting draws** and **no promotion**.

## Draws and termination

To guarantee the game always terminates, this package adds: a **120-ply
no-capture** draw, a **threefold-repetition** draw, and a hard **ply cap**.
(Tournament perpetual-check / perpetual-chase rules are simplified to the
repetition draw.)

## Correctness

The move generator has a self-computed **perft** regression baseline from the
standard symmetric opening — **31, 949, 29697** nodes at depths 1–3 — checked by
`selftest.py`, together with rule-specific positions (cannon jump-to-capture and
the three cannon restrictions, the elephant 1+2 leap with intermediate blocking,
General/Guard palace diagonals, soldier forward/sideways and enemy-palace
diagonals, the bikjang flying-general rule, and a constructed checkmate) and a
random self-play conformance sweep.
