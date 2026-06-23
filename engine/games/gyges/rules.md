# Gygès

Gygès (designed by **Claude Leroy**) is a two-player abstract **race** with one
striking twist: **the pieces belong to nobody**. There are no "your" and "my"
pieces — all 12 pieces are shared, and either player may move whichever piece the
rules allow on a given turn. This page documents the rules **as implemented** in
this package.

## Board and goal

- A **6×6** square board. Cells are written `c,r` (`r` grows toward player 2).
- Player 1 starts on the bottom row (`r=0`), player 2 on the top row (`r=5`).
- There is a single **goal cell** beyond each player's far edge:
  - **Player 1's goal** sits beyond row `r=5` (past player 2's home row).
  - **Player 2's goal** sits beyond row `r=0` (past player 1's home row).
- A goal cell is **adjacent to every square of the row in front of it** — i.e. a
  piece on that row is exactly **one step** from the goal.

## The pieces (NEUTRAL, height = movement rank)

- 12 pieces total: **four of height 1, four of height 2, four of height 3.**
- A piece's height is shown as a stack of that many discs with its number on it.
  The height is **only a movement rank** — it is **not** ownership. No piece is
  ever owned by a player.

## Setup

The two home rows are filled with the 12 pieces, two of each height per row. This
package uses a **fixed, documented, symmetric** opening — each home row holds,
left to right (`c=0..5`): **2 3 1 1 3 2**. (Some editions let players place their
own back row; we use a fixed layout for a deterministic, balanced start. This is a
documented ruleset choice — see *Notes*.)

## The active row

> On your turn you may move **only** a piece in the occupied row **nearest your
> own side** — your *active row*.

For player 1 that is the lowest-numbered occupied row; for player 2 the
highest-numbered occupied row. **Fallback:** in the unusual case where no piece in
the active row has any legal move, the next occupied row opens up (and so on),
which guarantees you always have a move.

## Moving a piece

A moved piece travels **exactly** a number of single **orthogonal** steps equal to
its **height** (1, 2 or 3):

- It may **change direction** between steps (turn corners).
- It may **not reuse the same edge** (travel between the same two squares twice)
  within one move.
- Every **intermediate** square along the count must be **empty**; the **final**
  square of the count may be **occupied** (which triggers a bounce or replace).
- The goal cell may be **entered only as a final landing square** and only with an
  **exact** count — you may not pass through it, and if the count cannot finish
  exactly on the goal, the goal cannot be entered.

## The signature mechanic: bounce or replace

If a piece would **end its count on an occupied square**, it does not stop there.
The player chooses one of:

- **Bounce.** The **same moving piece continues**, now moving by **the height of
  the piece it landed on** (the bounced piece **stays where it is**). If that new
  leg again ends on an occupied square, you again choose bounce or replace —
  bounces **chain** until the piece finally settles on an empty square (or the
  goal). A single turn can be a long chain of bounces.
- **Replace.** The moving piece **stops** on that occupied square, and the piece
  that was there is **picked up and dropped on any empty square** (the standard
  restriction "not behind the opponent's home row" never excludes a board square
  on this geometry, so any empty square is legal). The turn then ends.

A turn **ends** when the moving piece settles on an **empty** square, lands on the
**goal**, or you choose **replace**.

## Winning

> You **win** by landing a piece — by a normal move or at the end of a bounce
> chain — **exactly on your own goal cell** (the cell beyond the opponent's home
> edge).

There is no draw in the original game. For engine termination this package adds a
defensive **ply cap of 300**: if neither goal is reached by then the game is a
**draw**. In practice goals are reached far sooner.

## Move notation

A move is a `>`-separated path: the source cell, then each successive **landing**
(`c,r`), with goal landings written `G0` (player 1's goal) / `G1` (player 2's
goal), and a replacement written `R` + the drop cell (e.g. `2,0>3,3>R4,4`). The UI
lets you click the source then the landing; bounce/replace choices are offered as
the continuations of the path.

## Notes / ruleset choices flagged for review

- **Fixed vs. player-placed setup.** The original allows players to place their
  own back rows; we ship a single fixed symmetric layout (`2 3 1 1 3 2`) so the
  opening is deterministic and balanced. This is the one genuine ruleset decision
  here and is flagged for review; it could later become a manifest option
  (fixed / mirrored / free placement).
- **Replacement restriction.** The rule "may not be placed behind the opponent's
  first row" is implemented literally; on the 6×6 grid no board square lies behind
  a home row, so every empty square is a legal drop. Goals are not board squares,
  so they are never legal drops.
