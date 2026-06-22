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
  choose 5.5 / 6.5 / 7.5 with the *Komi* option, default 7.5).

The higher score wins. Because the komi is a half-integer, the game cannot end in
a tie.

> **Note on dead stones.** Under area scoring you should **capture stones you
> consider dead before passing** — they are not removed by agreement. A group that
> truly cannot make two eyes can always be captured given enough moves, and
> filling neutral points does not change the area score, so passing only when the
> position is settled gives the natural result. A hard move cap also forces
> scoring in the rare event a game runs extremely long.

## Notation

A move is a point in Go coordinates (a column letter — `I` is skipped by
convention — and a row number from the bottom), e.g. `E5`; passing shows as
`pass`. In the app, **Pass** is a button beneath the board, and the running
score (with komi) is shown in the caption.
