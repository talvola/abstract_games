# Konobi

A drawless connection game by **Luis Bolaños Mures** (March 2012), played on
the points of an initially empty square board. *(Rules as implemented in this
package.)*

## Goal

- **Black** (player 0) owns the **top and bottom** edges and wins by completing
  a chain of Black stones touching both.
- **White** (player 1) owns the **left and right** edges and wins by completing
  a chain of White stones touching both.

## Definitions

- Two like-coloured stones are **strongly connected** if they are orthogonally
  adjacent.
- They are **weakly connected** if they are diagonally adjacent **without
  sharing any strongly connected neighbour** — i.e. neither of the two points
  orthogonally adjacent to both holds a stone of the same colour. (If one
  does, the pair is connected *through* that stone instead.)
- Stones of different colours never connect.
- A **chain** is a set of connected stones; **both strong and weak links
  count**. (Because a diagonal pair that shares a friendly orthogonal
  neighbour is chain-connected through that neighbour anyway, chain
  connectivity works out to plain 8-adjacency of like-coloured stones.)

## Play

Starting with Black, players alternate placing one stone of their own colour
on an empty point, subject to two restrictions:

1. **The kosumi rule** (the game's namesake — *kosumi* = diagonal move,
   *nobi* = solid extension): *"It's illegal to make a weak connection to a
   certain stone unless it's impossible to make a placement which is both
   strongly connected to that stone and not weakly connected to another."*
   In other words, if your placement would weakly connect to stone **q**, it
   is legal only when **every** available strong attachment to q is "dirty" —
   occupied, illegal (crosscut), or itself weakly connected to some stone.
   If even one *clean* strong attachment to q exists, you must not attach to
   q weakly. When a placement weakly connects to several stones, this must
   hold for each of them.
2. **No crosscuts**: you may never complete a 2×2 checkerboard containing two
   diagonally adjacent Black stones and two diagonally adjacent White stones.

If you have **no legal placement**, you must **pass** (passing is otherwise
not allowed). The designer notes that at least one player always has a move;
the game ends when a player completes their chain. **Draws are impossible** in
practice; as a safeguard this implementation scores a hypothetical
double-pass with no winner as an honest draw (never observed in testing).

## Pie rule (swap)

Black places first. On White's **first turn only**, White may **swap** instead
of placing: Black's opening stone is removed and replaced by a **White stone
on the diagonally mirrored point** (the designer's own Zillions version
implements "changing sides" the same way — "a White stone on a point
diagonally symmetrical to it"; its mirror uses the other diagonal, which is
equivalent up to the board's 180° symmetry).

## Board size

The designer's material uses 11×11 as the default (his Zillions version
offers 6×6–19×19). This package offers **7 / 9 / 11 / 13 / 15**, defaulting to
**11**.

## Implementation notes

- Rules follow the designer's BGG description and official PDF rule sheet
  (identical wording, incl. worked legal/illegal examples and a full 5×5
  sample game, both reproduced in this package's selftest).
- The designer's Zillions file (`Konobi.zrf` v1.1) contains one extra pattern
  (`cross-pattern`) in its kosumi check that also excuses a weak attachment
  when a strong alternative would merely sit next to a parallel enemy pair.
  That pattern contradicts the prose rule in all three of the designer's own
  sources and looks like an argument transposition of the (redundant)
  crosscut check — swapping its first two arguments yields exactly "the
  alternative would form a crosscut". This port implements the prose rule;
  the difference only surfaces in rare mid-game patterns.

Official sources: <https://boardgamegeek.com/boardgame/123213/konobi>
(description + the official rules PDF under Files).
