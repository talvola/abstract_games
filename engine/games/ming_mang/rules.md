# Ming Mang

**Ming Mang** (Tibetan *mig mangs*, also written **Mig-mang**; the Ludii
project calls it **Gundru**) is the Tibetan custodial-**conversion** game,
popular among Tibetan monks and aristocratic families before 1959. Captured
stones are not removed — they **change colour**, which makes the game a
moving-pieces cousin of Reversi/Othello.

> **Name clash.** "Mig mang" is also the Tibetan name for a Go variant played
> on the same traditional 17×17 board — that is a *different game*, shipped
> here as **Tibetan Go** (`tibetan_go`). This package is the rook-move
> conversion game (Wikipedia "Ming mang (game)"; Ludii's "Gundru" — *not*
> Ludii's "Mig Mang", which is the Go variant).

## Equipment & setup

- An **n×n** board: **8×8** by default (a chessboard, common in the diaspora);
  options for **9×9** (the board Winther's "Tibetan Gundru" describes) and the
  traditional **17×17** (a Tibetan go board).
- Each player has **2n−2 stones on the board** (8×8 → 14, 9×9 → 16, 17×17 →
  32) and the same number again beside the board as a reserve, used only to
  replace captured enemy stones. (Reversi-style two-sided flip pieces work the
  same; the reserve needs no bookkeeping and nothing is rendered for it.)
- Setup (as implemented, matching the Wikipedia 8×8 diagram): each side's
  stones fill **two adjacent edges** of the board. **Black** (seat 0) fills the
  full **left file** plus the interior of the **bottom rank**; **White**
  (seat 1) fills the full **right file** plus the interior of the **top
  rank** — the exact 180° rotation. **Black moves first** (cyningstan leaflet
  #55). Which colour sits where is conventional; sources differ (Ludii puts
  Black on top+right) and all agree the players simply "decide who starts".

## Moving

- Players alternate; a turn moves **one** stone like a **rook**: any number of
  empty cells orthogonally, no jumping, landing on an empty cell.
- **Repetition ban (positional superko):** a move may **not** recreate any
  earlier position of the game (board arrangement + player to move). Such
  moves are simply illegal.

## Capture = conversion

After your stone lands, look outward in each of the four orthogonal directions
from its destination. If an **unbroken line of one or more enemy stones** lies
that way with **a friendly stone just beyond** it (no gaps anywhere), the whole
line is captured. All four directions resolve **simultaneously**, so one move
can capture a row line and a column line at once.

- **Captured stones convert to the capturer's colour in place** (replaced from
  the reserve). The total number of stones on the board **never changes** —
  2·(2n−2) all game.
- Capture is **active only**: moving *into* a sandwich is completely safe, and
  a line of your stones flanked by the enemy is safe until the enemy *re-makes*
  the sandwich with a move. (Unlike Mak-yek there is **no intervention
  capture** — landing between two enemy stones takes nothing unless each
  enemy line is itself flanked beyond by your stone.)
- **Corner stones can never be custodially captured** — there is no cell
  beyond a corner, so no sandwich exists. This is emergent; no special rule.

## Ending the game

- **A player who cannot move on their turn loses** (cyningstan rules 9–10;
  Ludii's BlockWin). This covers both defeat conditions: all your stones were
  converted (you have none to move), or your stones are **blockaded**. Because
  of the repetition ban, "all my remaining moves would repeat a position" also
  counts as having no move — you lose.
- **Draw backstops** (this implementation; the sources give no termination
  guarantee and an "impregnable fortress" standoff is genuinely reachable):
  **80 consecutive plies without any capture**, or **600 plies** total, end
  the game as an honest **draw**. No material tiebreak is applied — a mutual
  fortress standoff is a genuine tie. (Winther's page instead *awards the win
  against* a player who hides in an impenetrable fortress; that rule is
  judgment-based and is not implemented.)

## Option: last-stone leap (Rin-chen Lha-mo, 1926 — off by default)

From *We Tibetans* (1926), the earliest written source: when a player is down
to **one stone**, that stone gains the additional power of capturing by a
**short leap**, as in draughts — jumping over an orthogonally adjacent enemy
stone to the empty cell just beyond. The leapt stone is **removed from the
board** (not converted). Leaping is **optional**, never compulsory, and this
implementation allows one leap per turn (Lha-mo does not describe chains;
Ludii's HopCapture is also a single hop). Rook moves remain available.

## Historical variant not implemented

Lha-mo also describes capture sequences that are "not broken by going around a
corner" — a **corner-turning capture** of an L-shaped line around a board
corner. How far this extends is contested (Shotwell discusses the ambiguity),
and Ludii omits it too; it is documented here but **not implemented**.
Shotwell likewise notes that step-vs-rook movement details in the early
sources are historically open; the rook move is what every modern source uses.

## Coordinates & notation

Cells are `col,row` with `0,0` at the bottom-left. A move is `from>to`, e.g.
`3,0>3,4`. The move log shows algebraic notation with an `xN` suffix when N
stones were captured (e.g. `d1-d5 x3`).

## Sources

- Wikipedia, "Ming mang (game)" (setup diagram, multi-capture cases,
  repetition ban, stalemate loss).
- Damian Walker, *Cyningstan* leaflet #55 (Black moves first; constant board
  population; cannot-move loses).
- Mats Winther, "Tibetan Gundru" (9×9 board; leap optional; fortress caveat).
- Ludii, `Gundru.lud` (DLP game 377; BlockWin, HopCapture, hand-replacement).
- Rin-chen Lha-mo, *We Tibetans* (1926) — the primary written source, via
  Peter Shotwell, "A Form of Tibetan Mig-Mang From the West?".
