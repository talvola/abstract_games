# Raumschach (Space Chess)

**Dr. Ferdinand Maack, 1907** — the oldest surviving three-dimensional chess
variant and a Recognized Chess Variant. Maack first experimented with an 8×8×8
array but settled on **5×5×5** as the nicer game, and the Hamburg Raumschach
club (founded 1919) fixed the modern rules.

These are the rules **as implemented** in this package. The primary source is
[chessvariants.com/3d.dir/3d5.html](https://www.chessvariants.com/3d.dir/3d5.html),
cross-checked against Wikipedia's *Three-dimensional chess → Raumschach*
section.

## Board & coordinates

Five stacked 5×5 boards ("levels") **A** (bottom, White's home) through **E**
(top, Black's home), together a 125-cell cube. A cell is named
**level · file · rank**, e.g. `Ac1`, `Ee5`. Files are `a`–`e`, ranks `1`–`5`,
levels `A`–`E`.

Internally a cell is `(file x = 0..4, rank y = 0..4, level z = 0..4)` and its
move-string id is `"level,col,row"` (= `z,x,y`). A move is a path
`"z,x,y>z2,x2,y2"`, with a promotion suffix `=Q/R/B/N/U`. The board renders as
the five levels side by side, **A on the left … E on the right**.

## Starting position

White occupies levels **A** and **B**; Black occupies levels **D** and **E**
(level **C** starts empty). 20 pieces per side (K, Q, 2R, 2B, 2N, 2U, 10P).

```
Level A (White)     Level B (White)     Level D (Black)     Level E (Black)
 R N K N R  (rank1)  B U Q B U  (rank1)  p p p p p  (rank4)  r n k n r  (rank5)
 P P P P P  (rank2)  P P P P P  (rank2)  b u q b u  (rank5)  p p p p p  (rank4)
```

Concretely: White — `Ra1 Ae1`, `Nb1 Nd1`, `Kc1`, `Ba1 Bd1`, `Ub1 Ue1`, `Qc1`
(on level B), pawns on `Aa2–Ae2` and `Ba2–Be2`. Black is the mirror on levels
D/E: `Ra5 Ee5`, `Nb5 Ed5`, `Kc5` (on level E); `Ba5 Dd5`, `Ub5 De5`, `Qc5`
(on level D); pawns on `Da4–De4` and `Ea4–Ee4`. **White moves first.**

## How the pieces move

Think of a cell as a little cube. Its neighbours are reached through the cube's
**faces** (orthogonal), **edges** (2-D diagonal), or **corners** (3-D diagonal).

- **Rook (R)** — slides through **faces**: any one coordinate changes (rank,
  file, *or* level = "an elevator"). 6 directions.
- **Bishop (B)** — slides through **edges**: exactly two coordinates change by
  ±1 (an ordinary diagonal within one of the three coordinal planes). 12
  directions.
- **Unicorn (U)** — slides through **corners**: all three coordinates change by
  ±1 (a pure 3-D space-diagonal / *triagonal*). It has **no** 2-D move. 8
  directions. The Unicorn is colour-bound to a triagonal sub-lattice: from its
  starting cell `Bb1` it can ever reach exactly **30** of the 125 cells.
- **Queen (Q)** — **Rook + Bishop + Unicorn = 26 directions.** *(CVP: "The Queen
  has the combined moves of Rook, Bishop and Unicorn"; Wikipedia: "6 faces plus
  12 edges plus 8 corners.")* **Yes — the Queen moves triagonally.**
- **King (K)** — "moves the same as the Queen but one step at a time": one step
  to any of the 26 adjacent cells (through a face, edge or corner). *(So the
  King, too, can step along a triagonal.)*
- **Knight (N)** — a **(0,1,2) leap**: one coordinate unchanged, the other two
  change by 1 and by 2 (any signs) — "one step as a rook then one step outward
  as a bishop in the same plane." 24 destinations, and it **leaps over** any
  pieces in between. (Much stronger than the 2-D knight: `Aa1–Bc1–Ac3` in two
  moves.)

Sliders (R/B/U/Q) move any distance until blocked; the first enemy piece on the
ray may be captured, and a friendly piece blocks.

### Pawns

Pawns are the subtle part; Maack himself wrote that "the greatest difficulties
and liveliest controversies… arose in answering… how are the pawns to move?"
This package implements the move set given by the CVP article's worked example
(closest to Maack's *Movement C*, the "new" Hamburg-club method), because that
source pins the exact squares:

- **Non-capturing (passive)**: one step **straight forward** (toward the enemy
  side — `+rank` for White, `−rank` for Black) **or** one step **straight up**
  for White / **straight down** for Black (absolute level). *"White Pawn:
  straight-forward or straight-upward."*
- **Capturing**: one step diagonally, either **forward within the level**
  (`±file, +rank` for White) **or sideways-and-up/down** (`±file, +level` for
  White; `±file, −level` for Black).

So (per the CVP example) a **White pawn on `Ac2`** may move to `Ac3` or `Bc2`,
and capture on `Ab3`, `Ad3`, `Bb2`, `Bd2`. It does **not** capture the
"forward-and-up" cell `Bc3` — that is Anthony Dickins' variant (`A Guide to
Fairy Chess`), which the CVP author explicitly dislikes; we exclude it.

- **No two-step first move**, therefore **no en passant.**
- **Promotion**: a pawn reaching the far rank — **rank 5 for White, rank 1 for
  Black** (on any level) — promotes to **Q, R, B, N, or U**. *(Interpretation:
  the sources say "the last (or fifth) rank"; CVP phrases White's promotion zone
  as "the far side of level A and level B." We treat the promotion condition as
  simply reaching the far rank, on whichever level the pawn is on — the natural,
  always-reachable reading.)*

**Other Maack pawn variants** (not implemented; documented for faithfulness):
*A "old"* — free up/down on the z-axis, captures only toward the front edge;
*B "restricted"* — like C but without the sideways-up capture; *D "all-sided"* —
moves/captures in every direction and **cannot promote**. We ship the CVP/C set.

## No castling

There is **no castling** in Raumschach (both sources are explicit).

## Winning, check & draws

- **Check / checkmate / stalemate** work as in orthodox chess, in three
  dimensions: you may not leave your King attacked, **checkmate wins**, and
  **stalemate is a draw**.
- Additional draws (for a guaranteed finite game): **threefold repetition**, a
  **50-move** no-progress rule (100 half-moves with no capture and no pawn
  move), and a hard **400-ply cap**.

## Notation in the move log

Moves are shown as `Ub1-b1`-style **level+file+rank** with `x` for a capture,
e.g. `Nb1-c3`, `Bxe5`, `c4-c5=Q`.

## Anchors (verification)

- **perft** from the opening: **perft(1) = 61**, **perft(2) = 3 608**,
  **perft(3) = 236 510** (frozen in `selftest.py`).
- Single-piece move counts from the central cell `Cc3` on an otherwise empty
  board: Rook 12, Bishop 24, Unicorn 16, Knight 24, Queen 52, King 26.
- Unicorn reachability confirms Wikipedia's stated "30 cells" from `Bb1`.

### Derivation of perft(1) = 61 (White's opening moves)

No White piece is pinned and the King is safe, so every pseudo-legal move is
legal. Counting by piece:

| Piece(s) | Moves | Why |
|---|---:|---|
| 5 pawns on level A | 5 | each pushes 1 forward; the "up" cell is blocked by the level-B pawn above it |
| 5 pawns on level B | 10 | each pushes forward **and** up into empty level C |
| Knights `Nb1`,`Nd1` | 12 | 6 each (the 24 leaps, minus those off-board or onto own pieces) |
| Rooks `Aa1`,`Ae1` | 0 | boxed in by own knight, pawn and bishop on all three axes |
| Bishops `Ba1`,`Bd1` | 13 | 6 + 7; several rays climb through empty C/D up to a Black level-E pawn (a capture) |
| Unicorns `Ub1`,`Ue1` | 7 | 4 + 3 triagonal steps into empty space (two reach a Black pawn) |
| Queen `Qc1` | 14 | 3 up the column + 7 bishop-type + 4 unicorn-type rays |
| King `Kc1` | 0 | surrounded by its own pieces |

Total **15 + 12 + 0 + 13 + 7 + 14 + 0 = 61**. Five of the 61 are captures of
Black's level-E pawns along cleared up-and-forward diagonals.
