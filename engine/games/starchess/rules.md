# Starchess (Polgár Superstar Chess)

**László Polgár** (Hungary) — the chess pedagogue and father of the Polgár
sisters — designed Starchess as a commercial game: a board, a Windows program
("Superstar"), a problem collection and tournaments. It is chess on a **37-cell
hexagram** (Star of David) whose cells carry the printed numbers **1-37**, and
it has two signatures no other hexagonal chess shares:

1. **The players build their own back rank.** Only the pawns start on the board.
2. **There is no hex-diagonal movement anywhere in the game.**

These rules are as implemented here, taken from the official rules sheet
(*Polgar Superstar Chess Rules.doc*) and the 16-image rules gallery at
polgarstarchess.com. Where the prose was silent, the source image is named.

## The board and the numbering

Nine vertical **files** of heights **1, 2, 7, 6, 5, 6, 7, 2, 1** from left to
right. Cells are numbered **bottom-to-top inside a file, files left to right**,
so file 1 = {1}, file 2 = {2, 3}, file 3 = {4…10}, file 4 = {11…16},
file 5 = {17…21}, file 6 = {22…27}, file 7 = {28…34}, file 8 = {35, 36},
file 9 = {37}. Geometrically this is a hexagon of radius 2 (19 cells) plus six
three-cell star points. The numbers are printed on the board in this app, and
the move log uses them.

Internally each cell also has an axial coordinate `q,r` (q = file, r grows
downwards inside a file) purely so the generic hex renderer can draw the star.
As with the other hexagonal chesses in this app, the board is drawn with
**pointy-top hexes**, so the picture is the official diagram rotated by 30°: a
"vertical" file runs up-and-to-the-left on screen. White is at the bottom.

## Setting up — the opening placement phase

The **pawns** are fixed: White 5, 12, 18, 23, 29 — Black 9, 15, 20, 26, 33.

The **king, queen, rook, bishop and knight are not**. Before play, the players
place them one at a time, alternating, on their own five empty back-rank cells:

* White's back rank: **4, 11, 17, 22, 28**
* Black's back rank: **10, 16, 21, 27, 34**

*"White and black place alternately their other men one-by-one on the back rank
behind the pawns in no particular order"* — the official sheet, which labels the
result "1 of 14400" ( = (5!)² ). There is no restriction of any kind: either
player may put any of the five pieces on any of their five free cells, and both
sides see every placement as it happens. Cells 1, 2, 3, 35, 36 and 37 (the left
and right star points) start empty.

**Who places first is not stated in the official prose**, which says only that
the sides place "alternately". This implementation has **White place first**
(White also moves first). That is not a guess: the only other implementation of
Starchess, **Árpád Rusz's Zillions of Games rules file** — linked from the
official site's own Downloads page — declares `(turn-order White Black)` with
`(move-priorities dropping moving)` and both armies' K/Q/R/B/N `off 1`, i.e.
White drops first and the sides then alternate. Black therefore makes the last
placement, and White makes the first move.

*In this app* the phase is played on the board: your unplaced pieces sit in the
reserve tray, click one and then click a highlighted back-rank cell. The move
string is `"K@q,r"` and the move log shows it as `K@22`.

## How the pieces move

There are six **orthogonal** directions (through a cell's edges): straight up,
straight down, and the four oblique ones. There is **no diagonal move in
Starchess at all** — the piece that would normally use the hex diagonals, the
bishop, uses four of the orthogonals instead.

* **Rook** — any distance **vertically only**, 2 directions (rules image 4).
* **Bishop** — any distance along the **four oblique orthogonals**, never
  vertically (image 3).
* **Queen** — any distance in **all six** orthogonal directions (image 2).
* **King** — one step in any of the six orthogonal directions. **No castling**
  (image 1).
* **Knight** — the 12-target hexagonal leap, as in Gliński's chess; it jumps
  (image 5).
* **Pawn** — see below (image 6 gives the move *and* the two capture cells;
  also images 11, 12, 13, 14).

As a check: a queen alone on the central cell 19 reaches
6, 8, 13, 14, 17, 18, 20, 21, 24, 25, 30, 32 — exactly the bishop's eight plus
the rook's four.

### Pawns

* Moves one vacant cell **straight forward** (up the file for White, down for
  Black).
* **Two cells forward only as its very first move.** The official glossary calls
  a pawn that has already captured but sits on a starting cell a **"limping
  pawn"**: it looks like it could double-step but cannot. So the double step is
  tracked **per pawn**, not per square.
* Captures one cell on either **forward oblique orthogonal** — for a pawn on 18
  those are 13 and 24. An enemy man on a *hex diagonal* (14 or 25 from cell 18)
  is **not** capturable. (The official prose only says "captures diagonally",
  which on this board's printed picture means the two upper-oblique neighbours.
  **Rules image 6 settles it**: a white pawn on 18 with its *own* rook on 13 and
  an *enemy* knight on 24 — exactly the two capture cells, one blocked by a
  friend, one taken. Rusz's Zillions file agrees literally: `(Pawn-capture nw)`
  and `(Pawn-capture ne)`, and its `nw`/`ne` link tables send 18 to 13 and 24.)
* **No en passant.** "En passant and castling moves: there are no such special
  moves in Starchess."
* **Promotion is compulsory** on reaching the **opponent's back rank** — and
  nowhere else — to a **queen, rook, bishop or knight** of the same colour.
  White promotes on 10/16/21/27/34, Black on 4/11/17/22/28.

Because promotion is tied to those five cells and not to the end of a file, the
short outer files are traps — the official glossary names them:

* **dead pawn**: a pawn on 2, 3, 35 or 36. Its file has no promotion cell, so it
  must capture at least once before it can ever promote.
* **mummy**: a pawn on 1 or 37. It has no forward move at all and only one
  capture available.

Both are **terminology, not extra rules** — as is "limping pawn", except that
that one records the real per-pawn double-step rule above.

## Ending the game

* **Checkmate** wins.
* **Stalemate is a draw.** The official sheet lists "a stalemate position is
  reached" among the drawing results. (Rules images 9 and 10 are the same
  position with the black king one point of the star away: on 34 it is
  checkmated, on 37 it is stalemated.)
* Other draws implemented here: **threefold repetition**, the **50-move rule**
  (100 plies with no capture and no pawn move), and **bare king vs bare king**.
  Two lone kings are the only material that provably cannot mate on this board —
  the published mate-in-1 problems 2 and 3 show that a lone **bishop** and a lone
  **knight** each *do* mate, and published "Moremovers" problems 3 and 4 show a
  lone bishop actually *forces* mate (in 5 and in 6), so nothing wider is claimed
  as "insufficient".
* **Checkmate outranks every automatic draw.** A mate delivered on the very ply
  that trips the 50-move counter is a win, not a draw (FIDE 5.1.1 / 9.6: the
  automatic draws apply only if the last move was not mate). Threefold-plus-mate
  and bare-kings-plus-mate cannot occur, so in practice this guards exactly the
  50-move counter.
* A genuine draw is a genuine draw: both sides score 0.
* Resignation is available in the app; the sheet's time-limit and
  draw-by-agreement clauses are outside the engine.

A hard ply cap (20 000) exists only as a termination backstop and can never
decide a game. Proof: the 50-move counter ends the game 100 plies after the last
capture-or-pawn-move, so the game is a chain of at most `I + 1` quiet stretches
of ≤ 100 plies each, where `I` counts the irreversible events. There are at most
**18 captures** (the two kings are never captured), and a *non-capturing* pawn
move strictly decreases `r` for White (increases it for Black) while the board
spans only `r = 4 … −4`, so each of the ten pawns makes at most **8** of them:
`I ≤ 18 + 80 = 98`, hence at most `10 + 98 + 100 × 99 = 10 008` plies — half the
cap. Measured: over 600 random and 600 deliberately-stalling self-play games the
longest was **463** plies, and rerunning every one of them with the cap raised to
10⁹ produced byte-identical results, so no outcome depends on the constant.

## Notation

Moves are written with the printed cell numbers: `18-19` (pawn), `Q28-32`,
`26x27=N` (capture and promotion), `K@22` (an opening placement). This notation
is this app's convention built on the board's official numbering.

## Sources

* Official rules sheet, `polgarstarchess.com/Polgar Superstar Chess Rules.doc`
* Official rules gallery, `polgarstarchess.com/Rules/images/1..16.jpg`:
  1 king · 2 queen · 3 bishop · 4 rook · 5 knight · 6 pawn · 7 the fixed pawn
  array · 8, 15, 16 example post-setup arrays · 9 checkmate · 10 the same
  position stalemated · 11 the five promotion cells · 12 dead pawn / mummy ·
  13, 14 two pawn-capture geometry diagrams (14 a capturable forward-oblique
  enemy on 18, 13 a *non*-capturable enemy on the hex diagonal 14). There is
  **no en-passant diagram** — that rule is prose only. The prose likewise does
  **not** describe the knight at all; image 5 does.
* **Árpád Rusz's Zillions of Games implementation** (`zillions-of-games.com`
  submission 1822, March 2010), linked from the official Downloads page. Its
  `links` tables give a complete, independent adjacency list for the board; all
  **168 orthogonal** and **216 knight** directed edges, and all six zones
  (both back ranks, both pawn rows, both promotion zones), match this package
  exactly. It also fixes the placement order (White first) and the pawn-capture
  directions. It does **not** override the official sheet on stalemate: Zillions'
  default makes a player with no move *lose*, whereas the sheet lists stalemate
  among the drawing results and image 10 illustrates one — the sheet wins.
* Official problem set — all **56** published problems are asserted in
  `selftest.py`: `/MateIn1/images/1..12.jpg` (twelve mate-in-1s, each solved
  here by exactly one mating move), `/MateIn2/images/1..16.jpg` and
  `/MateIn3/images/1..16.jpg` (forced mates in exactly two and exactly three),
  and `/Moremovers/images/1..12.jpg` (forced mates in exactly 4, 5, 5, 6, 4, 4,
  4, 4, 4, 4, 4, 4 — every one genuinely longer than three).
  Note that the site's galleries advertise 44 thumbnails per section but only
  12 / 16 / 16 / 12 full-size diagrams actually exist; the rest 404.

## A word of warning about placement

The back rank you build is not cosmetic. Several of its cells are star points
or edge cells with only two to four neighbours — cell 16, for instance, touches
only 9, 10, 15 and 21 — so a king parked there behind its own men can be
smothered almost at once. Random play finds mates in three moves after the
setup phase.
