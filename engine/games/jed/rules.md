# Jed

A revisioning of Hex with **shared pieces**, **different objectives** and **unequal board spaces**, by J. Mark Thompson and Kerry Handscomb (*Abstract Games* magazine #22, Autumn 2021). Jed is Thompson's earlier game **Jade** (c. 2001) plus the "hox protocol" from Larry Back's Hox (AG21), added to cure Jade's "chilling" flaw.

## Board
A parallelogram of hexagons, **11 columns (1-11) by 9 rows (A-I)** — the standard 9x11. Every cell has a fixed type **J** (red), **E** (green) or **D** (yellow), in the magazine's printed colouring: `type(col,row) = J/E/D by (col - row) mod 3` (a proper three-colouring: neighbouring cells always differ; 33 cells of each type; corners A1=J, A11=E, I1=E, I11=D).

## Roles and objective
One player is **Cross**, the other **Parallel**. Stones are **shared**: a move places one stone of *either* colour (Black or White) on a vacant cell — both players may use both colours on any turn.

- **Cross** wins by forming a single connected group of like-coloured stones (either colour) that touches **all four sides** of the board. Corner cells belong to both adjacent sides.
- **Parallel** wins by forming **two** connected groups, **one Black and one White**, that both touch the **same pair of opposite sides** (either the A/I pair or the 1/11 pair).

The player whose objective is completed **wins even if the other player placed the final stone**. Passing is not allowed.

## The jed (hox) protocol
The first stone may be placed on **any** vacant cell. Thereafter placements must follow the strict cycle **J → E → D → J → …** (red → green → yellow): after a J placement the next stone must go on a vacant E cell, and so on. Because 99 = 3 x 33, the required type never runs out before the board is full, so a legal placement always exists.

## Modified pie rule
The first player places a stone **and declares** a role (Cross or Parallel). The second player either:
- replies with a placement, taking the **other** role, or
- plays **swap**: adopts the first move *and* the declared role, and play returns to the first player.

## Draws are impossible
The article's proof: colour the board's edge pairs like two notional Hex boards (rows Black / columns White, then the reverse). A filled board decides both notional Hex games; if the same colour wins both, Cross has won, otherwise Parallel has won. So a filled Jed board always satisfies one objective — and the protocol guarantees the board can always fill.

## Notes on this implementation
- **Simultaneous completion is impossible**: a Cross group spans *both* pairs of sides, and the opposite-coloured spanning group that Parallel would additionally need must cross one of those two chains — on a hex board two crossing chains always share a cell, so they cannot be different colours. The win check is therefore unambiguous (the implementation tests Cross first, which never matters).
- The magazine sentence "Cross may connect the pair of sides the shorter distance apart, or the other pair" is read as describing **Parallel's** free choice of pair (Cross touches all four sides by definition).
- Only the standard **9x11** board is offered. On it the Jade symmetric-opening restrictions do not apply (they only bite on odd-square or even-sided boards).
- **Minimum stones for a win (and a magazine errata):** Parallel's minimum is **18** stones (two disjoint 9-chains spanning rows A-I — any group touching both of a pair of opposite sides needs at least 9 resp. 11 cells). Cross's true minimum is **11**: the short-diagonal chain A11-I1 touches all four sides *via the two corner cells*, which by rule belong to both edges. This is anchored on the historical Jade implementation on Richard's PBeM server (Cameron Browne & Paul van Wamelen, 2003), whose rules page shows a bare 7-stone short-diagonal chain on a 7x7 board adjudicated "**Cross wins**". The magazine's Addendum-2 statement that "Cross needs 19" counts the row-plus-column cross shape and does not account for the corner rule; the win check here therefore runs from 11 stones so the game ends at the first completion.
- Move log notation: `Black E6 [J]` = a Black stone on column 6, row E (a J cell).

Source: *Abstract Games* #22 pp. 24-25 & 34, including the "Jed board" figure for the J/E/D colouring (extracted pixel-precisely) and the two Addenda on chilling.
