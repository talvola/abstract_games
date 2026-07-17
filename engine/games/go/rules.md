# Go (Weiqi / Baduk)

Go is the great territory game. Players place stones to surround empty space and
capture each other's stones; the player who controls more of the board wins. This
package implements the full game with algorithmic scoring on **9×9**, **13×13** or
**19×19** (choose with the *Board size* option). These are the rules **as
implemented** here.

## Play

- **Black moves first.** On your turn you either **place a stone** on an empty
  point, or **pass**.
- After a placement, any opponent group (stones connected orthogonally) left with
  **no liberties** (no adjacent empty point) is **captured** and removed. Enemy
  captures are resolved before your own group is checked.
- **Suicide is illegal:** you may not play a stone that leaves your own group with
  no liberties unless the move captures something.
- **Superko:** you may not play a stone that recreates any **previous whole-board
  position** (positional superko). This subsumes the simple ko rule and forbids
  longer repetitions too.

## Ending and scoring

The game **ends when both players pass in succession**. It is then scored by
**Tromp-Taylor area scoring**, which is completely algorithmic — *there is no
dead-stone marking step*:

- Each side scores **one point for every stone it has on the board**, plus **one
  point for every empty point that can only reach that colour** (an empty region
  surrounded entirely by one colour is that colour's territory; a region touching
  both colours is neutral).
- **White additionally receives the komi** (a compensation for moving second;
  choose 0.5 / 5.5 / 6.5 / 7.5 with the *Komi* option, default 7.5 — 0.5 is the
  traditional choice for handicap games).

The higher score wins. Because the komi is a half-integer, the game cannot end in
a tie.

> **Note on dead stones.** Under area scoring you should **capture stones you
> consider dead before passing** — they are not removed by agreement. A group that
> truly cannot make two eyes can always be captured given enough moves, and
> filling neutral points does not change the area score, so passing only when the
> position is settled gives the natural result. A hard move cap also forces
> scoring in the rare event a game runs extremely long.

## Variants (options)

- **Handicap** (0 or 2–9 stones, default none). Black's handicap stones are
  pre-placed on the traditional fixed star points and **White plays the first
  move** (a 1-stone "handicap" is just an even no-komi game, so it is not
  offered). The placement follows the standard Japanese convention
  ([Sensei's Library: Handicap placement](https://senseis.xmp.net/?HandicapPlacement),
  and for 13×13/9×9 [Handicap stone placement on smaller boards](https://senseis.xmp.net/?HandicapStonePlacementOnSmallerBoards),
  matching OGS's fixed placement): stones sit on the 4th-line star points
  (3rd-line on 9×9) — 2 = upper-right + lower-left corners; 3 adds lower-right;
  4 adds upper-left; 5 = corners + centre; 6 = corners + left/right sides;
  7 = 6 + centre; 8 = corners + all four sides; 9 = all nine star points.
  Komi is **not** changed automatically — traditionally a handicap game is
  played with komi 0.5, so pick that in the *Komi* option.
- **Board topology: Torus** (default normal). All four edges wrap around
  ([Sensei's Library: Toroidal Go](https://senseis.xmp.net/?ToroidalGo)):
  every point has exactly four neighbours, and there are no corners or edges.
  Capture, liberties, suicide, superko and territory flood-fill all wrap
  consistently. The board is still drawn as a flat grid — remember that the
  left/right and top/bottom edges are adjacent (the caption shows "torus" as
  a reminder). Handicap stones keep their normal grid coordinates, which on a
  torus is an arbitrary (but legal) placement.
- **Mode: Kill-All** (default normal Go). Kill-All Go
  ([Sensei's Library: Kill-all Game](https://senseis.xmp.net/?KillAllGo),
  first proposed in the West by Alexandre Dinerchtein): Black takes a large
  handicap and must **kill every White stone**; White wins by making *anything*
  live. At the end of the game (two passes, or the move cap), **White wins if
  at least one White stone remains on the board; Black wins if none do**. Komi
  is ignored and there are no draws. Traditionally this is played on 19×19
  with a 17-stone free-placement handicap; our fixed-placement handicap option
  goes up to 9, so this is the generalized "Black must kill everything" mode
  at whatever handicap you choose (a documented platform adaptation — set the
  handicap yourself, it is not forced).

## Notation

A move is a point in Go coordinates (a column letter — `I` is skipped by
convention — and a row number from the bottom), e.g. `E5`; passing shows as
`pass`. In the app, **Pass** is a button beneath the board, and the running
score (with komi) is shown in the caption.
