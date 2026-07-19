# SanQi — "The Game of Three"

By L. Lynn Smith (c. 2003, for the Abstract Games / Strategy Gaming Society
*Shared Pieces* design competition). Rules as implemented here follow the
designer's own rules document ("The Rules of SanQi"), cross-checked against
the reprint in *Abstract Games* #17 (2019), pp. 13-17.

Two players — **First** and **Second** by turn order — play on a hexagonal
board of hexagons (side 4 to 10; the designer calls hex-10 optimal and the
smaller boards learning sizes; hex-7 is this module's default).

## Pieces

Three piece types, **shared by both players** (neither side owns any piece),
in unlimited supply — the three Lingqijing characters:

- **Shang 上** "Above" (red)
- **Zhong 中** "Middle" (yellow)
- **Xia 下** "Below" (blue)

The colours follow the magazine's diagrams and do **not** indicate ownership.

## Play

Players alternate; First moves first. Each turn you must do exactly one of
the following (no passing):

- **Placement** — put any one of the three types on any vacant cell.
- **Replacement** — change an occupied cell's piece to a *different* type
  **T**. This is legal only if, among the six neighbours of that cell,
  `count(T) >= count(current type) + 2`. (Equivalently, per the AG#17
  editor: counting the target cell itself plus its six neighbours,
  attackers must strictly outnumber defenders.)

**Immunity:** the piece your opponent just placed *or created by
replacement* cannot be replaced on your immediately following turn. Only
that one piece is protected, only for that one turn; its creator may
replace it on their own next turn.

In the UI, click a cell and pick the type from the pop-up (a vacant cell
places, an occupied cell replaces). The highlighted piece is the opponent's
last move — the one you may not replace this turn.

## Goals

Wins are checked only **at the end of the mover's own turn**, over six
pieces of any *one* type:

- **First** wins if a **circle** of six exists — the six cells surrounding
  some cell, regardless of the condition of that centre cell.
- **Second** wins if a straight **line** of six exists (any of the three
  hex axes).
- **Either** player wins if a compact **triangle** of six exists (rows of
  3-2-1; any of the six orientations) at the end of their own turn.

So a pattern completed by your opponent's move wins for *you* only if it
still stands when your own next turn ends.

## Implementation notes

The sources let replacement play continue indefinitely on a full board, and
say nothing about a player with no legal move. This module adds honest-draw
backstops, all documented here because they are not in the original rules:

- **No-progress draw:** max(40, number of board cells) consecutive
  replacements with no intervening placement.
- **Move-limit draw:** a hard cap of 20 × (number of board cells) plies.
- **Stalemate draw:** a player whose turn arrives with no legal move
  (possible only on a full board with no legal replacement).

A genuine standoff is scored as a draw — never a fabricated tiebreak.
