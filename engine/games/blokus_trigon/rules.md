# Blokus Trigon

**4 players.** Bernard Tavitian, Sekkoïa 2006 (Mattel). Blokus on a **triangular
lattice**: the squares become triangles, the polyominoes become **polyiamonds**,
and a piece suddenly has *nine* corners to reach from instead of four.

These are the rules **as implemented**, from the Mattel **R1985** rulebook.

## Components

- A hexagonal board of **486 triangles** (a hexagon nine triangles to a side).
- **88 pieces** — four colours of **22**, one of every shape. Each colour has:

| Triangles | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Pieces | 1 | 1 | 1 | 3 | 4 | 12 |

  That is every **free polyiamond** of 1 to 6 triangles — "free" because pieces
  may be **rotated and flipped**, so a shape and its mirror image are the same
  piece. 110 triangles per colour.
- **Six starting points**, marked on the board. They are **shared**: any colour
  may open on any of them.

## Play

Play passes **Player 1 → 2 → 3 → 4** and repeats.

1. **Your first piece must cover one of the six starting points.** They are not
   assigned to a colour — take whichever you like, but once a starting point is
   covered it is simply occupied, so it is gone for everyone.
2. **Every later piece must touch at least one piece of your own colour at a
   corner, and must never touch your own colour along an edge.**
3. **Different colours are unrestricted** — they may touch edge-to-edge freely,
   and three colours may meet at one point.
4. Pieces never overlap, never leave the board, and never move once placed.

On a triangular lattice each triangle has exactly **3 edge neighbours** and
**9 corner neighbours** (three at each of its three corners). Because the grid is
isometric, one of your triangles may legally touch a *corner* of another of your
triangles that also lies against an edge of a third — the corner rule is about
edges shared, not about proximity.

**A player who cannot place must pass**, and a player who *can* place **must**.
The game ends when **no player can place** anything.

## Scoring

- **−1 point** per unit triangle in each piece you did **not** place.
- **+15** if you placed **all 22** of your pieces.
- **+5 more** if the **last** piece you placed was the **single triangle**.

So a perfect game is +20 and an untouched set is −110. **Highest score wins.**

## Interpretations

The rulebook is explicit about almost everything; two points needed a decision.

- **Ties.** The rulebook says only "the player with the highest score is the
  winner" and never mentions a tie, which is entirely reachable here. A tie for
  first is scored as an **honest draw** — every player gets 0 — rather than
  broken by an invented rule. A sole leader scores +1 and everyone else −1.
- **Passing** is automatic. Rather than making a blocked player choose a "pass"
  move, the engine skips any player with no legal placement, which is exactly the
  rulebook's "the game ends for a player when he/she is blocked" combined with "a
  player MUST play if it is possible to play". You are therefore never offered a
  pass, and never asked to move when you cannot.

## Not implemented

The rulebook's variants: the **2- and 3-player** games (the 3-player game plays on
a smaller inset area of the board), the **teams** game, and the one-player
"Eighty-eight" brainteaser. A game's player count is fixed on this platform, so
this package is the standard **four-player** game.

## Notation

A move is `PIECE:orientation@column,row` — e.g. `1:0@9,6` drops the single
triangle on the starting point at column 9, row 6. In the move log this reads as
`1@j7`. You never type these: click a piece in your tray, pick an orientation if
it offers several, and click a highlighted target.

## Correctness

The board geometry, the 22-piece set and the triangular rotation maths are
anchored against **Pentobi** (Markus Enzenberger's reference Blokus engine): the
opening position has exactly **2478** legal moves — 413 for each of the six
starting points — split by piece size as {1: 6, 2: 18, 3: 54, 4: 168, 5: 540,
6: 1692}. `selftest.py` asserts that and re-derives the edge/corner neighbour
rules from an independent vertex model; `_diff_pentobi.py` checks our legal-move
sets and final scores against Pentobi over complete games.

**Official source:** the Mattel R1985 instruction sheet,
<https://service.mattel.com/instruction_sheets/R1985-0920.pdf>.
