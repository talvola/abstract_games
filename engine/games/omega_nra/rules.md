# Omega

*Omega* is a placement-and-scoring game by **Néstor Romeral Andrés**
(nestorgames, 2010) — not to be confused with *Omega Chess*. It was "born as
an experiment on complexity and intuitive arithmetic": your score is the
**product** of the sizes of your groups, and on every turn you place stones of
**both** colours.

## Board

A **hexagon of hexagons** ("hexhex") whose side length is selectable from
**5 to 10** hexes (option, default **6** = 91 cells). Cells use axial
coordinates `q,r`; a cell is on the board iff `max(|q|, |r|, |−q−r|) ≤ side−1`.
Each cell has up to six neighbours.

The rulebook notes that 2-player games on boards of side **beyond 8** are
"only recommended for experienced players and scores are often gigantic".

## Players and turn order

Two players: **White** (moves first) and **Black**. Stones never move and are
never captured.

## A turn

On your turn you **must place one stone of each colour in play on free
cells** — with two players that means **two stones: one of your own colour and
one of your opponent's colour**, on two different empty cells anywhere on the
board.

In this implementation each turn is entered as **two clicks**: first the cell
for **your own** stone, then the cell for the **opponent's** stone (the caption
tells you which stone you are placing). The rulebook does not fix an order for
the two placements within a turn; the outcome is the same either way.

## Game end

The game ends when, **just before White's turn, a complete round no longer
fits** — for two players, when **fewer than 4 free cells** remain. (A few
cells always remain empty at the end; the rulebook points out that these empty
spaces "are very important!")

## Scoring

A **group** is a maximal set of connected same-colour stones (6-adjacency); a
lone stone is a group of size 1. Your score is the **product of the sizes of
all your groups** — e.g. groups of 1, 5, 2 and 4 score 1×5×2×4 = **40**.

**The highest score wins.** Per the rulebook, *"in case of a tie, the last of
the tied players wins"* — turn order is White then Black, so **a tie in scores
is a win for Black**. There are therefore no draws.

## Implementation notes

- This package ships the **2-player** game. The physical set also supports 3
  players (red) and 4 players (blue) with the same rules (a complete round then
  needs 9 / 16 free cells); those seat counts are out of scope here.
- The **pie rule** is optional in the rulebook ("although it's not needed, the
  pie rule may be applied upon agreement") and is **not implemented**; the
  tie-break in Black's favour is the built-in balancer.
- Scores are exact big integers internally; captions abbreviate scores past
  seven digits.

Official rulebook: [nestorgames OMEGA_EN.pdf](https://nestorgames.com/rulebooks/OMEGA_EN.pdf)
