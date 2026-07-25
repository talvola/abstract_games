# Brusky's Hexagonal Chess

Yakov Brusky, USSR, **1966**. Chess on an irregular hexagonal board of **84 cells**
with *horizontal ranks* and *slanting files* — the opposite orientation family
from Gliński's hexagonal chess, whose files run vertically. Each side has the
orthodox army plus **one extra bishop** (three, one per hex colour) and **one
extra pawn** (ten), and the two kings stand on **opposite wings**, which gives
the starting position 180° rotational symmetry.

These are the rules **as implemented here**. The primary source is
[chessvariants.com — Brusky's Hexagonal Chess](https://www.chessvariants.com/rules/bruskyshexagonalchess)
(Fergus Duniho, 2023), which follows the "HEXAGONAL C" article of the first
edition of D. B. Pritchard's *Encyclopedia of Chess Variants* "in every detail".

## Board and notation

Ranks 1–8 run horizontally. Files a–l lean to the **left** as they go up. Files
d–i cover all eight ranks; the four corner files are cut short so the board is a
symmetrical hexagon rather than a parallelogram:

| file | a | b | c | d–i | j | k | l |
|---|---|---|---|---|---|---|---|
| ranks | 1–5 | 1–6 | 1–7 | 1–8 | 2–8 | 3–8 | 4–8 |

2×5 + 2×6 + 2×7 + 6×8 = **84 cells**. (A *right*-leaning file also exists —
a1‑b2‑c3‑d4‑e5‑f6‑g7‑h8 — but only the left-leaning one is used for naming, a
pure notation convention with no effect on movement.)

Cells come in **three colours**; each side's three bishops start one on each.

Internally a cell is the axial hex coordinate `q,r` with `q` = file index
(a = 0 … l = 11) and `r` = −rank, so `c4` is `2,-4`. Moves are
`"q,r>q,r"`, with an `=Q/=R/=B/=N` suffix for promotions; castling is written as
the king's two- or three-cell move.

## Setup

* **White** (rank 1, left to right): **R a1, N b1, B c1, Q d1, B e1, K f1, B g1,
  N h1, R i1**; pawns **a2–j2**.
* **Black** (rank 8, left to right as seen by *Black*, i.e. the 180° rotation of
  White's): **R d8, N e8, B f8, K g8, B h8, Q i8, B j8, N k8, R l8**;
  pawns **c7–l7**.

The kings therefore sit on **different wings** (f1 and g8). That is not a
transcription error — it is exactly what the rotational symmetry requires, and
it is confirmed by the article's setup diagram and by Jocly's piece tables.

## Pieces

Apart from castling and the pawns, every piece moves exactly as in Gliński's
hexagonal chess.

* **Rook** — any distance in any of the **6 orthogonal** directions (through
  cell edges), until it reaches an occupied cell. Along a rank, "orthogonal"
  is simply left/right.
* **Bishop** — any distance in any of the **6 diagonal** directions (through
  cell corners). Diagonals are colourbound; a bishop reaches only one third of
  the board. One of the six diagonals is **fully vertical** (straight up or down
  the board), which is why the c1/e1/g1 bishops and the queen can shoot past
  their own pawn wall on move 1 (c1‑d3‑e5‑f7: the diagonal only ever lands on
  odd ranks, so it skips the pawn rank entirely).
* **Queen** — rook + bishop, 12 directions.
* **King** — one cell in any of the same 12 directions. (A cell has 12 such
  neighbours in mid-board but as few as 5 in a corner such as l8, which is why a
  lone queen can checkmate there.)
* **Knight** — the 12-target hex leap: one cell orthogonally, then one more in
  an *outward* diagonal direction; equivalently, every cell of its fourth
  perimeter that a queen cannot reach. It jumps over anything in between.

### Castling

* **King's side** — the king moves **two** cells toward the rook on its own side
  (White `Kf1‑h1`, Black `Kg8‑e8`).
* **Queen's side** — the king moves **three** cells toward the rook beyond the
  queen (White `Kf1‑c1`, Black `Kg8‑j8`).
* In both cases the rook hops to the cell **adjacent to the king on the king's
  far side** (White `Ri1‑g1` / `Ra1‑d1`, Black `Rd8‑f8` / `Rl8‑i8`).
* All orthodox conditions apply: neither piece has moved, every cell between
  king and rook is empty, the king is not in check, and it neither passes
  through nor lands on an attacked cell. A cell the *rook* crosses may be
  attacked (as in orthodox chess).

### Pawn

The pawn is what makes this variant distinctive. Because ranks are horizontal, a
pawn has **two** forward orthogonal directions (for White, up-left and up-right).

1. **Advance** — one cell in *either* forward orthogonal direction, if empty.
2. **Double step** — from its own starting rank (White rank 2, Black rank 7) a
   pawn may advance two cells, but **both steps must be in the same direction**
   (both cells must be empty). Hence a black pawn on k7 reaches k5 or i5 but
   **not** the empty j5.
3. **Cross-blocking** — if an **enemy** piece stands adjacent in one of the two
   forward directions, the pawn may not advance in the **other** direction
   either — neither the single step **nor the double step**. A **friendly**
   piece blocks only its own direction. The rule works on **adjacent** cells
   only: a white pawn on i2 with an enemy queen on i4 is still free to play i3,
   j3, or the double step to k4.

   That the *double* step in the open direction dies too is settled by the
   article's own pawn diagram, not by inference: White's f2 pawn is cross-blocked
   by the black g3 pawn, and the diagram marks **neither f3 (single, open
   direction) nor f4 (double, open direction)** — while it does mark the k4
   double step of the merely *obstructed* i2 pawn. The article states the rule as
   "if a Pawn is blocked by an enemy piece in one orthogonally forward direction,
   it is also blocked in the other", i.e. the *direction* is shut, not just one
   cell of it.
4. **Capture** — on the two **slanted** forward diagonals always; **and, while
   the pawn stands on its own starting rank, on the fully vertical forward
   diagonal as well**. So a white pawn on f2 can capture a knight on g4, while a
   pawn on c4 does *not* attack d6.
5. **En passant** — after any double step, an enemy pawn that could have
   captured on the cell the double-stepper skipped may capture it there on the
   very next move. (Which cell is skipped depends on which of the two forward
   directions was used.)
6. **Promotion** — on reaching the far rank (rank 8 for White, rank 1 for
   Black) a pawn must become a **queen, rook, bishop or knight**.

## Ending the game

Ordinary chess, in the article's words: "This game follows the rules of Chess in
every respect except those already described above."

* **Checkmate** wins, and it takes precedence over the draw counters: a mating
  move ends the game even if it is also the 100th reversible ply or the third
  occurrence of the position. **Stalemate is a draw** (unlike Gliński's, whose
  tournament rule scores it 3/4–1/4; nothing in Brusky's sources suggests such a
  rule, so orthodox chess applies).
* **Draw** by the **50-move rule** (100 plies with no pawn move and no capture),
  by **threefold repetition** of the position (board + side to move + castling
  rights + en-passant right), and with **bare kings** (mate is then impossible —
  the only "insufficient material" case implemented, see below).
* A hard **ply cap of 20 000** exists purely as a termination backstop and is
  **never outcome-load-bearing**: a pawn advances at most 6 ranks and there are
  10 pawns a side (≤ 120 pawn moves), plus at most 36 capturable pieces, so a
  game contains at most 156 irreversible plies and therefore ends under the
  50-move rule within 156 + 157×100 = **15 856 plies**, always before the cap.
  (Random self-play games actually end after 400–700 plies.)

## Interpretations and source notes

* **Insufficient material.** Only **king vs king** is declared drawn. FIDE's
  dead-position rule (5.2.2) draws a position only when *neither player can
  checkmate by any series of legal moves*, and on this board K+N versus K and
  K+B versus K do **not** qualify: because a corner such as a5 or l8 has only
  **five** king-neighbours instead of twelve, checkmate with a lone minor piece
  is genuinely reachable. An exhaustive sweep of all 84×84×84 king/piece/king
  placements finds mates for every single piece — e.g. **Kc5 + Nb3 vs Ka5#** and
  **Kc5 + Bb4 vs Ka5#**. Auto-drawing K+minor here would therefore be a rule
  *error* (it is one of Jocly's), so those endings are played out and end under
  the 50-move rule if nobody finds the mate.
* **"From its starting space"** (for the double step and the vertical capture)
  is implemented as *standing on its own colour's starting rank* — rank 2 for
  White, rank 7 for Black. Since pawns never move backwards and every cell of
  those ranks starts occupied by a pawn of that colour, this is equivalent to
  "has not yet moved". The colour distinction is unobservable in play (a black
  pawn on rank 2 would double-step or capture vertically onto the non-existent
  rank 0), but it is what the code does.
* **A vertical-diagonal capture is not a double step.** It spans two ranks just
  as a double step does, so it must be recognised by its *direction*: a pawn
  capturing straight up the board creates **no** en-passant right. Likewise the
  captured pawn's cell is *recorded* with the en-passant right rather than
  inferred from the target cell — with two forward directions, both cells
  "behind" an en-passant target can hold an enemy pawn, and only one of them is
  the pawn that just double-stepped.
* **En passant by an unmoved pawn** is generated (a pawn on its starting rank
  captures on three diagonals, and any of them may be an en-passant target), but
  it can never actually arise: an en-passant target always lies on rank 6 for
  White and rank 3 for Black, while a home-rank pawn's capture cells are on
  ranks 3/4 (White) and 6/5 (Black). Jocly's model reaches the same conclusion
  by giving its "initial pawn" type no en-passant-capture flag at all.
* **The article corrects four programmed versions**, and this implementation
  follows the article rather than any of them:
  * *Greenchess* — forbids the unmoved pawn's vertical capture, and lets a pawn
    blocked by an enemy in one direction still move in the other.
  * *Ed Friedlander's Java applet* — no double steps, no castling, and lets
    *moved* pawns capture vertically.
  * *Jocly* — moves the king only **two** cells for queen's-side castling, and
    again ignores the cross-blocking rule.
  * *Ludii* — treats a **friendly** blocker as blocking the other direction too;
    only an enemy piece does that.
* **An erratum in the article's own diagrams (found during QA).** The **Bishop**
  and **Queen** diagrams both show the piece on f4 and both stop the fully
  slanting f4‑g3‑h2 diagonal one cell short of the board's bottom-right corner:
  **i1 is left unmarked** even though it is on the board and on the ray. The
  rules text ("any number of spaces in any diagonal direction until it reaches an
  occupied space") and the *Rook* diagram — which does trace its rays to the edge
  in that same corner — both contradict the omission, as does the mirror-image
  ray f4‑e5‑d6‑c7, which the bishop diagram marks in full. We follow the **text**:
  a bishop or queen on f4 reaches i1. The other three diagrams (King 12 cells,
  Rook 25, Knight 12) are reproduced exactly, and all five are selftest anchors.
* **Cross-blocking is the one rule the historical sources left unclear.** The
  article's author settled it by replaying the game **O. Yefimov – Ya. Brusky**
  printed in Pritchard's *Encyclopedia*: a white pawn on j2 played **j2–l4**
  although Black had a pawn on **j4** (proving that a *non-adjacent* enemy does
  not cross-block), and Black replied **j4×k3 e.p.** That fragment is one of
  this package's selftest anchors.

## Verification

* **All five of the article's piece diagrams** — whose positions are embedded in
  the page's `drawdiagram.php` URLs — are decoded and reproduced **cell for
  cell** by the selftest: Pawn (the 8 `#` cells for White's c4/f2/i2 and the 4
  `!` cells for Black's k7, plus all four negatives the text calls out — c4 does
  not attack the d6 king; k7 cannot reach j5; f2 can reach neither f3 nor f4; i2
  cannot reach i4), King 12, Rook 25, Knight 12, and Bishop 13 / Queen 38 modulo
  the single diagram erratum (i1) documented above. The **board shape** is
  independently re-derived from those diagrams' own off-board markers and comes
  out as exactly our 84-cell set.
* The **geometry** was re-derived from scratch during QA: hexagon polygons were
  built at the renderer's own `x = √3(q + r/2), y = 1.5r`, the 6 orthogonals
  taken as the edge-sharing cells, the 6 diagonals as the nearest cells on the
  rays through the hexagon's 6 vertices, and the 12 knight leaps as "one
  orthogonal step + one *outward* (±30°) diagonal step". All three tables came
  out identical to `game.py`'s — and to the article's own Knight, Rook, Bishop,
  Queen and King diagrams.
* **Differentials.** Against an independent reimplementation of Jocly's ruleset:
  88 821 positions (85 939 from 250 random self-play games plus 2 882 scrambled
  positions) with **0** legal-move-set differences once Jocly's two documented
  bugs are corrected; before that correction, all 43 374 divergences were
  attributable to exactly those two bugs and nothing else (43 320 involved
  pawn cross-blocking, 251 the queen-side castling distance, 197 both). Against
  a *second*,
  from-scratch QA implementation written only from the article text and the
  decoded diagrams — and whose en-passant right is derived from the **move
  history**, never from this engine's own `ep` field — 43 663 positions with 0
  differences, plus an **exhaustive** sweep of all 228 geometrically possible
  en-passant configurations (76 of them carrying a decoy pawn on the *other*
  cell behind the target), comparing the resulting boards, with 0 differences.
* `_attacked()` was checked against a move-generation definition of "attacks"
  over **60 319** (position, cell, side) probes, and serialization round-trips
  over 14 036 states (833 of them carrying an en-passant right): 0 mismatches
  each.
* Frozen **perft** baselines, all seven of them reproduced independently by that
  QA implementation: 61 / 3 583 / 217 683 from the initial position and
  46 / 1 155 / 47 625 / 1 376 153 from the endgame probe.
