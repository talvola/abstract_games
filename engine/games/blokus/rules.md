# Blokus

**Bernard Tavitian**, 2000 — originally published by **Sekkoïa** (Mattel acquired Blokus in 2008).
This is the original **four-player** game. Rules below are **as implemented**, from the Mattel
*Blokus* rulebook (R1983).

The two-player *Blokus Duo*, on its own 14×14 board, is a separate game — see the **Blokus Duo**
package.

## Board and pieces

- The board has **400 squares (20×20)**.
- **84 pieces in four colours** — blue, yellow, red and green, **21 pieces per colour**.
- Each colour's 21 pieces are every *free polyomino* of size 1 to 5:
  - **1** one-square piece, **1** two-square piece, **2** three-square pieces,
    **5** four-square pieces, **12** five-square pieces.
- Pieces may be **rotated and flipped** freely. (This is exactly why there are 21 of them:
  counting reflections as distinct would give 29.)

Pieces are named with the standard polyomino letters, size-suffixed:
`I1` (single square), `I2`, `I3` `V3`, `I4` `L4` `N4` `O4` `T4`,
and the twelve pentominoes `F5 I5 L5 N5 P5 T5 U5 V5 W5 X5 Y5 Z5`.

## Play

The order of play is **blue, yellow, red, green** — seats 1 to 4 — which runs **clockwise**
around the board:

| Seat | Colour | Corner |
|---|---|---|
| 1 | Blue | top-left |
| 2 | Yellow | top-right |
| 3 | Red | bottom-right |
| 4 | Green | bottom-left |

1. **"The first piece played by each player must cover a corner square."** Each colour has its
   own corner (the table above).
2. Players then take turns laying down **one piece per turn**:
   - **"Each new piece must touch at least one other piece of the same colour, but only at the
     corners."**
   - **"Pieces of the same colour cannot be in contact along an edge."**
   - **"There are no restrictions on how pieces of different colours may contact each other."**
     Both tests above are **per colour** — only your *own* pieces constrain you. Another
     colour's piece may sit edge-to-edge against yours, but it also gives you no corner to
     build from, and you may never overlap it.
   - Pieces may not overlap, and must lie entirely on the board.
3. **"Once a piece has been placed on the board it cannot be moved during subsequent turns."**
4. A player who cannot place any remaining piece **passes**. Passing is automatic here — the turn
   simply skips a blocked player, so you are never asked to pass by hand.
5. **"The game ends when all players are blocked from laying down any more of their pieces. This
   also includes any players who may have placed all of their pieces."**

## Scoring

Counted at the end, for each player:

- **−1 point per unit square** in your remaining (unplaced) pieces.
- **+15 points** if you placed **all 21** of your pieces.
- **+5 additional points** if you placed all 21 *and* the **last piece you placed was the
  one-square piece**.

So a player who places everything scores **+15**, or **+20** if they finished with the single
square. The rulebook's own worked example (figure 5) scores a completed game as blue **+20**
(all placed, smallest last), yellow **−8** (two four-square pieces left), red **−24** and
green **−20**.

**The player with the highest score wins.**

## Interpretations

The rulebook leaves these points open; this implementation resolves them as follows.

- **Ties are an honest draw.** The rulebook says only that "the player with the highest score is
  the winner" and says *nothing* about equal scores — but a tie is plainly reachable. Rather than
  invent a tiebreak, a tie **for first** is recorded as a **draw** (no winner), whether it is two,
  three or four players level at the top. A sole leader wins outright.
- **The +5 requires the +15.** The wording is "+15 points if all of his/her pieces have been
  placed on the board **plus 5 additional bonus points** if the last piece placed on the board was
  the smallest piece". "Additional" reads as additive on top of the all-21 bonus, and the
  rulebook's figure-5 example scores such a player **+20**. So the +5 is only awarded together
  with the +15, never on its own.
- **Which colour starts on which corner.** The rulebook says only that the first piece "must cover
  a corner square", and that each player "places that set of 21 pieces in front of his/her side of
  the board" — so the corner follows from where a player sits, but the text never names it. The
  four corners are related by the board's symmetry, so the assignment is cosmetic. We use the one
  in the table above, which matches **Pentobi** (the reference Blokus engine) and gives the
  rulebook's blue→yellow→red→green order a clockwise seating.

## Variants not implemented

The rulebook also defines official **two-player** and **three-player** variants, plus a
**two-teams-of-two** variant, all played on the same board with all four colours:

- **Two players:** one player controls blue and red, the other yellow and green.
- **Three players:** each takes one colour and the fourth is shared, played alternately; the
  shared colour's score is ignored.
- **Two teams of two:** blue+red against yellow+green, team scores added.

None of these ship here: the number of seats is fixed before a game exists, so they cannot be a
simple option on this package. This package is the canonical **four-player** game.

## Notation

A move is `KEY:o@c,r` — the piece `KEY`, its orientation index `o`, anchored at cell `c,r`
(the piece's bottom-most, then left-most square — always a square the piece covers). In the app
you simply click a piece in your tray, pick an orientation, and click a highlighted square. The
move log shows e.g. `F5@a20`.

## Correctness

The opening position is anchored against **Pentobi**, the reference Blokus engine: every seat has
exactly **58** legal first moves, split by piece size **{1: 1, 2: 2, 3: 5, 4: 13, 5: 37}**. The
package's `selftest.py` asserts this for all four seats; `_diff_pentobi.py` (manual, one-time)
replays complete random games against `pentobi-gtp` and compares the full legal-move set and the
final scores at every position.
