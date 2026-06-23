# Kamisado

Kamisado is an abstract game by **Peter Burley** (published 2008 by Burley
Games / GameWright / Huch! & friends). Two players race towers across an 8x8
coloured board; which tower you may move is dictated by the colour your opponent
just landed on. This package implements the **base single-round game**.

## The board and the colours

The board is **8x8**. Every cell is one of **8 colours**:

Orange, Blue, Purple, Pink, Yellow, Red, Green, Brown.

The colours are arranged in a **fixed pattern**. That pattern is a *Latin square*
— each colour appears **exactly once in every row and every column** — and the
board has **180-degree rotational symmetry**. This is the standard Kamisado
layout used on the physical board. (Colour layout source: the published Kamisado
board / the Wikipedia "Kamisado" description; the implemented grid is asserted to
be a Latin square with 180-degree symmetry in `selftest.py`.)

Coordinates are `c,r` with `c` the column 0..7 (left to right) and `r` the row
0..7. **Row 0 is player 0's (Black's) home row; row 7 is player 1's (White's)
home row.** The cell colours, row 0 at top to row 7 at bottom, are:

```
Orange Blue   Purple Pink   Yellow Red    Green  Brown
Red    Orange Pink   Green  Blue   Yellow Brown  Purple
Green  Pink   Orange Red    Purple Brown  Yellow Blue
Pink   Purple Blue   Orange Brown  Green  Red    Yellow
Yellow Red    Green  Brown  Orange Blue   Purple Pink
Blue   Yellow Brown  Purple Red    Orange Pink   Green
Purple Brown  Yellow Blue   Green  Pink   Orange Red
Brown  Green  Red    Yellow Pink   Purple Blue   Orange
```

(This exact grid is the standard published Kamisado board; it was cross-checked
against an open-source Kamisado implementation's board array and verified to be a
Latin square with 180-degree rotational symmetry — the main diagonal is all
Orange.)

## The towers

Each player has **8 towers, one of each colour**. They start on the player's home
row, **each tower on the cell of its own colour** (so the home row is itself a
rainbow of all 8 colours, and every tower sits on its match).

## Movement

A tower moves **forward only** — *away from its own home row* — either:

- straight forward (along its column), or
- forward on a diagonal,

**any number of empty cells**. A tower may **never** move sideways or backward,
and may **never jump** over another tower (its own or the opponent's). There is
**no capturing** in Kamisado — every move ends on an empty cell.

Player 0 advances toward row 7; player 1 advances toward row 0.

## The colour chain (the heart of the game)

- The **very first move of the game is free**: player 0 may move any one of their
  towers.
- **After any move, look at the colour of the cell the tower landed on.** The
  opponent **must, on their turn, move the tower of that colour.** This continues
  every turn: the colour you stop on tells your opponent which single tower they
  are forced to move.

## Deadlock (the required tower can't move)

If the player to move finds that their required-colour tower has **no legal move**
(it is boxed in — every forward/forward-diagonal path is blocked), that player
**passes**, and the obligation **bounces**: the opponent must then move the tower
whose colour matches **the colour of the cell the blocked tower is standing on**.

If that opponent's newly-required tower **also** has no legal move at the moment
the turn bounces to them (a true deadlock — neither obliged tower can move and
play cannot continue), the official rule applies: **"the last person to move a
tower before the deadlock occurs loses that round."** So the player who made the
last *actual tower move* before the gridlock **loses**. (The only degenerate case
where no tower has ever moved is scored as a draw; it cannot arise in real play.)

## Winning

You **win the instant you move one of your towers onto the opponent's home row**
(the far row: row 7 for player 0, row 0 for player 1).

## Scope / ruleset choices

- **Base single-round game only.** The official product also defines a *match*
  (best-of / first-to-N rounds) and a *Sumo* variant where a winning tower gains
  "dragon teeth" and starts the next round taller and must reach the home row with
  a deeper push. **Those cumulative-scoring variants are not implemented.**
- **Deadlock / double-deadlock** are handled as documented above (pass + bounce;
  simultaneous gridlock = draw).
- A **defensive ply cap** (600 plies) forces a draw to guarantee termination; in
  practice the colour-chain dynamics resolve far sooner, so the cap should never
  bind in normal play.

## Notation

Moves are clickable cell paths `from>to`, e.g. `3,3>4,4`. When a player's
required tower is blocked, the only legal action is the `pass` button.
