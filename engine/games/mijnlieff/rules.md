# Mijnlieff

*Andy Hopwood — Hopwood Games, 2010. Winner, UK Games Expo 2010 Best Abstract
Game.* Rules below are **as implemented** in this package, verified against the
official Hopwood Games rules sheet.

## Equipment

- A plain **4×4** board.
- Each player has **8 tiles in their own colour** (Red = player 1, Blue =
  player 2): **two of each of four types**, held in a reserve tray.

| Letter | Name | Glyph | The opponent's next tile must go… |
|---|---|---|---|
| **S** | Straights | ✚ | on an empty square **in a straight (orthogonal) line** from this tile — same row or column, any distance |
| **D** | Diagonals | ✕ | on an empty square **in a diagonal line** from this tile, any distance |
| **P** | Pushers | ◯ | on an empty square that does **NOT touch** this tile (not one of the 8 neighbouring squares) |
| **L** | Pullers | ● | on an empty square that **touches** this tile (one of the 8 neighbouring squares) |

## Play

1. **First move:** the first player places any tile on one of the **12 outside
   (edge) squares** — the central 2×2 is barred for the opening placement only.
2. Thereafter, each tile you place **dictates where your opponent must play
   their next tile** (table above). A tile constrains **the next turn only** —
   it exerts no permanent restriction, and **intervening tiles do not block**
   the straight/diagonal lines.
3. **Passing:** if none of the squares your opponent's tile allows are empty,
   you **must pass**, and your opponent plays again — a **free placement on any
   empty square** (which then constrains you as usual; you may be forced to
   pass repeatedly). Passing is forced and automatic in this implementation.

## Ending the game

As soon as one player places their **last tile**, the opponent gets **ONE last
chance to play** — one final tile (under the usual constraint), **forsaken if
they would have to pass** — and the game ends. One last chance means one last
tile, even if more placements would have been possible.

## Scoring

Score **1 point for each straight or diagonal continuous line of three tiles
in your colour**; longer lines score 1 extra point per extra tile, so a **line
of 4 = 2 points** (it contains two overlapping lines of 3). Lines must be
**consecutive** — a gap or an opposing tile interrupts a line.

**Highest score wins.** An equal score is a **draw** (the official rules give
no tiebreak). With perfect play Mijnlieff is a win for the second player
(Kate Morley, 2021).

## Move encoding

A move is a reserve-tray **drop**: `"<type>@c,r"`, e.g. `"S@1,0"` places a
Straight on column 1, row 0 (0-indexed). In the web UI, the squares you are
allowed to use are tinted; click a tile chip in your reserve tray, then click
a highlighted square. The caption states the active constraint.
