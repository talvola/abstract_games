# Col

**Col** is a map-colouring combinatorial game invented by **Colin Vout**. It is
played here on a **square grid** (default **5x5**; a `size` option offers
3x3 through 7x7). Cell coordinates are `c,r` (column, row), zero-based.

## Players

Two players, each with a colour:

- **Player 1** — the first to move.
- **Player 2** — the second.

## The turn

On your turn you **colour one empty cell with YOUR colour**, subject to a single
restriction:

> The cell you colour must **NOT** be **orthogonally adjacent** (up / down / left
> / right) to any cell that **already holds your OWN colour**.

- It **MAY** be orthogonally adjacent to the **opponent's** colour — that is
  always allowed.
- **Diagonal** adjacency is **never** restricted.

Stones are never moved and never captured. Every move permanently fills one
empty cell, so the game always ends after at most `width x height` moves.

## Winning — normal play (last to move wins)

This package uses the standard **normal-play** convention:

> The player who **cannot make a legal move LOSES**. Equivalently, the **last
> player able to colour a cell WINS**.

There is no separate scoring; the result is decided purely by who runs out of
legal placements first. Because each player's own previously-placed stones block
the cells around them, the board fills until one side is stuck.

## Move notation

A move is a single cell id, e.g. `2,3` (one click in the web UI).

## Note: Snort, the dual game

Col's sibling, **Snort** (also by Vout, popularised in *Winning Ways*), uses the
**opposite** restriction: in Snort you may not colour a cell orthogonally
adjacent to the **OPPONENT's** colour (same colours may sit next to each other).
This package implements **Col**, not Snort.

## Source

See Wikipedia, ["Col (game)"](https://en.wikipedia.org/wiki/Col_(game)).
