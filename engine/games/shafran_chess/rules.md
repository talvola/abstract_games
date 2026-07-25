# Shafran's Hexagonal Chess

Invented by **Isaak Grigorevich Shafran**, a Soviet geologist, in **1939**;
registered in **1956** and demonstrated at the Chess Olympiad in **Leipzig,
1960**. It is the third of the three historic hexagonal chesses, after
Gliński's (1936) and alongside McCooey's (1978) — and the only one of them with
**castling**.

Its board has only **70 cells**, much closer to chess's 64 squares than
Gliński's 91.

## The board

An irregular hexagon: **four sides of 5 cells and two of 6**.

- Nine **vertical files** `a`-`i`, left to right.
- Ten **obliquely descending ranks** `1`-`10`. A rank runs from the upper left
  down to the lower right, so `a1` is the *highest* cell of rank 1 and `e1` —
  the white king's cell — is the **lowest cell on the whole board**. Continuing
  right and up from `e1` along the board's edge gives `f2`, `g3`, `h4`, `i5`,
  each on its own rank.
- File lengths: a 6, b 7, c 8, d 9, e 10, f 9, g 8, h 7, i 6. Files `f`-`i`
  begin at ranks 2, 3, 4, 5 respectively; files `a`-`d` end at ranks 6, 7, 8, 9.
- The cells have **three colours**, as on every hex-chess board.

Internally a cell is the axial pair `q,r` with `q = file index - 4` and
`r = 5 - rank`; the board is exactly `-4 <= q <= 4`, `-5 <= r <= 4`,
`-5 <= q+r <= 4`.

## Setup

Each side has **K, Q, 2 R, 3 B, 2 N and 9 P** — Gliński's army.

- **White**: R a1, N b1, B c1, Q d1, K e1, B f2, N g3, B h4, R i5;
  pawns a2 b2 c2 d2 e2 f3 g4 h5 i6.
- **Black** is the exact 180° rotation: R i10, N h10, B g10, Q f10, K e10,
  B d9, N c8, B b7, R a6; pawns i9 h9 g9 f9 e9 d8 c7 b6 a5.

Each player calls the left-hand side of the board (as he sees it) his *queen's
flank* and the right-hand side his *bishops' flank*. They do **not** correlate:
White's queen's flank (files a-d) is Black's bishops' flank.

## Piece movement

Apart from the pawn and castling, everything moves as in Gliński's / McCooey's
hexagonal chess.

- **Rook** — any distance through cell **edges** (6 directions).
- **Bishop** — any distance through cell **vertices** (6 directions). Bishops
  are colourbound; the three bishops start on the three colours.
- **Queen** — rook or bishop, 12 directions.
- **King** — one cell in any of the 12 directions.
- **Knight** — leaps to any cell of its **third ring that the queen cannot
  reach** (12 targets): one orthogonal step followed by one *outward* diagonal
  step, jumping over anything in between.

## The pawn

- Moves **one vacant cell straight forward** (up its own file).
- **Captures one cell diagonally forward** — i.e. along the two *bishop*
  directions that lean forward. This is McCooey's capture, **not** Gliński's
  forward-orthogonal one. From e6 a white pawn captures on d7 and f8; from c4
  it captures on b5 and d6.
- **First move**: a pawn may advance **as far as it can without leaving its own
  half of its file**, over vacant cells only and without leaping:
  **3 cells on the d, e and f files; 2 on b, c, g and h; 1 on a and i.**
  (Odd-length files have an exactly midway cell, which either side may reach.)
- ***En passant*: every cell CROSSED by such a multi-step move is capturable.**
  An enemy pawn that could have captured the mover had it stopped short may
  capture it by moving diagonally forward onto that crossed cell, on the
  immediately following move only. A three-cell move therefore offers **two**
  en-passant squares, and two different enemy pawns may each have one.
- **Promotion** to Q, R, B or N (forced) on reaching the **far end of any
  file** — 9 cells per side: a6 b7 c8 d9 e10 f10 g10 h10 i10 for White, and
  a1 b1 c1 d1 e1 f2 g3 h4 i5 for Black.

## Castling

Unique among the classical hexagonal chesses. The king may castle toward
**either** rook, in **either of two lengths**:

- **Long (`0-0-0`)** — the king moves **three** cells toward the rook, landing
  next to it, and the rook jumps over him to the far side.
- **Short (`0-0`)** — "the opposite procedure" (Derzhanski): the **rook** moves
  to the cell next to the king and the **king** jumps over *it*, so the king
  ends **two** cells from home (one less than long castling) and the rook one.

The four white and four black castlings are therefore: White toward a1 —
`Q-0-0-0` **K e1→b1, R a1→c1** and `Q-0-0` **K e1→c1, R a1→d1**; White toward
i5 — `B-0-0-0` **K e1→h4, R i5→g3** and `B-0-0` **K e1→g3, R i5→f2**; Black
toward i10 — `Q-0-0-0` **K e10→h10, R i10→g10** and `Q-0-0` **K e10→g10,
R i10→f10**; Black toward a6 — `B-0-0-0` **K e10→b7, R a6→c8** and `B-0-0`
**K e10→c8, R a6→d9** (this last is the one Wikipedia's diagram shows).

| | long | short |
|---|---|---|
| White toward a1 | K e1→b1, R a1→c1 | K e1→c1, R a1→d1 |
| White toward i5 | K e1→h4, R i5→g3 | K e1→g3, R i5→f2 |
| Black toward a6 | K e10→b7, R a6→c8 | K e10→c8, R a6→d9 |
| Black toward i10 | K e10→h10, R i10→g10 | K e10→g10, R i10→f10 |

The ordinary chess restrictions apply, in Derzhanski's words: "neither the King
nor the Rook may have moved and the King may not start from, go through or
finish on a checked field". The **three** cells between king and rook must be
empty in both lengths (the rook travels over all of them).

Shafran's notation prefixes the flank: `Q-0-0-0` / `Q-0-0` for castling on the
player's **queen's** flank, `B-0-0-0` / `B-0-0` on his **bishops'** flank. The
move log uses those names.

## Ending the game

- **Checkmate** wins. **Stalemate is a DRAW** — Shafran keeps the orthodox
  result, unlike Gliński's 3/4-1/4 rule.
- **Draws**: the 50-move rule (100 plies with no pawn move and no capture) and
  **threefold repetition** (same position, side to move, en-passant targets and
  castling rights).
- There is deliberately **no "insufficient material" auto-draw**: no source
  states one for this game, hex-board mating material differs from chess's, and
  bare-king endings simply end by the 50-move rule.
- A hard cap of 20,000 plies exists purely as an engine safety net and can
  **never** decide a game. Only a capture or a pawn move resets the 50-move
  clock, and there can be at most 34 captures (36 men, two kings) plus at most
  144 pawn moves (18 pawns; every pawn move gains at least one rank, and no
  pawn can gain more than 8 — the earliest start rank is 2 and the latest
  promotion rank is 10), i.e. **at most 178 irreversible plies**. At most 99
  reversible plies may pass in each of the 179 gaps around them, so the 50-move
  rule always fires by ply 178 + 179×99 = **17,899** at the very latest. In
  practice random play ends far sooner: over 240 random games the longest was
  723 plies.

## Notation used here

Moves are entered as cell paths; the move log shows long algebraic in
Shafran's own coordinates (`Nb1-c4`, `e2-e5`, `Bc1xg9`, `d5xe7 e.p.`,
`b6-b7=Q`, `Q-0-0-0`).

## Sources, and where they disagree

1. **Ivan A. Derzhanski, "Hexagonal Chess by I G Shafran"**
   (`math.bas.bg/~iad/tyalie/shegra/`, 1998–2001; now only on the Wayback
   Machine, and linked as the Shafran reference from Wikipedia). This is the
   closest thing to a primary source in English: it is written up from the
   description published in the Soviet magazine *Junyj texnik*, and it carries
   that report's **sample games, endgame studies and problems**. It states the
   full array cell by cell, the castling procedure, en passant on *either*
   crossed cell, and "stalemate is draw".
2. **Wikipedia, "Hexagonal chess" § Shafran's hexagonal chess** (citing
   Pritchard 2007), with its setup and castling/en-passant diagrams. Its text
   follows Derzhanski closely (the d8-pawn study is the same one).
3. **Fergus Duniho, "Shafran's Hexagonal Chess", chessvariants.com (2023)** —
   a later summary drawing on Pritchard's *Encyclopedia of Chess Variants*,
   Jocly and Wikipedia; it adds a second worked en-passant diagram.
4. The **Jocly** reference implementation of the game.

Interpretations and corrections this package had to make:

- **"The Bishop is on f1" (Duniho) is a typo for f2.** `f1` is not a cell of
  this board at all — the f-file begins at f2 — and only f2 gives the three
  bishops the three different colours that the same page requires (a bishop on
  f1 would share c1's colour). Derzhanski lists the array cell by cell and
  writes "**Bf2** (red)"; Wikipedia's diagram and Jocly's array agree.
- **Pawn captures are diagonal (bishop-wise), not Gliński's orthogonal.**
  Wikipedia's body text says "all pieces except pawns and kings move exactly as
  in Gliński's"; Duniho shows this to be a misreading of Pritchard, whose own
  words are "Pawns capture diagonally ahead on next hex of own colour".
  Derzhanski is explicit: "Pawns capture diagonally forwards, towards 1 or 11
  o'clock (**not** on the same rank as they do in Gliński's game)". Wikipedia's
  parenthetical gloss "(one rank and one file)" is inaccurate for one of the two
  directions — because the ranks are oblique, the two forward diagonals are
  "+1 rank, −1 file" (11 o'clock) and "+2 ranks, +1 file" (1 o'clock) — as its
  own example `cxd6` (c4 to d6) demonstrates.
- **Short castling is directly sourced, even though Duniho's page omits it.**
  Derzhanski and Wikipedia both describe long *and* short with Shafran's own
  `Q-`/`B-` + `0-0-0`/`0-0` notation; Wikipedia's diagram shows the two black
  results (Kh10 long, Kc8 short), which fixes the rook squares as well; Jocly
  implements both, with exactly these eight destinations. Duniho's 2023 summary
  describes only the three-cell form, but himself notes that the Java applet
  consistently offers two or three cells and that this "might have been
  programmed intentionally". So this is not an override of a source, only of a
  later source's omission.
- **The `.gcsettings` Game Courier preset for this game has the wrong starting
  array** and was ignored: its back rank runs `R B N B K` with the queen pushed
  out to `f2`/`d9` (i.e. `R B N B K Q B N R` along each player's edge instead of
  `R N B Q K B N B R`), and it mirrors Black's array rather than rotating it.
  Derzhanski, Wikipedia, Duniho and Jocly all agree against it.
- **"On its first move" is implemented as "standing on its own starting cell".**
  These are provably equivalent here: every pawn starting cell can only be
  entered from that side's back rank, where a pawn of that colour can never be
  (pawns never move backwards and none starts there). The selftest checks this
  by exhaustion.
- Duniho notes that the Java applet's promotion was limited to queens as a
  stopgap; promotion here is to Q/R/B/N as in chess, matching Jocly.

## Verification

The package's `selftest.py` re-checks the board, array, pawn table, the
Wikipedia en-passant study (`1...d7 2.exd7`, `1...d6 2.exd7 e.p. / 2.cxd6`,
`1...d5` capturable by either pawn), Duniho's own en-passant diagram
(`d5xe7 e.p.`, `f7xe8 e.p.`, and the f-pawn's ordinary `f7xg9`), both castling
positions from Wikipedia's diagram, promotion, stalemate scoring and the frozen
perft series **42 / 1,706 / 75,494** for depths 1-3.

It also replays the material Derzhanski reprints from the *Junyj texnik*
report, which is the strongest end-to-end anchor available for this game:

- **Sample game #1 ("Kindermatt")** — `1.Nb1-c4 Nc8-d6 2.Qd1-e3 b6-b5?? 3.Nc4-d7#`,
  the knight forking king, queen and bishops' rook while the e9 pawn is pinned.
- **Sample game #4**, all 44 half-moves, including the real `6. Q-0-0-0`
  (Ke1→b1, Ra1→c1 — confirmed later in the score by `15.Rc1:c2` and `20...Kb1-a1`)
  and ending in `22...Qg4-a4#`.
- **Sample game #3**, all 59 half-moves.
- **E. A. Baum's eight checkmating studies** (Q; K+Q; K+R; K+2N; K+N+B; K+2B),
  each mate confirmed.
- **Rostovcev's problems #1 and #3 and Rudenko's #5**, every printed line.
- Derzhanski's structural counts: 70 cells in three colours **23 / 23 / 24**
  with **two corners of each colour**.

Three transcription errors on that page were identified while doing so (the
engine is right, the page is mistyped): problem #2's solution says `1.Bb2-g5`
where the position — and bishop geometry — require `Ba2-g5`; problem #3's key
`1.Kd7-c10` names a cell that does not exist (the c-file ends at c8) and the
unique mate-in-2 key is `1.Kd7-c8`; problem #4 prints `5...Rd7-e2` where its own
next move requires `Rd7-e7`, and its white pawn must stand on `h7`, not `h8`
(on h8 the king escapes 8.Ki6-h7 and the self-mate fails). With those readings
every line is exact.

Those numbers, and every geometric detail above, were cross-checked one-time
against two independent oracles: the **Jocly model** (its own board geometry
and per-cell movement graphs for all eleven piece types, the starting array,
the promotion table and the castling tables — 0 mismatches over all 70 cells),
and a **from-scratch reimplementation** written in file/rank coordinates
(89,303 positions compared in lockstep across random games, en-passant-biased
games and randomly constructed positions — 0 legal-move-set mismatches, and
identical perft to depth 3). Perft(4) from this package alone is 3,310,230.
