# Tintas

A colour-collection game by **Dieter Stein** (2016, published by Gerhards).
Official rules: [spielstein.com/games/tintas/rules](https://spielstein.com/games/tintas/rules).

## Material

- A board of **49 hexagonal cells** — a 37-cell hexagon plus six 2-cell bumps
  (the official board shape).
- **49 pieces**: 7 each of 7 colours (red, orange, yellow, green, blue, purple, white).
- **1 neutral pawn**, shared by both players, off the board at start.

## Setup

All 49 pieces are spread **at random** over the 49 cells (this module deals them
when the game starts). Per the official rule, the spread is re-randomised only if
all **seven** pieces of one colour come out adjacent as a single group.

## Play

- **First move of the game**: the first player places the pawn on any cell and
  collects the piece that was there. The turn ends.
- **Every later turn**: slide the pawn in a straight line (any of the 6 hex
  directions) across any number of **vacant** cells; it stops on the **first
  occupied** cell it meets, and you collect that piece.
  - You **may continue**: further slides in any direction, but each continuation
    must land on (and collect) a piece of the **same colour** as those already
    collected this turn. Continue until you are unable **or unwilling** — press
    **end** to stop while continuations remain.
- **Stuck pawn**: if no line from the pawn contains any piece, you must **jump**
  the pawn to any occupied cell, collect that piece, and your turn ends
  immediately (no chaining after a jump).

Click the destination cell to move (the pawn is the only mover); the trays above
and below the board show each player's collected pieces.

## Winning

- **Instantly**, by collecting all **7 pieces of one colour**; or
- by **majority**: the official rules say the game goes on *"as long as one
  player can still get seven pieces of one colour"*; once that is impossible,
  the player holding **4+ pieces in at least 4 different colours** wins.

## Interpretations (as implemented)

- **Setup constraint**: implemented exactly as written — re-deal only when one
  colour's seven pieces form one connected clump (smaller clumps are fine).
- **End of the game**: completing a colour is possible for a player exactly
  while their opponent holds none of that colour. The game therefore ends when
  **both players hold at least one piece of every colour** *and* one player has
  reached 4+ pieces in 4+ colours (at most one player ever can — 4 pieces is a
  colour's majority, and only 7 majorities exist). If neither has, play simply
  continues; at the latest, when the board is empty every colour is fully split
  and exactly one player holds four majorities. **Draws are impossible.**
- **Sliding** is blocked only by pieces; the pawn is the only pawn, so nothing
  else can obstruct a line.
- A turn is entered as a sequence of single-cell sub-moves (each collects one
  piece) plus an explicit **end** action for stopping an optional chain.
