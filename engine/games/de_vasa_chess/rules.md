# De Vasa's Hexagonal Chess

**Helge E. de Vasa, 1953** — first published in Joseph Boyer's *Nouveaux Jeux
d'Échecs Non-orthodoxes* (Paris, 1954). Two players, no luck, no hidden
information.

Almost every hexagonal chess (Gliński, McCooey, Shafran, Starchess) draws its
board with **vertical files**, so a pawn has one straight-ahead move. De Vasa
turned the hexes 90°: his board has **orderly horizontal ranks**, and it is a
**rhombus** rather than a hexagon. The consequences run right through the game —
a pawn now has *two* forward moves and captures only *sideways*, and castling
comes back (it does not exist in Gliński's or McCooey's games). The first-rank
array he introduced was borrowed by Brusky in 1966.

## Board

A parallelogram of hexes, **9 files `a`–`i` × 9 ranks `1`–`9` = 81 cells**.
Ranks run horizontally; the files lean up and to the left, so `a1` is at the
bottom left of the bottom row and `a9` at the far left of the top row.

The cells come in the usual **three hex colours** — the 1954 sheet counts them:
"81 hexagones, dont 27 blancs, 27 noirs, 27 bruns". The three bishops of each
side start on the three colours, one each, and each bishop stays on its own
colour forever.

White's home rank is **1**, Black's is **9**. "Forward" for White is toward
rank 9.

## Setup

| | |
|---|---|
| White, rank 1 | **R** a1, **N** b1, **B** c1, **Q** d1, **B** e1, **K** f1, **B** g1, **N** h1, **R** i1 |
| White pawns | a3 b3 c3 d3 e3 f3 g3 h3 i3 |
| Black, rank 9 | **R** a9, **N** b9, **B** c9, **K** d9, **B** e9, **Q** f9, **B** g9, **N** h9, **R** i9 |
| Black pawns | a7 b7 c7 d7 e7 f7 g7 h7 i7 |

Black's array is White's rotated **180°** about the centre of the board — *not*
mirrored. So the **kings stand on opposite wings**: White's king is on `f1`,
Black's on `d9`, and each king faces the enemy *queen*. This asymmetry is
deliberate and is one of the game's signatures — Pritchard's encyclopedia
confirms it sideways, describing a *different* game (Strozewski's) as having
the "array as in de Vasa's game, **with Ks and Qs facing each other**", i.e.
unlike de Vasa's.

## The pieces

All non-pawn moves are exactly Gliński's.

- **Rook** — any distance along one of the 6 *edge* (orthogonal) directions.
- **Bishop** — any distance along one of the 6 *diagonal* (vertex) directions.
  A diagonal step lands on a cell of the bishop's own colour, two edge-steps
  away; bishops are colourbound.
- **Queen** — rook + bishop (12 directions).
- **King** — one cell in any of those 12 directions.
- **Knight** — the hex knight: two cells orthogonally, then one more at 60°.
  12 target cells, jumping over anything in between.

## The pawn

Because the ranks are horizontal there is **no cell straight ahead** — the two
cells forward are up-left and up-right. So:

- A pawn **moves** to *either* of the **two forward adjacent cells** (same file
  one rank up, or next file one rank up).
- On its **first move** (i.e. while it still stands on its own third rank) it
  may instead advance **two cells in the same direction**, over a vacant cell.
  An unmoved pawn therefore has **four** move options.
- A pawn **captures** only on the **two side diagonals** — one rank forward,
  one file back, and one rank forward, two files on. Both are diagonal
  (same-colour) cells. It can **never** capture on a cell it can move to, and
  it can **never** capture on the "straight ahead" diagonal (that cell is *two*
  ranks away).
- **En passant** applies: a pawn that double-steps across a cell attacked by an
  enemy pawn may be captured on that crossed cell by that pawn, on the
  immediately following move only.
- **Promotion**: a pawn reaching the opponent's back rank (rank 9 for White,
  rank 1 for Black) must promote to **Q, R, B or N**, freely chosen.

*Worked example (Wikipedia's pawn diagram):* the unmoved pawn on `b3` may go to
`b4`, `b5`, `c4` or `d5` and captures on `a4` or `d4`. The pawn on `g5` has
moved, so it has only `g6` and `h6`, and captures on `f6` or `i6`. After
`1… f7-f5`, White may reply `2. g5xf6 e.p.`

## Castling

Both kings sit **three** cells from one rook and **five** from the other, so
there are exactly two castlings per side:

| | king slides | rook slides | White | Black |
|---|---|---|---|---|
| **Short (0-0)** — toward the near rook | 2 cells | 2 cells | K f1→h1, R i1→g1 | K d9→b9, R a9→c9 |
| **Long (0-0-0)** — toward the far rook | 3 cells | 3 cells | K f1→c1, R a1→d1 | K d9→g9, R i9→f9 |

The rook always ends on the cell next to the king, on the side the king came
from. All the ordinary chess restrictions apply: king and rook must both be
unmoved, every cell between them must be vacant, and the king may not start
from, pass over, or land on an attacked cell.

## Ending the game

- **Checkmate** wins.
- **Stalemate is a draw** (½–½) — *not* Gliński's 3/4–1/4 scoring, which
  Pritchard & Beasley say explicitly "has not been followed elsewhere".
- **Draws** also by the **50-move rule** (100 plies with no pawn move and no
  capture) and by **threefold repetition** (same position, side to move,
  en-passant right and castling rights).
- There is no "insufficient material" auto-draw; bare-king endings run out
  under the 50-move rule.

## Notation

Cells are `file letter + rank`, e.g. `f1`. Moves are written
`Nb1-c4` / `Nb1xc4`, pawn moves without the letter (`b3-c4`), `e.p.` for an
en-passant capture, `=Q` for a promotion, and `0-0` / `0-0-0` for castling.

## Implementation notes and interpretations

### Sources

- **The primary rules sheet for this (revised) version.** D. B. Pritchard's
  files contained an unprovenanced single-sheet French typescript,
  *"Modification au projet de jeu hexagonal De Vasa, pages 81 et 82"* — i.e. a
  modification to pages 81–82 of Boyer's *Nouveaux Jeux d'Échecs
  Non-orthodoxes* — printed in full by John Beasley in *Variant Chess* **64**
  (January 2010), pp. 161–62. It is the complete delta from the original game
  to the 81-cell one, and it is what this package implements: *"Addition d'une
  9ème ligne d'hexagones, soit en tout 81 hexagones, dont 27 blancs, 27 noirs,
  27 bruns … des Figures noires (R, D, T, F, C), les Pions noirs restant sans
  changement sur la 7ème ligne. Disposition des Pions blancs sur la 3ème ligne,
  les Figures blanches … sur la 1ère ligne. **Suppression de la faculté des
  Pions de prendre à un pas de Fou en avant**; pour le reste, ils conserveront
  **leurs deux avancements et leurs deux prises à droite et à gauche**, ainsi
  que la faculté d'avancer de 2 cases au premier coup, de même que celle de la
  prise en passant … Les deux roques, p.ex. pour les Blancs … après le **grand
  roque**, sera: **Rc1, Td1** … après le **petit roque**, sera: **Rh1, Tg1**."*
- **D. B. Pritchard & J. D. Beasley, *The Classified Encyclopedia of Chess
  Variants* (2007)** — the De Vasa entry, §22.4 pp. 209–10, and the chapter
  preamble, p. 203.
- The Wikipedia article **"Hexagonal chess"**, § *De Vasa's hexagonal chess*,
  with its **two diagrams** (starting position; pawn moves + a castled
  position).
- **greenchess.net** (`rules.php?v=de-vasa`), which implements the game, with
  its pawn and castling diagrams.
- **quadibloc** ("Hexagonal Chess II") — but it documents the *original* game,
  not this one (see below). **Wikibooks**, *Chess Variants/Hexagonal Chess*.
  The **Jocly** reference model, read only as an oracle for the starting array,
  the pawn graphs and the promotion table.

### The original (72-cell) game, and this revised one

De Vasa's 1953 game as Boyer printed it was a **72-cell** board — nine files by
**eight** ranks, pieces on ranks 1 and 8, pawns on ranks 2 and 7 — and its pawn
captured on **three** forward bishop steps. Pritchard & Beasley, p. 209:
*"72-cell diamond-shaped board, extra B and P each side … Pawns capture ahead
as a bishop (normally three alternatives), greatly enhancing their value
vis-a-vis the pieces. A revised form of the game, probably in response to
criticism of the dominant pawns, has the board extended by an extra nine-cell
rank with the array pawns on the 3rd and 7th ranks respectively. The pawn
capture is limited to the two hexes on either side a bishop's step in advance.
Castling permitted: K moves three (0-0-0) or two (0-0) hexes towards the R, the
R moving adjacent to K on inside."*

**This package implements the revised 81-cell game** — the one Wikipedia
documents ("in the revised form of the game"), the one Green Chess and Jocly
implement, and the one the French modification sheet specifies.

### Interpretations

1. **Castling is primary-sourced.** The modification sheet gives the finished
   positions outright — after the *grand roque* **Rc1, Td1**; after the *petit
   roque* **Rh1, Tg1** (R = *roi*, T = *tour*) — and Pritchard & Beasley state
   the rule: "K moves three (0-0-0) or two (0-0) hexes towards the R, the R
   moving adjacent to K on inside". Wikipedia's text ("two cells when castling
   short; three when castling long"), Green Chess ("on kingside both the king
   and the rook move two fields, on queenside both pieces move three") and
   quadibloc ("two spaces Kingside, three Queenside") all agree; Wikipedia's
   own diagram *shows the finished position* (White castled short **Kh1/Rg1**,
   Black castled long **Kg9/Rf9**), and Green Chess's three castling diagrams
   independently show the same two White positions (**Kh1/Rg1/Ra1** and
   **Kc1/Rd1/Ri1**). Because the kings start on opposite wings, White's short
   side is the `i` wing and Black's is the `a` wing — Green Chess's
   "kingside"/"queenside" wording agrees, since Black's king's flank *is* the
   `a` wing here. The one dissenting source is **Wikibooks**, which says only
   that castling "works exactly the same as in Shafran's variant"; Shafran's
   formulation (long = the king moves next to the rook and the rook jumps over
   it) happens to reproduce this game's *short* castling for the near rook, but
   for the far rook it would give Kb1/Rc1 rather than the Kc1/Rd1 that the 1954
   sheet, Wikipedia and Green Chess all give. The explicit sources win.
2. **The pawn captures on TWO diagonals, not three.** The modification sheet
   settles it: the revised game *suppresses* the forward bishop-step capture
   and keeps "leurs deux avancements et leurs deux prises à droite et à
   gauche"; Pritchard & Beasley say the same ("limited to the two hexes on
   either side a bishop's step in advance"). Four further sources agree —
   Wikipedia's prose ("captures diagonally forward *to the sides*"); its pawn
   diagram, which marks four consecutive cells one rank forward in the order
   **red, green, green, red** (verified by colour-segmenting the image: the b3
   pawn's marks fall exactly on a4/b4/c4/d4 plus b5 and d5, the g5 pawn's on
   f6/g6/h6/i6); Green Chess's pawn diagram, the same **cross, dot, dot,
   cross** row; and Jocly, which ships a *dedicated* `cbDVInitialPawnGraph`
   that is its Brusky graph with exactly the straight-ahead diagonal deleted
   (`[0,-s,-s]`, the sum of the two forward moves) and uses a two-capture graph
   for pawns that have already moved. Green Chess also flags its *Brusky* pawn
   as "simplified" and flags nothing on its De Vasa page.
   The one dissenting source is **quadibloc**, whose diagram gives the pawn
   three forward bishop captures — and whose De Vasa board is drawn with
   **eight ranks** and pawns on ranks 2 and 7 (measured off the GIF: eight hex
   rows, 72 cells). That is precisely the *original* game, three-way pawn
   capture included. Quadibloc is right about the game it is describing; it
   simply is not describing this one.
3. **Stalemate is a draw** — stated, not merely assumed. The encyclopedia's
   chapter preamble (p. 203) says exactly how far the "as Gliński"
   cross-reference reaches: *"The rules of Gliński's game are therefore given
   in full, those of other variants by reference to Gliński **at least as
   regards the moves of the men (Gliński's treatment of stalemate has not been
   followed elsewhere)**."* De Vasa's entry sits inside that chapter, so the
   3/4–1/4 rule is explicitly *not* inherited — which is also why Wikipedia's
   sentence is carefully scoped to "rules for piece **movement**". The primary
   modification sheet, which specifies the board, the array, the pawn-capture
   restriction, the double step, en passant and both castlings in detail, says
   nothing about stalemate; neither does Jelliss's *Variant Chess* 1(8) survey.
   Green Chess says "otherwise the rules of chess apply", and its Gliński page
   shows that it *knows* the 3/4–1/4 rule and flags it as a deviation there and
   nowhere else. (Gliński's rule is in any case a **match-play scoring**
   convention, not a rule about terminal positions.) Stalemate is therefore an
   honest draw here — `winner = None`, `[0, 0]` — and it is not a corner case:
   19 of 600 random games ended in stalemate.
   The one dissenting source, Jocly's De Vasa *rules blurb* ("Stalemate is not
   a draw but is counted less than checkmate"), is refuted. It is a
   near-verbatim copy of Jocly's own **Gliński** blurb, and Jocly's De Vasa
   *model file* is demonstrably `brusky-model.js` with the geometry,
   `posNames`, promotion table and pawn graphs swapped but the `castle:` block
   **left un-updated**: its four castle keys are still Brusky board indices, so
   on De Vasa geometry the king cell they name is `e2` (the De Vasa king is
   index 113 = `f1`) and one rook index is not a cell of the board at all. That
   table can never fire. Jocly is a fine oracle for this game's array, pawn
   graphs and promotion cells, and no oracle at all for its castling or its
   prose.
4. **Promotion is on the opponent's back rank**, not "the end of a file" as in
   the hexagon-board variants. Jocly's promotion table lists exactly `a9…i9`
   for White and `a1…i1` for Black, and Green Chess says "on the opposite edge
   of the board" (singular — a rhombus has one far rank, unlike a hexagon's two
   far edges). Because both of a pawn's move directions gain a rank, and at
   least one of them always stays on the board, a pawn can never become
   permanently stuck short of promotion.
5. **"First move" = "standing on its own third rank."** A pawn's every move
   gains a rank, and no pawn of a colour ever occupies a cell behind its home
   rank, so the two formulations are equivalent.
6. **Board orientation.** De Vasa's hexes have a **vertex** at the top (checked
   against the Wikipedia diagram at pixel level, and implied by Wikipedia's own
   rule of thumb: "if a variant's gameboard has cell vertices facing the
   players, pawns typically have two oblique-forward move directions"). That is
   the renderer's *pointy-top* default, so this game deliberately does **not**
   set `orientation: "flat"` — that is for the vertical-file hex chesses
   (Gliński/McCooey/Shafran/Starchess), and it would draw this board 30° off
   every published diagram. Which of the three colour classes `(c-r) mod 3` is
   light, which mid and which dark *was* read off the Wikipedia diagram's
   pixels (class 0 light, 1 mid, 2 dark); the three hex codes themselves are
   the platform's shared hex-chess palette.
7. **The hard ply cap is a pure termination backstop and can never fire.** At
   most 34 captures and 108 pawn moves (18 pawns; every pawn move gains one or
   two of the six ranks it must cross) = 142 irreversible plies, with at most
   99 reversible plies in each of the 143 gaps around them, so no game can
   exceed **14,299** plies — well under the cap of 25,000. Measured over 600
   random games: mean ≈ 480 plies, longest **916**, most irreversible plies in
   any one game **105** (of the 142 the bound allows), and the cap fired
   **zero** times (those games ended 448× by the 50-move rule, 114× by
   checkmate, 19× by threefold repetition and 19× by stalemate). The selftest
   asserts both the analytic bound and that no random game is decided by the
   cap.

**Correctness anchors.** Perft from the initial position is **55 / 2,992 /
168,335 / 9,343,938** for depths 1–4; all four were reproduced by a second,
independently written generator whose direction sets are *discovered by
measuring distances between hex centres* (no delta table, no cube
permutations) and whose castling geometry is transcribed in cell names off the
Wikipedia and Green Chess diagrams. Depth 1 is also derived by hand in the
selftest. Against that generator the package was compared move-set for
move-set over **14,167 positions from random games** plus **4,272
castling-rich** and **6,688 post-double-step** constructed positions
(6,152 castling moves and every legal en-passant capture exercised) —
**0 mismatches** — and its attack sets agree over all 936 (piece, colour,
cell) combinations on an empty board and 8,000 randomly occupied ones.

**Official source:** [Wikipedia — Hexagonal chess § De Vasa's hexagonal
chess](https://en.wikipedia.org/wiki/Hexagonal_chess#De_Vasa's_hexagonal_chess)
