# Pentominoes

**Pentominoes** is a two-player placement game invented by **Solomon W. Golomb**
in the **mid-1950s**, and popularised by Martin Gardner in *Mathematical Puzzles
and Diversions* (1959). It is not a commercial product — it is the mathematician's
game that goes with Golomb's pentominoes, and it is a standard example in
combinatorial game theory. It has been **solved**: it is a first-player win.

Hilarie Orman states the rules in one sentence:

> *"Pentominoes is a two-player game involving twelve pieces — the regular
> 5-ominoes shown in Figure 1 — and an 8 × 8 board. Players alternate placing
> pieces on the board, covering whole squares and without overlap. The player who
> cannot make a move loses."*

## Board

An empty **8×8** board. Cells are addressed `c,r` with `c` the column and `r` the
row, both zero-based, `r` increasing up the board.

## The pieces — twelve, in ONE SHARED POOL

The twelve **free pentominoes**: every shape you can make from five squares
joined edge to edge. They carry Golomb's conventional letters
**F, I, L, N, P, T, U, V, W, X, Y, Z** (the mnemonic is *FILiPiNo* plus the end
of the alphabet, *TUVWXYZ*).

- **Rotations *and* reflections are allowed.** A piece and its mirror image are
  the *same* piece, which is what makes the count twelve. (Were reflections
  forbidden there would be 18 "one-sided" pieces; counting every rotation and
  reflection separately gives 63 "fixed" pentominoes.)
- **The twelve pieces are a single pool shared by both players.** There is *not*
  a set of twelve per player. Each piece is used **at most once in the whole
  game, by either player** — once anyone plays the X, the X is gone for both.

Because the pool is shared, **both players always have exactly the same legal
moves**. Pentominoes is therefore an **impartial** game, like Cram (and unlike
Domineering, where each player has their own move set).

## Play

**Player 1 moves first.** On your turn, place **one pentomino that is still in
the pool** onto the board, covering **five whole empty squares**. Placements may
not overlap and may not hang off the board. Pieces, once placed, never move, and
there are no captures. You may rotate and/or flip a piece freely when placing it.

## Winning — normal play

The **player who cannot make a move loses**; equivalently, the last player to
place a piece wins. There are **no draws** — the result is always decisive.

Every move consumes one of the twelve pieces, so a game lasts **at most 12
placements** and always terminates. (12 is achievable: all twelve pentominoes
cover 60 of the 64 squares, leaving four holes. `selftest.py` plays such a game
out.) A game ends as soon as no piece left in the pool fits anywhere.

## The solution

**Pentominoes is a first-player win.** Orman proved this in 1996 by exhaustive
computer search — some 22 billion board positions, about two weeks on a 175 MHz
DEC Alpha — and the winning line was independently verified by a separate program
written by Richard Schroeppel. This package does **not** re-derive that result and
the bot does not know it; it is recorded here as the game's known value.

## The move-count anchors

Orman reports, and this implementation reproduces exactly:

- **2308** legal opening moves.
- **296** opening moves once the board's 8 symmetries are discounted.
- Replies to an opening range from **1181** to "about 2000" (we count 1974).
- **1181** is the fewest replies any opening allows, and the only openings that
  achieve it are placements of the long **L** (Orman's Figure 2). That move is
  **losing** — of the 1181 replies, exactly two refute it, both playing the
  straight **I** piece.
- **1197** is the fewest replies allowed by the **N**, the second most restrictive
  piece — the piece Orman drew in Figure 3 as a **winning** first move.

These numbers are asserted in `selftest.py`. Together they pin down the entire
move generator, and 2308/296 in particular confirm the *free*-pentomino model:
one-sided or fixed pieces would not give these counts.

## Move notation and the interface

A move is **`KEY:o@c,r`** — the piece `KEY`, its orientation index `o`, anchored
at cell `c,r`. In the web UI you never type this: click a piece in the tray to
arm it, pick an orientation from the strip that appears, then click one of the
highlighted squares to place it. The whole footprint ghosts under the cursor
before you commit. Orientations are normalised so that the anchor is always a
square the piece actually **covers**, so the square you click is always part of
the piece you place.

Because the pool is shared, there is **one tray, labelled "Pool"** — not a tray
per player. It always belongs to whoever is to move (it takes their colour), and
a piece vanishes from it as soon as *either* player uses it.

## Ruleset notes

- **Normal play only** (last to place wins). The misère variant (last to place
  loses) is not offered.
- The pieces are coloured by who placed them. This is purely informational — it
  never affects legality, since the pool and the move set are shared.
- The board is the standard empty 8×8; this package offers no other size and no
  pre-removed squares.
- Orman's paper does **not** state a minimum game length, and this package makes
  no claim about one. It does bound the maximum at 12, which follows directly
  from there being twelve pieces.

## Sources

- Hilarie K. Orman, "Pentominoes: A First Player Win", in *Games of No Chance*,
  MSRI Publications vol. 29 (1996), pp. 339–344 —
  [library.slmath.org/books/Book29/files/orman.pdf](https://library.slmath.org/books/Book29/files/orman.pdf)
  (the rules statement, the 2308/296/1181/1197 counts, and the first-player-win proof).
- Solomon W. Golomb, *Polyominoes* (Scribner, 1965; 2nd ed. Princeton, 1994).
- Martin Gardner, *Mathematical Puzzles and Diversions* (1959).
- David Pritchard, "Golomb's Game", in *Brain Games* (Penguin, 1982), pp. 83–85.
- [Pentomino (Wikipedia)](https://en.wikipedia.org/wiki/Pentomino) — the piece
  naming convention and the 12 free / 18 one-sided / 63 fixed counts.
