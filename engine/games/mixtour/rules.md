# Mixtour

A pure stacking game by **Dieter Stein** (2011) for 2 players. Rules as
implemented, verified against the designer's official page
([spielstein.com](https://spielstein.com/games/mixtour/rules)).

## Material

- 5×5 board, initially **empty**.
- Each player (White / Red) has a supply of **20** stackable pieces.
- A single piece also counts as a "stack". White moves first.

## Objective

Build a stack **at least 5 pieces high with your colour on top**.

## Play

On your turn you must do exactly one of:

1. **Enter a piece** — place a new piece of your own colour on any *empty*
   square (click the square).
2. **Move a stack** — move one or more pieces from the **top** of any stack
   (click the stack, then the target; for stacks taller than one, a picker
   asks how many top pieces to move):
   - Pieces move **orthogonally or diagonally in straight lines**.
   - **The move's distance must exactly equal the height of the target
     stack** (before landing). The height of the *moving* stack is irrelevant.
   - A move must **end on another stack** — never on an empty square. Moved
     pieces land on top, keeping their order.
   - Moving pieces **may not cross occupied squares** (no jumping).
   - Stacks may be **split at any level**; remaining pieces stay behind.
   - You may move pieces of **any colour** — ownership does not matter for
     movement (only the top piece matters for winning).
   - You may **not effectively take back your opponent's last move** (moving
     the same pieces straight back to where they came from).

## Pass

If you cannot enter a piece you must move a stack; if no move is available
either, you must **pass** (only then — passing is never optional). If both
players pass in sequence, the game is a **draw** (official rule).

## End of the game

When a move creates a stack of height **5 or more**, that stack is removed
and the player owning its **top piece wins immediately** (the standard
1-point game; note you can lose by being forced to build a stack with the
opponent's piece on top). Removed pieces return to the reserves.

## Draws (as implemented)

The official rules acknowledge that endless move loops are possible and say
such games "should be declared drawn". This implementation makes that
concrete:

- Both players pass in sequence → **draw** (official).
- The same position (board + player to move) occurs a **third time** between
  two entries → draw.
- 100 consecutive plies without a piece being entered → draw (backstop).
- 600 total plies → draw (hard backstop; unreachable in normal play).

## Notation

Squares are `a1`–`e5` (a1 = bottom-left). In the move log `+c3` enters a
piece on c3; `e4-b4 x2` moves the top 2 pieces of e4 onto b4.
