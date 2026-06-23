# Sygo

**Sygo** is a Go/Othello hybrid by **Christian Freeling** (mindsports.nl). It
plays on a Go board and borrows Go's group-and-liberty capture, but adds the
Othello twist: a captured group is not removed from the board — it is **reversed**
(flipped) to the capturing player's colour. Freeling calls this *othelloanian
capture*.

## Board and opening

- Played on the **intersections** of a square Go grid. Standard size is **19×19**;
  this package also offers **9×9** and **13×13** as options.
- The board starts **completely empty**. (Unlike Othello, there is no four-stone
  centre cross.)
- **White moves first**, then players alternate. (mindsports/Wikipedia.)

## A turn

On your turn you **place one stone on any vacant point**, or you **pass**.

- A stone placed next to one of your existing stones extends (grows) that group;
  a stone placed away from your stones starts a new group. (In Sygo both are just
  "placing a stone".)
- Passing is always allowed and costs nothing toward your turn order.

## Capture — the key Sygo rule (group reversal, not Othello line-flip)

Sygo captures by **liberties, like Go**, but **converts by group, like Othello**:

- A group's **liberties** are the vacant points orthogonally adjacent to it.
- When your placement causes an **enemy group to lose its last liberty**, that
  **entire connected group is reversed to your colour** (it stays on the board,
  flipped — it is *not* removed). Every stone orthogonally connected within that
  surrounded group flips together.

This differs from **Othello** (which flips only the bracketed straight lines
between two of your stones) and from **Go** (which removes captured stones). In
Sygo the surrounded *connected group* flips colour and remains in play.

## Suicide

- **Suicide is illegal**: if, after the move resolves (including any reversals),
  your own group containing the placed stone has no liberty, the move is not
  allowed.
- **Exception (handled automatically):** a placement that reverses an enemy group
  is legal even if the placed stone momentarily had no liberty, *as long as* the
  resulting (now larger, reversed) group is alive — i.e. has a liberty after the
  reversal. Because we check liberties **after** reversing captured groups, this
  case resolves correctly.

## Ko / repetition

To guarantee the game terminates and to forbid endless recapture, a move may not
recreate a previous whole-board position (**positional superko**). This also
covers the simple ko.

## End and scoring

- The game ends when **both players pass in succession** (a resignation also ends
  it in over-the-board play; not modelled here). A hard ply cap is also enforced
  as a safety net for random play.
- Each player's **territory** = the number of their stones on the board **plus**
  the vacant points surrounded by only their colour.
- The **larger territory wins**. Equal territory is a **draw** (a *seki* can force
  this, as Freeling notes).

## Notation

- A move is a single cell `"col,row"` (0-indexed), or `"pass"`.
- Move log uses Go-style coordinates (columns A–T skipping I; rows counted from
  the bottom).

## Implementation notes and FLAGGED rule choices

This package implements the **mindsports rules** (the authoritative source), which
differ from the common BoardGameGeek/secondary summary that describes Sygo as
"Othello with group flips". The authoritative game is **Go-with-reversal**, and
that is what is implemented. Specifically:

1. **FLAG — single-stone turns (simplification).** The mindsports rules allow a
   richer move on a turn: *"put a stone on a vacant point not connected to a
   like-coloured group (a new group), **or** grow any or all of your groups by one
   stone each"* — i.e. a single turn may add **one stone to several different
   groups at once**. They also give **Black** a first-turn balance bonus (grow all
   groups *and* place a stone) when neither player has grown yet. Enumerating
   "grow any subset of groups, one point each" is combinatorially explosive for a
   generic string-move engine on a 19×19 board, so **this package restricts a turn
   to placing a single stone** (which still grows a group when adjacent to your
   stones). The Black balance bonus is therefore also omitted. The capture/scoring
   core — the part that actually defines Sygo — is faithful.

2. **Othelloanian capture is faithful:** an enemy group that loses its last
   liberty is reversed to the mover's colour by connected group, not removed.

3. **Suicide** is illegal with the capturing-move exception, resolved by checking
   liberties after reversals (see above).

4. **Superko** (positional) is added for termination/anti-cycling; mindsports
   notes othelloanian capture itself "does not lead to cycles", so this is a
   conservative safety rule and should rarely bind in normal play.

5. **No komi** is applied (the source describes a plain territory majority; ties
   are genuine draws).
