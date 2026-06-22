# Rolit

Rolit is **four-player Reversi**. It plays on a standard 8×8 board; each of the
four players has a colour. These are the rules **as implemented** here.

## Setup

Four balls start in the centre of the board — one of each colour, arranged as a
pinwheel (Player 1 and Player 3 on one diagonal, Players 2 and 4 on the other).
Players move in order **1 → 2 → 3 → 4 → 1 …**

## Your turn

On your turn you **place one ball of your colour on an empty cell that is next to
a ball already on the board** — horizontally, vertically, or diagonally.

If your new ball, together with another of your balls, **brackets a straight line
of other players' balls** (with no gap), every ball in that line **flips to your
colour** — exactly as in Reversi, and in all eight directions at once. A bracketed
line may contain a mix of the other three colours; all of them flip.

Unlike Reversi, you are **not** required to flip anything: any placement next to an
existing ball is legal, whether or not it captures.

## Ending and winning

Because every move adds a ball and none are ever removed, the board fills after
**60 placements**. When it is full, the player with the **most balls** wins. A tie
for the most balls is a **draw**.

## Notation

A move is the cell in board coordinates, e.g. `C4`; the move log shows how many
balls a placement flipped, e.g. `C4 (+3)`. Each player's balls are shown in their
seat colour (Player 1 red, 2 blue, 3 green, 4 amber).
