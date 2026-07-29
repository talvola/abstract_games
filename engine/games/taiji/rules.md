# Taiji

**Néstor Romeral Andrés, 2007** (published by nestorgames). 2 players, no
randomness, no hidden information.

*Taiji* is the Chinese "Great Duality" — yin and yang, light and dark, and the
point of the game is that they are **indivisible**. Both players place the same
two-coloured piece, so every turn you play your opponent's colour as well as
your own.

These are the rules **as implemented here**. They follow the designer's own
rulebooks — [TAIJI_EN.pdf](https://nestorgames.com/rulebooks/TAIJI_EN.pdf)
("2007 - 2020 © Néstor Romeral Andrés") and the deluxe-edition sheet
[TAIJIDELUXE_EN.pdf](https://nestorgames.com/rulebooks/TAIJIDELUXE_EN.pdf) —
and were differentialled move-for-move against the
[AbstractPlay](https://play.abstractplay.com) reference implementation.

## Board and pieces

A square grid: **9×9 by default**, with 7×7 and 11×11 offered as options. (The
physical board is 11×11; the smaller games are played on the inner 7×7 or 9×9
squares.)

The only piece is the **TAIJITU** — a domino with one **light** half and one
**dark** half.

**Seat 1 is Light and moves first**; seat 2 is Dark. Each player scores **only
their own colour** — but each player places **both** colours every turn.

## Play

On your turn you **must** place one TAIJITU on two **empty, orthogonally
adjacent** squares (horizontally or vertically — never diagonally). You choose
the orientation, i.e. which of the two squares gets the light half and which
gets the dark half.

There is no passing and no capturing; nothing ever leaves the board.

## End of the game

The game ends **when no TAIJITU can be placed** — that is, when no two empty
squares are orthogonally adjacent.

All three board sizes have an odd number of squares, so the board can never be
filled exactly: at least one square is always left empty, and usually several,
scattered and isolated. Empty squares are worth nothing to anybody.

## Scoring

A **group** is a maximal set of squares of one colour connected **orthogonally**
— "A square is considered to be connected to another square if it is
horizontally or vertically adjacent (**not diagonally**)" (rulebook). Diagonal
contact does not connect.

Your score is the **sum of the sizes of your N largest groups**, where N — the
"scoring type" — is chosen before the game:

| Board | Designer's recommended scoring type |
|---|---|
| 7×7 | 1 group |
| 9×9 | 2 groups (the default here) |
| 11×11 | 3 groups |

All three scoring types are selectable on any board size, exactly as in the
rulebook ("Determine the scoring type (1, 2 or 3 groups)").

**The higher score wins.** If the scores are equal, **Dark wins**: *"In case of
a tie, the 'Dark' player wins."* (TAIJI_EN.pdf, "GAME END"). This tie-break is
the default here because it is the designer's published rule, and equal scores
are common — 13.5% of uniform-random games in the oracle differential. An
**"Equal scores → Draw"** option is offered for players who prefer an honest
draw (it is also AbstractPlay's reading); it changes nothing about a decided
game.

### The designer's worked example

The example figure on page 1 of the rulebook shows a finished 9×9 game — 35
TAIJITUs placed, 11 isolated empty squares — captioned *"Type = 2 groups. Light
wins (6+7=13 vs 5+5=10)"*. That exact position is replayed move by move in this
package's `selftest.py`: Light's groups come out 7, 6, 5, 5, 3, 3, 2, 2, 1, 1
and Dark's 5, 5, 4, 4, 4, 4, 3, 2, 2, 1, 1, so the two-group score is 13–10 to
Light, as printed. (Reading groups with diagonal connectivity would score the
same board 32–25, so the example pins the connectivity rule as well.)

## Notation

Squares are named `a1`…`i9` (file letter left to right, rank number bottom to
top), matching AbstractPlay. A move is written internally as

```
c1,r1>c2,r2
```

— the **first** square takes the **Light** half and the **second** the **Dark**
half. Both orientations of every domino are legal moves, so simply click the
square you want to be light and then the square you want to be dark. The move
log shows e.g. `e5(L)-e6(D)`.

## Why the game always ends

Every legal move fills exactly two empty squares and nothing ever empties a
square, so the number of empty squares strictly decreases by two every ply. A
game is therefore at most ⌊n²/2⌋ plies long — 24 (7×7), 40 (9×9), 60 (11×11) —
whatever the players do. No ply cap or repetition rule is needed, and none is
used.

## Interpretations and deliberate omissions

* **Which colour a seat scores.** The rulebook assigns the colours ("Player's
  colours (light/dark) are determined randomly. 'Light' player starts"), so
  seat 1 is always Light and always moves first here, rather than randomising.
  The tournament format in the rulebook — play twice, once with each colour,
  and add the two scores — is a match structure, not a game rule, and is not
  implemented.
* **Placement adjacency vs. group adjacency.** The rulebook says a TAIJITU
  goes in "a free space of 2 connected squares" and defines "connected" as
  orthogonal only. Both are orthogonal-only here, matching the reference
  implementation.
* **Omega scoring (advanced variant).** The 2020 rulebook adds "Your score is
  calculated by multiplying the sizes of **all** the groups of your colour."
  It is **not** implemented: it is an advanced optional variant, and the
  obvious oracle for it (AbstractPlay's `products` variant) multiplies only the
  *N largest* groups, which is a different rule from the sheet — so there is no
  independent check available for either reading. AbstractPlay's `squares`
  scoring variant appears in no rulebook and is likewise not implemented.
* **The `tonga` variant** in the reference implementation (dominoes may also be
  placed diagonally) is a different nestorgames game, not part of Taiji's
  rules, and is not implemented.
* **Board colouring.** The printed board marks the inner 7×7 and 9×9 areas so
  one physical board serves all three sizes; here each size is simply drawn as
  its own grid.
