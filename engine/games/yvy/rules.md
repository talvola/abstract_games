# YvY

**Designers:** Christian Freeling & David Bush · **Players:** 2 (White = seat 0, Black = seat 1) · White moves first.

YvY is a territory game played on a **serrated hexagonal board** of 147 cells. Twenty-one of them are **sprouts** — the pointed cells around the rim, drawn **green**. Sprouts are what keep your stones alive and are the only cells that score.

## Turn

On your turn you do exactly one of:

- **Place** one stone of *your own* colour on any empty cell, or
- **Pass**. Passing does **not** cost you the right to move on your next turn.

Stones never move and are never removed during play. There are no captures.

**Swap (pie rule).** On the second player's *first* action — when exactly one stone sits on the board — he may **swap** instead of placing. Swapping hands him the opening (the lone stone becomes his) and returns the move to the opener. This offsets the first-move advantage.

## Groups and loops

- A **group** is a set of connected like-coloured stones (connected through the board's adjacency graph). A single stone is a group.
- A **loop** is a group that completely **surrounds** one or more cells — whether those enclosed cells are empty or occupied, by anyone, is irrelevant.
- **The instant your placement completes a loop, you win** — immediately, regardless of the score (sudden death). A loop is checked after every stone you place.

## Ending the game

If **both players pass in succession**, the game ends and is scored.

## Scoring

1. **Life & death.** A group **lives** if at least one of its stones occupies a **sprout**; otherwise it is **dead**. Remove every dead group (of either colour) from the board *before* counting.
2. **Fenced-in territory.** After dead groups are gone, any like-colour group fenced in (enclosed) by another counts as part of that same group. You **control** a sprout if you **occupy** it *or* it is **fenced in** by your stones.
3. **Score.** For each player:

   > **score = (sprouts you control) − 2 × (number of your groups)**

   The higher score wins.

*Worked example from the rules:* one group controlling 11 sprouts scores 11 − 2 = **9**; the opponent controlling the other 16 sprouts with 3 groups scores 16 − 6 = **10** and wins — but with 4 groups only 16 − 8 = **8** and loses. Splitting into more groups costs you.

**Draws.** The parity of the scoring formula means a fully played-out game is always decisive. But a *symmetric early double-pass* (e.g. both players pass on the empty board) genuinely ties at 0–0; that is scored as an **honest draw**, never a fabricated tiebreak.

## Implementation notes (this board)

- **Enclosure** is decided by flood-fill: a cell is "outside" if, moving only through non-barrier cells, you can reach the board's outer rim (a cell with fewer than 6 neighbours); any non-barrier cell you cannot reach is enclosed. The same routine drives both loop detection (barrier = one group) and territory (barrier = a colour).
- On this extracted board the 21 sprouts are **degree-2 spikes** that poke into the exterior. A consequence is that an empty sprout can never be enclosed, and a group that touches a sprout (i.e. is *alive*) always touches the rim, so it can never be fenced in. So here **sprout control is by occupation** and there is no group merging — the fenced-in machinery is implemented faithfully but is inert for scoring on this geometry.
- A hard ply cap and the two-pass rule guarantee every game terminates.
