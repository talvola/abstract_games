# Akron

3D connection game by **Cameron Browne** (2002). Played here as implemented from
Browne's own sources: the official rules v3.7 (June 2004, cameronius/cambolbro
site), his article in *Abstract Games* #14 (Summer 2003), his PBM-server help
file, and igGameCenter's rules page.

## Board and aim

An **8×8 grid of holes** (option: 10×10), each player a pile of *n²/2* balls
(32 / 50). **Black** owns the West and East edges, **White** owns the South and
North edges; **corner holes belong to both** adjoining edges. You win by
connecting your two edges with a chain of touching balls of your colour — at
any level. Edge contact is by board-level balls on your border columns/rows.

Balls stack: an elevated point exists wherever a **flat square of four
touching balls** (any colour mix) supports it.

## Touching, connection, the over/under rule

Two balls **touch** if they are orthogonally adjacent on the same level, or one
rests directly upon the other. A **connection** is a chain of touching
same-colour balls — subject to the **over/under rule**: where connections
cross, *the uppermost prevails* and the lower one is cut there until the upper
is removed. As implemented (from the article's Figures 5–6, the v3.7
clarification and igGameCenter's cut diagram):

- **Edge over edge** — orthogonal adjacencies at successive levels cross
  perpendicularly above one another. At each crossing point the highest
  same-colour adjacent pair prevails; every lower adjacency of the other
  colour through that point is severed. (So a level-1 bridge cuts the level-0
  road beneath it — and a level-2 bridge re-cuts the level-1 bridge *and
  frees the level-0 road*, if the level-2 pair is the road's colour.)
- **Piece over piece** — a ball with an enemy ball directly overhead (same
  spot, higher level) is cut from **all** connections; with several balls
  stacked over one spot, the topmost prevails.

## Play

Black places first; on White's first turn White may **swap** (steal the first
move) instead of playing. Then each turn you must either:

1. **Add** a ball from your pile to any vacant **board-level** hole (never
   directly to an upper level), or
2. **Move** one of your balls to any valid empty point that **touches a ball
   connected to the moving ball** (not the mover itself), the touch holding
   both before and after the move. A point is *valid* if it is on the board or
   fully supported **before, during and after** the move — the mover cannot
   serve as its own destination's support, and a ball that dropped this turn
   cannot support the mover.
3. A ball that has balls resting on it may move **only if it supports exactly
   one ball**; that ball then **drops** into the vacated pocket, cascading
   while each dropper in turn supported exactly one ball. (A lift that would
   strand two or more balls is not allowed. Dropping *enemy* support out from
   under a bridge is a key tactic.) The mover may not take the place of a
   dropping ball.

## End of the game

- **Win**: your connection wins **only if it still exists after the
  opponent's replying move** (official v3.7 / PBM default). Implemented as:
  after every move, if the player *not* on move spans their edges, they win at
  once. This also means that lifting an overpass and revealing the opponent's
  connection loses immediately (AG #14).
- A player whose opponent has **no legal move** on their turn wins.
- **Draw**: the article/v3.7 let either player *call* a draw when a position
  repeats a second time; implemented as an **automatic draw on the third
  occurrence** of the same position (same balls, same player to move), plus a
  hard 600-ply cap as a backstop.

## Notation

Cells are `level,col,row`; the move log shows files `a–h`, ranks `1–8` and one
apostrophe per level (`d4` board, `d4'` first interstitial layer, `d4''`
above that). `c3→d4'` = movement, `swap` = pie rule.

## Implementation notes (interpretation calls)

- Support squares may be **any colour mix** (v3.7, igGameCenter, AG Fig 2).
- "Touches a *connected* ball" = a ball connected **to the mover** before the
  move (igGameCenter wording; matches AG Figure 2's exact move set, where
  points adjacent only to *other* White groups are not legal destinations).
- Ai Ai and Ludii do **not** implement Akron (contrary to some databases);
  the oracle sources are Browne's own three rule texts, which agree.
