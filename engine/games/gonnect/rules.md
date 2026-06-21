# Gonnect

**Gonnect** (João Pedro Neto, 2000) is a connection game played with the rules of **Go**. It combines Go's placement-and-capture mechanics with a Hex-like connection goal.

## Objective
**Connect your two opposite edges** with an unbroken chain of your own stones (4-orthogonal adjacency: up/down/left/right — diagonals do **not** connect).

- **Black (player 0)** connects the **TOP** edge (row 0) to the **BOTTOM** edge (row N-1).
- **White (player 1)** connects the **LEFT** edge (col 0) to the **RIGHT** edge (col N-1).

You do **not** win by capturing stones or by territory — connection is the only win condition.

## Board & setup
An N×N grid of intersections (the **size** option: 7, 9, or 13; 9 is the default), empty to start. **Black moves first**, then players alternate.

## Play
On your turn, place one stone of your colour on any empty intersection. **You may not pass** — passing is not allowed.

A **group** is a maximally-connected set of same-colour stones (4-orthogonal adjacency). A **liberty** of a group is any empty intersection orthogonally adjacent to one of its stones.

After you place a stone, standard Go captures apply:
1. **Resolve enemy captures first.** Any enemy group adjacent to your new stone that now has **zero liberties** is removed from the board.
2. **Then check your own group.** If your just-placed group has zero liberties after enemy removals, it would be self-captured (see *Suicide* below).

## Winning by connection
The connection is checked on the **post-capture board** (a capture can break an existing chain, so the board after all removals is what counts). The win is detected by a breadth-first search over your stones starting from those touching one of your edges; if the search reaches the opposite edge, you win immediately. Only the player who just moved can win on their own move.

## Illegal moves
- **Suicide.** A move that leaves your own just-placed group with no liberties **and** captures no enemy stones is **forbidden**. (A move that would self-capture but instead captures an enemy group is legal — captures are resolved first.)
- **Positional superko.** A move may not recreate **any** whole-board position that has occurred earlier in the game. This subsumes the simple ko rule (no immediate position-repeating recapture); here we forbid repetition of any prior whole-board position.

## Losing with no move
There is **no passing**. If the player to move has **no legal move** — every empty point is suicide or forbidden by superko, or the board is full — that player **loses**. This guarantees the game terminates.

## Ruleset choices made in this implementation
- **Edge assignment:** Black owns rows 0 and N-1 (top/bottom); White owns cols 0 and N-1 (col 0 and col N-1, i.e. left/right). A corner stone belongs to both of its owner's edges.
- **Win condition:** connection only (4-orthogonal chain between the mover's two opposite edges), checked on the post-capture board. Capturing stones and territory are irrelevant to the result.
- **Captures:** standard Go — enemy zero-liberty groups removed before the mover's own group is checked.
- **Ko rule:** full **positional superko** (no repeated whole-board position), which is stricter than and includes the basic ko rule.
- **No passing.** A player with no legal move loses; this (with superko) keeps the game finite.
- **No suicide** (the most common Go convention).
- **Coordinates:** moves are `c,r` (0-indexed column,row). The move log uses Go-style letters (skipping `I`) with row numbers counted from the bottom.
