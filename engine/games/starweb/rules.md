# Starweb

*By Christian Freeling (2017). A drawless connection / scoring game.*

Starweb descends from Freeling's **Star** and **Symple** and is, in his words,
"very similar to Havannah." Where Havannah rewards completing a structure,
Starweb rewards **connecting groups through the corners** with a *triangular*
score that makes each additional corner in a group worth more than the last.

## The board

The board is a six-fold-symmetric **"web"** (a cloud / flower of hexes):

- A **hexagon-of-hexes of side 7** (a *hexhex-7*, 127 cells) forms the centre.
- A triangular **chunk of 15 cells** (rows of width 6, 5, 4) grows outward from
  the middle of each of the six sides.
- Total: **217 cells.**

Cells use axial coordinates `q,r` (the third cube coordinate is `s = -q-r`);
neighbours are the six adjacent hexes.

### The 18 stars ("corners")

The web has **18 star cells**, which are the only cells that score:

- **12 outward** stars — the convex tips of the six bumps;
- **6 inward** stars — the concave notches between adjacent bumps.

Intrinsically, a star is exactly a cell with **3 on-board neighbours** (outward)
or **5** (inward). Every non-star cell has 4 or 6. The stars are tinted gold on
the board so they are easy to see.

## Play

- The game starts with a **pie (swap) rule**: after the first stone is placed,
  the second player may instead **swap** — adopt that stone as their own colour
  and pass the move back. (Toggle with the *Pie / swap rule* option.)
- On your turn, **place one stone** of your colour on any empty cell, **or
  pass**. Stones never move and are never captured.
- A pass does **not** forfeit your right to move next turn. The game **ends when
  both players pass in succession.** (As a safety net the engine also ends a
  completely full board.)

## Scoring

Like-coloured connected stones form a **group**. A group containing **n stars**
is worth the **triangular score**

> Σ(n) = n·(n+1)/2 = 1 + 2 + … + n

So a group with **1 star scores 1**, **2 stars → 3**, **3 stars → 6**,
**4 stars → 10**, **5 → 15**, and so on. A group with **0 stars scores nothing**
(but is still useful for *cutting* the opponent's groups to lower their score).

Your total is the sum over all your groups.

## Winning

The player with the **highest total wins.** Starweb is **drawless**: on an equal
score, the player who placed the **second stone** (the second player) wins. This
is why the swap rule matters — both the "placer" and the "chooser" are aware of
it.

## Implementation notes

- The board geometry (217 cells, 18 stars) was reconstructed from the official
  board diagram and verified cell-for-cell against it.
- In this implementation the first player is **Black** (index 0) and the second
  player — who wins ties and is offered the swap — is **White** (index 1).
- A move is a single cell id `q,r`; `swap` and `pass` appear as action buttons.

## Source

Official rules: <https://mindsports.nl/index.php/arena/starweb/738-starweb-rules>
