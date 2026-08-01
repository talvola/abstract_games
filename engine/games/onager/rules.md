# Onager

*Néstor Romeral Andrés, 2012 — published by nestorgames.*

A hexagon-of-hexes with **6 cells per side** (91 cells). Each player tries to reach the
opponent's **back rank**. Nothing is ever captured: a piece that jumps onto an enemy piece
simply sits **on top** of it. Onager was inspired by Robert Abbott's *Epaminondas*.

These are the rules **as implemented here**, following the nestorgames rulebook
`ONAGER_EN.pdf` (© 2012 Néstor Romeral Andrés, "Revisions by Nathan Morse").

## Board and setup

The board is drawn with **horizontal rows** — 6, 7, 8, 9, 10, 11, 10, 9, 8, 7, 6 cells from
top to bottom. The two 6-cell rows are the **back ranks**: the bottom one is **Black's**, the
top one is **White's**.

Each player fills the two rows nearest himself, one disc per cell: 6 + 7 = **13 discs** each,
exactly the disc count in the rulebook's material list.

Then three neutral grey **lakes** are placed, one per turn, **starting with Black**, on any
empty space *except the centre*. So **Black places two lakes and White one**, and — turns
alternating throughout — **White makes the first walk-or-jump**. The lakes exist to break the
board's symmetry and give every game a different landscape.

## Pieces and stacks

A **piece** is a lone disc, or the **topmost** disc of a stack. Discs buried in a stack are not
pieces: they cannot move, and they do not count towards victory, until the disc above them
moves away and *liberates* them.

A stack is created only by **jumping onto an enemy piece**, so the disc under any piece is
always an enemy disc. **Stack height is irrelevant.**

## Your turn — walk *or* jump

**Walk.** Move one of your pieces to an **adjacent empty** space. A lake or any disc blocks.

**Jump.** Two of your **pieces** must be aligned along one of the three axes with **no
obstacle** (a lake or any disc) strictly **between** them. One jumps over the other and lands
exactly as far **beyond** it as the two were apart — a mirror image:

```
   W . . W . . ?          W = your pieces, 3 apart
   0 1 2 3 4 5 6          the jumper lands on cell 6, never on 5
```

* The landing space must be **on the board** and either **empty** or occupied by an **enemy
  piece**. Never a lake, never one of your own pieces.
* Whatever sits **beyond** the jumped-over piece does *not* matter — a lake between it and the
  landing space is fine.
* Landing on an enemy piece **stacks** onto it. Nothing is captured or removed.

**Multiple jumps.** If a jump lands on top of an enemy piece, the same piece **may** jump
again under the same conditions, and so on. This is optional, and the board updates between
hops: the piece really has left its previous square, which is now empty (or shows the enemy
disc it just liberated).

You may not combine a walk with a jump, and **a jumping piece may not end its turn on the
square it started from**.

## Victory

At the **start of your turn, before you move**: if you have strictly **more pieces** on your
opponent's back rank than your opponent has on yours, **you have won**. Only topmost discs
count.

If that has not happened and you **cannot make a legal move** at the start of your turn, you
**lose**. (The rulebook notes this rarely happens; in 600 random games here it never did.)

The rulebook's only draw is **by agreement**. There is no repetition or no-progress rule, so
this package adds a **hard ply cap of 200 plies per board cell** (18,200 at the standard size)
purely as a termination backstop; reaching it is scored as an honest draw. It has never fired:
over 2,500 random games at the published size the longest was **730 plies** (mean 220, median
207, 99th percentile 523), a factor of 25 below the cap, and a decisive result always outranks
it.

## The bot

This package ships **no evaluation function**, on purpose. A candidate one (back-rank
difference plus advancement towards the enemy back rank) was measured *through `MCTSBot`* — the
only thing that would use it — at 100 iterations with the rollout cutoff forced, seats
alternated, 40 games per matchup: **19-21 against a constant-zero eval** and **23-17 against
its own sign-flipped self**. Neither result is significant, so the eval carries no demonstrable
signal and would only have read as bot strength it does not have. Onager's win is tested at the
*start* of a turn, so arriving on the enemy back rank is a claim the opponent gets to answer,
which is probably why the obvious eval does not work.

## Options

| Option | Values | Notes |
| --- | --- | --- |
| Board size | 4, 5, 6, 7 | **6 is the published game.** The other sizes are a platform convenience; the three lakes and all other rules are unchanged. A side-*N* board gives each player *2N+1* discs and an *N*-cell back rank. |

## Notation and how a turn is played

A cell is named by its row letter counting up from Black's back rank (`a` … `k`) and its
position within that row (`a1` is the bottom-left corner, `f6` the centre). A walk is written
`f6-f7`, a jump `f6^f10`, and a multiple jump chains the carets: `f6^f10^d10`.

**A turn is two clicks: the piece, then where it ends up** — whether that is a walk, a single
jump or a chain of five. Internally a move is just `from>to`, with no route, and that is not a
simplification of the rules: whatever a turn is, its effect is the same one operation — the
mover's single disc leaves `from`, liberating any disc under it, and lands on `to`, stacking on
any enemy piece there. **A jump chain changes nothing else**; every square it passes through
reverts the instant the disc leaves it. So the destination determines the resulting position
completely, and every route to a given landing square is equivalent. The move log reconstructs
a shortest route so you can see how the piece travelled.

## Interpretive decisions

Every point where the sheet needed reading rather than transcribing:

1. **White makes the first walk-or-jump.** The lakes are placed as ordinary alternating turns
   starting with Black, and the rulebook says "Black starts. Players alternate turns during the
   game" — so after Black-lake, White-lake, Black-lake, the next turn is White's. The
   alternative (Black opening the movement phase too) would give Black two turns in a row, which
   no edition mentions. AbstractPlay's implementation independently does the same.
2. **Only topmost discs count towards victory.** The 2018 English sheet says only "Remember the
   definition of *piece*"; the superseded **2012 Spanish** sheet spells it out — *"al comienzo
   de tu turno (antes de mover) tienes más **piezas (no discos)**"* — and the endgame figure
   confirms it: one of White's two counted pieces there is only the **top of a stack**.
3. **A jump chain never revisits a cell.** The sheet's "cannot end the turn in the same space
   where it started" is not vacuous — a jumper that was a stack top leaves an *enemy* disc
   behind, so its own start square really can be a legal landing square. During a chain the
   board is exactly "the original board with the mover's one disc relocated", so revisiting a
   cell reproduces an earlier position; deleting the loop gives a legal chain with the same
   final square and the same resulting position. Forbidding all revisits therefore loses no
   reachable outcome and makes the rule impossible to violate.
4. **The start square is vacated for the second and later jumps.** The piece is physically
   somewhere else, so it can no longer serve as the friendly piece to jump over.
   **AbstractPlay's `onager.ts` disagrees**: it generates jump chains against the *un-updated*
   board, so a chain's second and later hops can still use the mover's own abandoned square as
   a partner (or be blocked by it). Over a two-sided differential of **2,641 positions** (1,041
   played, 1,600 constructed with dense stacks) the two engines agreed on every walk, every
   single jump and every terminal result, and differed on **13** multi-hop destinations — every
   one adjudicated to this single defect, with nothing offered by this package that the oracle
   rejected. An earlier route-level comparison over 6,278 positions found the same thing (68
   differing chains, no difference in walks or single jumps).

## Sources

* **Rulebook (authoritative):** <https://www.nestorgames.com/rulebooks/ONAGER_EN.pdf> —
  md5 `41f09beb55336f67e5aa6f57161fdcdb`, PDF creation date 2018-06-23, verified live against
  this package's copy. The English sheet has never been archived by the Wayback Machine.
* **2012 Spanish edition** (archived 2016-03-27) and **Japanese edition** (2018-06-23, archived
  2021-10-14). Comparing them shows the 2018 revision **added** the sentence "Your jumping
  piece cannot end the turn in the same space where it started" — the 2012 Spanish sheet has no
  such clause — while the 2012 sheet is the *more explicit* document about the victory count.
* **BGG:** <https://boardgamegeek.com/boardgame/131047/onager> (Néstor Romeral Andrés,
  nestorgames, 2012).
