# NoGo

The **anti-Go**: a combinatorial Go-family game with *misère* capture — capturing is forbidden, so no stone is ever removed. Devised in the Combinatorial Game Theory tradition (associated with John H. Conway) and used as a computer-Go test bed (a.k.a. "Anti-Atari Go").

## Objective
Be the player who can still make a legal move. The player who, on their turn, has **no legal placement loses** (normal-play convention).

## Board & setup
An N×N square grid of intersections (the **size** option: 7, 9, or 11; default 9), empty to start. **Black** moves first; **White** second.

## Groups & liberties
Stones of the same colour that are **orthogonally adjacent** (up/down/left/right — no diagonals) form a *group*. A group's **liberties** are the empty intersections orthogonally adjacent to any of its stones. This is exactly Go's definition of groups and liberties.

## Play — the one rule that matters
On your turn, place one stone of your colour on an empty intersection. A placement is **ILLEGAL** if it would:

- **(a) Capture** — leave **any enemy group** with zero liberties, or
- **(b) Suicide** — leave **your own** group (the one the new stone joins) with zero liberties.

In other words, **every legal move must leave every group on the board — yours and the opponent's — with at least one liberty.** Because of this, **no stone is ever captured or removed**: the board only fills up.

## Winning & draws
Stones are never moved or removed. Since the board strictly fills, the game always ends within N² placements. The first player who **cannot place a legal stone loses**; the other wins. **Draws are impossible.**

## Notes on this implementation
- **No ko rule is needed.** Captures never happen, so a position can never repeat — every move adds a stone. This makes a ko/superko rule and a pass move unnecessary; there is no passing.
- Adjacency for groups, liberties, capture, and suicide is strictly **4-orthogonal**.
- Move notation is a single cell `c,r` (one click). The move log uses Go-style coordinates (column letters skip "I", rows count from the bottom-left as row 1).
- Board **size** (7/9/11) is selectable; rules are otherwise identical across sizes.
