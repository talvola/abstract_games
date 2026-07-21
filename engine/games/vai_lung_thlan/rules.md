# Vai lung thlân

A two-player sowing (mancala) game of the **Mizo** people of Mizoram, in the far
east of India. First recorded by Lt.-Col. J. Shakespear in *The Lushei Kuki
Clans* (1912); this implementation follows Ralf Gering's write-up in *Abstract
Games* magazine, issue 12 (Winter 2002). Unlike most Indian mancala variants it
is a **single-lap** game, in the spirit of Oware and Toguz Xorgol.

## Board

Two rows of six holes (12 holes total). **South** owns the bottom row, **North**
the top row. Each player numbers their own holes **1–6 from their right to their
left**. Each hole starts with **5 stones** (60 stones in all). South moves first.

## Sowing

On your turn, pick one of **your** non-empty holes, lift **all** its stones, and
sow them **one per hole**, first along the rest of your own row and then
continuing along your opponent's row, around the board. The emptied origin hole
is part of the loop: with 12 or more stones the sowing wraps all the way around
and drops a stone back into it.

It is a **single lap**: no matter where the last stone lands, the move is over —
you never re-lift and relay from the final hole.

## Capture

If the **last stone lands in a hole that was empty** (so it now holds exactly one
stone), you capture it — **and**, walking **backward** along the path you just
sowed (against the direction of movement), every immediately preceding hole that
also holds **exactly one** stone. This "unbroken chain of single stones" stops at
the first hole that does not hold exactly one.

- The empty landing hole may be on **either** row, and the chain may cross from
  one row to the other. There is no ownership restriction — you may even capture
  single stones in your own row.
- Captured stones are removed from the board and kept in your store.
- There is **no grand-slam exception**: a move captures whatever the rule allows.

A hole holding exactly **12** stones can always capture at least one stone (its
last stone lands back in its own emptied hole). Holes with **more than 12**
stones can never capture — sowing them merely fills every empty hole, which makes
them useful for defense (but "bad shape").

## Turn order, passing and end of game

Players alternate. **Passing is forbidden** unless a player has no legal move
(their whole row is empty): that player is skipped and the opponent moves again.

The game ends when **no stones remain on the board** (every stone has been
captured). The player who has captured **more** stones wins. **If each player has
captured exactly 30 stones, the game is a draw** — a genuine tie is an honest
draw, never broken artificially.

*(Anti-loop backstops, not part of the traditional rules: if a very long stretch
of moves passes with no capture, or a hard ply cap is reached, the game is scored
on the stones actually captured so far — uncaptured stones count for no one.)*

## Notation and worked example

Moves are entered by clicking the hole to sow from. The move log shows, e.g.,
`South 4 (3 stones)`. The endgame problem printed in *Abstract Games* #12 (South
has captured 19, North 23; South to move) is drawn by the line
**4 / 2 / 5 / 1 / 6**, which clears the board to a final **30–30**.
