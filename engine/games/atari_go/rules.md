# Atari Go

Also called **Capture Go** or **first-capture Go** — a teaching variant of Go used to introduce the capturing mechanic without the complexity of territory scoring.

## Objective
Be the **first player to capture any enemy stone(s)**. That single capture wins the game immediately.

## Board & setup
An N×N grid of intersections (the **size** option: 7, 9, or 13; 9 is the default), empty to start. **Black moves first**, then players alternate.

## Play
On your turn, place one stone of your colour on any empty intersection.

A **group** is a maximally-connected set of same-colour stones, using **4-orthogonal** adjacency (up/down/left/right — diagonals do **not** connect). A **liberty** of a group is any empty intersection orthogonally adjacent to one of its stones.

After you place a stone:
1. **Resolve enemy captures first.** Any enemy group adjacent to your new stone that now has **zero liberties** is removed from the board.
2. **Then check your own group.** If your just-placed group has zero liberties after enemy removals, it would be self-captured.

## Capturing wins
If your placement captures **one or more** enemy stones, you **win** immediately — the game ends. There is no scoring; the first capture decides everything.

## Illegal moves
- **Suicide.** A move that leaves your own just-placed group with no liberties **and** captures no enemy stones is **forbidden**. (A move that would self-capture but instead captures an enemy group is legal — and wins.)
- **Positional superko.** A move may not recreate **any** board position that has occurred earlier in the game. This subsumes the simple ko rule (no immediate recapture that repeats the prior position); here we forbid repetition of any prior whole-board position.

## Ending without a capture
If the player to move has **no legal move** — every empty point is either suicide or forbidden by superko, or the board is full — that player **loses**. In practice this is extremely rare; a capture almost always ends the game first.

## Ruleset choices made in this implementation
- **Win condition:** first capture of any number of stones wins (the standard Atari Go / Capture Go rule). Some variants require capturing a fixed count of stones; this package uses the classic "first capture wins" rule.
- **Ko rule:** full **positional superko** (no repeated board position), which is stricter than and includes the basic ko rule.
- **No passing.** Unlike full Go, there is no pass move; a player with no legal move loses, which guarantees the game terminates.
- **No suicide.** Suicide is illegal (the most common Go convention).
- **Coordinates:** moves are `c,r` (0-indexed column,row). The move log uses Go-style letters (skipping `I`) with row numbers counted from the bottom.
