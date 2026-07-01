# Cheskers

**Cheskers** is a chess/checkers crossover invented by **Solomon W. Golomb in 1948**.
It is played on the **32 dark squares** of a standard 8×8 board (pieces only ever
occupy squares where *column + row* is even, and all movement is diagonal in
spirit). Each side has **two Kings, one Bishop, one Camel, and eight Pawns**.

## Board and setup

Rendered as a normal 8×8 square board; pieces sit only on the dark squares.

- **Black** (moves first, top of the board): Kings **d8, f8**; Bishop **h8**;
  Camel **b8**; Pawns **a7, b6, c7, d6, e7, f6, g7, h6**.
- **White** (bottom of the board): Kings **c1, e1**; Bishop **a1**; Camel **g1**;
  Pawns **a3, b2, c3, d2, e3, f2, g3, h2**.

**Black moves first**, then players alternate.

## Pieces

### Pawn
Moves, without capturing, **one square diagonally forward**. Captures by
**jumping two squares diagonally forward** over an adjacent enemy piece to the
empty square beyond, removing the jumped piece (exactly like a checkers man).
Multiple jumps chain into a single move. A pawn does **not** capture backward.

### King
Moves like a **promoted checkers piece** (a checkers king): **one square
diagonally in any of the four directions**, and captures by jumping in any
diagonal direction, with multi-jump chains. It is *not* a chess king / not a
slider. The Kings are the royal pieces — losing all of them loses the game.

### Bishop
Moves and captures **exactly as a chess bishop**: slides any distance along a
diagonal and captures by **replacement** (landing on the enemy square). Blocked
by intervening pieces.

### Camel
An **extended knight** — "one diagonal and two straight", i.e. a **(1,3)/(3,1)
leaper** (the fairy-chess Camel). It **leaps over** intervening pieces like a
knight and captures by **replacement** (moving onto the enemy square). A Camel
always stays on the same colour of square.

## Forced capture (a key rule)

If **any Pawn or King can make a checkers jump, you must capture this turn** —
but you may satisfy the obligation **with any piece**: a pawn jump, a king jump,
a bishop capture, or a camel capture (your choice when several exist).

If **no Pawn or King can jump**, capturing is **optional** — a Bishop or Camel
capture never forces you to capture. So only an available pawn/king jump triggers
the obligation.

Within a pawn/king jump, the jump chain continues while that piece can keep
jumping (standard checkers). You are *not* required to choose the longest
available capture.

## Promotion

When a Pawn reaches the far row its move **ends** (even mid jump-chain), and it
**promotes to a King, Bishop, or Camel** — the player's choice. In move notation
this is the `=K` / `=B` / `=C` suffix.

## Winning

You win by **capturing all of the opponent's Kings**, or by **stalemating** the
opponent (leaving them with no legal move — they lose). There is no check or
checkmate; a King can simply be captured.

## Draws / termination safety

To guarantee the game ends, this implementation adds two draw rules (not part of
Golomb's original description): a **50-ply no-progress draw** (no capture and no
pawn move for 50 half-moves — e.g. only Kings/Bishops/Camels shuffling) and a
**400-ply hard cap**.

## Move notation

Moves are `>`-separated cell paths (`"col,row"`, 0-indexed): `"3,5>2,4"` (a step),
`"3,5>1,3>3,1"` (a double jump), `"1,5>0,6=B"` (a pawn promoting to Bishop).

## Interpretation notes / deviations

- Sources (chessvariants.com, Wikipedia, the Seattle Cosmic wiki, all quoting
  Golomb) agree on setup, moves, the forced-capture rule and the win condition;
  they are implemented as stated above.
- Pawn/King multi-jump chaining follows standard checkers (the sources say pawns
  "move as in checkers"); maximal capture is **not** enforced.
- The 50-ply / 400-ply draw rules are an added termination safeguard.
