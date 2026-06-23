# Seega

Seega is a traditional two-player custodial-capture game from Egypt and Nubia.
It is played in two phases — a placement phase, then a movement phase — on an odd
square board.

## Board

A square board with an odd side length. **5×5 is the default**; the `size` option
also offers **7×7** and **9×9**. Cells are addressed `col,row`. The single
**centre cell** is special.

## Phase 1 — Placement

The board starts empty. Players alternate turns; on each turn the active player
**places two of their own stones**, one at a time, on any empty cells — with one
restriction: **no stone may be placed on the centre cell**. Placement continues
until every cell except the centre is filled.

Each player therefore ends the placement phase with **(size² − 1) / 2** stones
(12 each on a 5×5 board, 24 on 7×7, 40 on 9×9). The centre is the only empty cell
when movement begins.

In this implementation each placement is a single click (one stone); the turn
passes to the opponent after the active player's second stone.

## Who moves first in Phase 2

**The player who placed second moves first.** Placing first is a disadvantage, so
the second placer opens the movement phase. *(Flagged: sources are not perfectly
consistent here — Wikipedia's wording is ambiguous — but "second placer moves
first" is the common heritage/online convention, and it is what this package
implements.)*

## Phase 2 — Movement and capture

On a turn, a player **moves one of their stones one step orthogonally**
(horizontally or vertically, never diagonally) into an **adjacent empty cell**.
Stones never jump.

**Custodial capture is active.** After the move, look outward from the destination
in each of the four orthogonal directions: if an enemy stone sits directly
adjacent and a friendly stone sits immediately beyond it (a tight sandwich with no
gap), that enemy stone is **captured and removed**. Several directions can capture
on the same move. Capture only happens to the side that just moved — a stone that
**moves into** a position between two enemies is **safe**, not captured.

**The centre cell is a safe square:** a stone standing on the centre can never be
captured.

*(Flagged variant choice: this package allows only a SINGLE move per turn. Some
sources let a player keep moving while each move makes a capture; we do not chain,
for a clean encoding and guaranteed termination.)*

## Cannot move

If the player to move has **no legal move**, they **lose** (a blockade), matching
the documented win condition that a player trapped so they cannot move loses. (We
do not implement the pass / "opponent removes a blocking stone" variants.)

## Winning

A player wins by reducing the opponent to **fewer than two stones** (a lone stone
can never make a custodial capture, so the game is decided) or by **blockading**
the opponent so they have no legal move.

To guarantee termination, a movement-phase **no-progress counter** draws the game
if 120 plies pass with no capture.
