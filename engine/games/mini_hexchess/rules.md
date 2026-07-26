# Mini Hexchess

**Dave McCooey, 1997.** Two players, no luck, no hidden information.

On 21 April 1997 Hans Bodlaender put a 37-cell board on the Chess Variant Pages
and asked his readers to invent a game on it as a present for his 37th birthday.
Dave McCooey noticed that 37 is a *hexagonal* number — there is a perfect
hexagonal board of exactly 37 hexes — and shrank his own 1978 hexagonal chess
onto it. ("I couldn't miss the opportunity: the next perfect hex board will be
when you're 61.")

**Be clear about what this is:** it is **McCooey's Hexagonal Chess** on a much
smaller board — 37 of the full game's 91 hexes, side 4 instead of side 6 — with a
reduced army and three rule changes. Every piece moves
exactly as it does in the full-size game. Its interest is that it is a genuinely
different *game* to play — 37 hexes, no queen, no double step — not a new set of
movement rules.

## Board

A regular hexagon of **37 hexes** (side 4). Seven **vertical files** `a`–`g` of
lengths 4, 5, 6, 7, 6, 5, 4; ranks `1`–`7` bend 60° at the central `d` file, so
`d1` is White's near corner, `d4` the centre and `d7` Black's corner. Ranks are
numbered from White's corner throughout (so Black's men start on ranks 5–7).

Cells come in the usual **three hex colours**; the centre hex `d4` is the
lightest.

## Setup

Each side has a **king, rook, bishop, knight and five pawns — no queen.**

| | |
|---|---|
| White | **N** c1, **B** d1, **R** e1, **P** b1, **P** f1, **P** c2, **K** d2, **P** e2, **P** d3 |
| Black | **R** c6, **B** d7, **N** e6, **P** b5, **P** f5, **P** c5, **K** d6, **P** e5, **P** d5 |

Black's array is White's exact **180° rotation** about the centre hex.

## The pieces

Exactly as in McCooey's (and Gliński's) hexagonal chess:

- **Rook** — any distance along one of the 6 *edge* directions.
- **Bishop** — any distance along one of the 6 *diagonal* (vertex) directions;
  colourbound.
- **King** — one cell in any of those 12 directions.
- **Knight** — the hex knight: two cells orthogonally, then one at 60°;
  12 targets, jumping over anything between.
- **Queen** — rook + bishop. It is not in the array **and can never appear**,
  because a pawn may not promote to one.

## The pawn — and the three changes from McCooey's game

- A pawn **moves** one vacant cell **straight forward** along its file.
- It **captures** one cell along its two **forward diagonals** (bishop-wise) —
  McCooey's rule, and the orthodox-chess-like one. It cannot capture the piece
  directly in front of it, and that piece blocks it.
- **1. There is NO initial double step** — and therefore **no en passant** at
  all.
- **2. Promotion is to ROOK, BISHOP or KNIGHT — never a queen.** It is forced.
- **3. All SEVEN hexes on the opponent's side of the board are promotion
  hexes**: `a4 b5 c6 d7 e6 f5 g4` for White and `a1 b1 c1 d1 e1 f1 g1` for
  Black — the two far edges, which meet at the far corner.

There is **no castling**, as in McCooey's and Gliński's games.

## Ending the game

- **Checkmate** wins — and it **ends the game at once**, outranking the draw
  counters below: a mate delivered on the 100th reversible ply is a win, not a
  50-move draw. ("Otherwise the rules of chess apply", per Green Chess.)
- **Stalemate is a draw** (½–½) — McCooey's rule, and explicitly *not*
  Gliński's 3/4–1/4 scoring.
- **Draws** also by the **50-move rule** (100 plies with no pawn move and no
  capture) and by **threefold repetition**. With no en-passant and no castling
  state, board + side to move *is* the whole position.
- There is no "insufficient material" auto-draw.

## Notation

Cells are `file letter + rank`, e.g. `d1`. Moves are written `Nc1-d4` /
`Nc1xd4`, pawn moves without the letter (`d3-d4`), and `=R` / `=B` / `=N` for a
promotion.

## Implementation notes and interpretations

Sources: **chessvariants.com/hexagonal.dir/minihex.html** (Hans Bodlaender's
write-up of McCooey's own email — the primary rules text, with the setup
diagram `d.37/hexa37.gif`); the **Game Courier preset FEN**
`1prb/2pkn/3ppp/7/-PPP3/--NKP2/---BRP1`; **greenchess.net**
(`rules.php?v=mini-hex`), which implements the game; and **Ludii**'s
`Mini Hexchess.lud` (Jay M. Coskey, 2020), a fourth independent implementation.

1. **The setup is quadruple-sourced and self-checking.** The Game Courier FEN
   was decoded independently (7 columns; `-` marks a cell that is not on the
   board; `(q,r) = (col-4, row-col)` — and under that mapping every `-` falls
   exactly on an off-board cell, which is what pins it) and agrees with the
   chessvariants setup image **cell for cell**; the resulting position is
   exactly 180°-rotationally symmetric, a consistency check no single source
   could give. QA added two more: the 322×341 setup GIF was decoded from its own
   **pixels** (37 hex centres sampled, every occupied cell's glyph identified),
   and **Ludii**'s `(place …)` list was decoded after pinning Ludii's hex
   coordinate convention by re-deriving Gliński's known array from Ludii's
   *Gliński Chess*. All four sources agree on all 18 men. Note the trap the
   symmetry check cannot catch: an off-by-one in the FEN mapping would still
   yield a 180°-symmetric position, so the pixel read is what actually settles
   it. The selftest re-derives the array from the FEN string at run time.
2. **"No double step, hence no en passant"** is quoted verbatim from
   chessvariants and confirmed by Green Chess ("They cannot make a
   double-move"). The state object carries **no en-passant field at all**, and
   the selftest proves by exhaustion over all 37 cells that no pawn anywhere
   ever has more than its single forward step.
3. **Promotion to R/B/N only, on all seven far hexes** is likewise verbatim
   from chessvariants ("A pawn can promote to a rook, bishop, or knight, but
   not to a queen. All seven hexes on the opponents side of the board are
   promotion hexes") and corroborated by Green Chess ("They cannot promote to
   queen, only to rook, bishop or knight … on the opposite two edges").
4. **Everything else is McCooey's**, including *stalemate is a draw*, *no
   castling*, and the pawn's diagonal capture. Green Chess's Mini Hexchess page
   states "otherwise the rules of chess apply … there is no castling", and
   flags Gliński's 3/4–1/4 stalemate only on its Gliński page.
5. **Board orientation.** The files are drawn vertical (the chessvariants
   diagram shows seven vertical columns of 4/5/6/7/6/5/4 hexes, each hex with a
   horizontal top edge), so the board renders **flat-top**, exactly like
   `mccooey_chess` and `glinski_chess`. Wikipedia classifies the whole family
   the same way — "vertically oriented (Gliński's, Shafran's, McCooey's)" — and
   notes the consequence this game relies on: "when the sides of hexagonal cells
   face the players, pawns typically have one straightforward move direction".
   The three background shades are the diagram's own: its cell colours are
   exactly the classes of `(q−r) mod 3`, and its centre hex is the lightest.
6. **Checkmate outranks the draw counters.** Chess ends the instant the king is
   mated, so a mate delivered on the 100th reversible ply is scored a win, not a
   "50-move rule" draw. Random play never lands on that boundary (0 of 3,000
   random games), so only a constructed position exposes it; the selftest ships
   one. Stalemate and the counters are unaffected — every genuine tie is an
   honest 0–0.
7. **The hard ply cap is a pure termination backstop and can never fire.** At
   most 16 captures and 60 pawn moves (10 pawns; every pawn move drops a pawn
   one or two of the six ranks it must cross) = 76 irreversible plies, with at
   most 99 reversible plies in each of the 77 gaps around them, so no game can
   exceed **7,699** plies — far under the cap of 25,000. Random games average
   about 210 plies. The selftest asserts the bound and that no random game is
   ever decided by the cap.

**Correctness anchors.** Perft from the initial position is
**9 / 71 / 681 / 7,534 / 92,914** for depths 1–5, **1,220,292** at depth 6 and
**17,450,532** at depth 7 (all seven independently recomputed by QA); depth 1 is
also listed move by move in the selftest. The move generator was checked in
lockstep against three separate oracles, **0 mismatches** every time:

- **`mccooey_chess`'s own move generator**, retargeted at the 37-hex board with
  the double step switched off — so every rule the two games share is compared
  directly against the already-anchored full-size implementation. Reproduced by
  QA over **51,747 positions** from 250 random games (9,798 promotion and 43,456
  capture moves).
- A **from-scratch reimplementation** whose directions are *discovered by
  measuring distances between hex centres* in pixel space, and whose seven
  promotion hexes are characterised as "the cells a forward move would leave the
  board from": **33,812 positions** from 250 random games.
- QA's own independent **cube-coordinate** generator, which derives the rook
  directions as the permutations of (1,−1,0), the bishop's as those of
  (2,−1,−1), the knight's as *the distance-3 ring minus the rook rays*, and the
  pawn's captures as the two bishop directions with the largest Euclidean
  component along the file: **86,245 positions** from 400 random games plus
  **11,000** random sparse positions.

Also fuzzed: **669,696** move strings against `apply_move` (every from→to pair
with every promotion suffix on 48 positions, plus random garbage) — it accepts
exactly `legal_moves` and nothing else; **180,144** attack probes confirming
`_attacked` agrees with capturability cell by cell; and 3,000 positions
confirming the 180°-rotation-plus-colour-swap symmetry of the whole ruleset.
The selftest itself was mutation-tested against **46** distinct injected bugs
(gutted captures, a smuggled double step, queen promotion, a shrunken promotion
zone, Gliński stalemate scoring, setup skews that stay 180°-symmetric, a
corrupted `render()`, dropped serialization fields, …): **46/46 caught**.

**Official source:** [Mini Hexchess on
chessvariants.com](https://www.chessvariants.com/hexagonal.dir/minihex.html)
