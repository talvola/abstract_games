# Snort

**Snort** is a combinatorial game devised by **Simon Norton**. It is the **dual
of Col** (Colin Vout's map-colouring game) and is described and analysed in
*Winning Ways for your Mathematical Plays*. It is played here on a **square grid**
(default **5x5**; a `size` option offers 3x3 through 7x7). Cell coordinates are
`c,r` (column, row), zero-based.

## Players

Two players, each with a colour:

- **Player 1** — the first to move.
- **Player 2** — the second.

## The turn

On your turn you **colour one empty cell with YOUR colour**, subject to a single
restriction:

> The cell you colour must **NOT** be **orthogonally adjacent** (up / down / left
> / right) to any cell that **already holds the OPPONENT's colour**.

- It **MAY** be orthogonally adjacent to your **OWN** colour — same colours are
  always allowed to sit next to each other.
- **Diagonal** adjacency is **never** restricted.

(The story behind the name: think of the colours as two farmers' pigs; pigs of the
same farmer are happy beside each other, but a pig will not settle next to a
*rival* farmer's pig.)

Stones are never moved and never captured. Every move permanently fills one
empty cell, so the game always ends after at most `width x height` moves.

## Winning — normal play (last to move wins)

This package uses the standard **normal-play** convention:

> The player who **cannot make a legal move LOSES**. Equivalently, the **last
> player able to colour a cell WINS**.

There is no separate scoring; the result is decided purely by who runs out of
legal placements first. A player can become stuck while empty cells still remain
(every remaining empty cell touches an opponent stone).

## Move notation

A move is a single cell id, e.g. `2,3` (one click in the web UI).

## Snort is the dual of Col

Snort and **Col** share the exact same board, turn, and last-to-move-wins
convention; only the placement restriction is **flipped**:

| Game | Forbidden placement |
|------|---------------------|
| **Col**   | next to your **OWN** colour |
| **Snort** | next to the **OPPONENT's** colour |

For this reason Snort is sometimes informally called "misère Col", but strictly
it is the *dual* of Col (the adjacency constraint is inverted), not the
misère-play (last-to-move-loses) version of Col. This package implements
**Snort** under normal play.

## Source

See Wikipedia, ["Snort (game)"](https://en.wikipedia.org/wiki/Snort_(game)),
and Berlekamp, Conway & Guy, *Winning Ways for your Mathematical Plays*.
