# Anchor

Steven Meyers, 2000. Published in *Abstract Games* magazine issue 5 (Spring
2001): "Anchor — Redefining Life and Death" by Kerry Handscomb. A territorial
game with Go-style scoring on the standard Havannah board, but with life and
death completely redefined — no liberties, no eyes, no captures during play.

## Board

A hexagon of hexagons, 8 cells per side (169 hexes; base-6 and base-7 are
offered as smaller variants). The six board corners are marked alternately in
the two players' colours: each player has three **home corners** (tinted in
their colour) and three **away corners**.

## Play

- Black moves first. On your turn place one stone of your colour on any empty
  hex, or **pass**. Stones never move and are never captured during play.
- Two consecutive passes end the game.
- **Pie rule** (option, default on): in place of their first move White may
  **swap**. The opening stone changes colour and is reflected through the
  board's centre — because the central reflection maps Black's home corners
  exactly onto White's, the swapped position is strategically identical to
  the one White declined (a plain recolour would not be, since the corner
  colours break the symmetry).

## Life and death

- Same-colour stones on adjacent hexes are **connected**; connectivity extends
  through chains. A stone on the edge of the board is connected to that side;
  a stone in a corner is connected to **both** sides meeting at that corner.
- An **anchor** is a connected group joined to at least two sides of the
  board — **except** that a group joined to exactly two *adjacent* sides is an
  anchor only if those two sides meet at one of its owner's **home corners**.
  - A lone stone in a home corner is an anchor; in an away corner it is not.
  - A group touching two non-adjacent sides, or three or more sides, is
    always an anchor.
- When the game ends, every stone that is not part of an anchor is **dead**.
  All determinations are simultaneous and by **explicit connection only**:
  dead stones are *not* removed first to enable other connections, and there
  is no Go-style implied life.

## Scoring

Dead stones are removed, then each player scores:

- **1 point per empty hex of territory** — an empty region counts for you if
  every stone bordering it is yours (the board edge is neutral filler, as in
  Go). Regions bordering both colours, or no stones at all, are neutral.
- **1 point per dead enemy stone** (prisoner).

The higher total wins. **An equal score is a draw.**

## Implementation notes

- Home-corner assignment matches the magazine's Figure 1 (alternating; unique
  up to rotation, which does not affect play). On screen the six corner hexes
  are tinted in the owning seat's colour.
- The magazine's Figure 3 worked example validates this module: our scorer
  reproduces its Black territory (30) exactly and its 9-point White win, and
  finds the same dead stones **plus one isolated white stone at (4,0) that the
  article's prose overlooked** (it lies deep inside White's territory; counting
  it strictly gives Black 33 / White 42 instead of the printed 32/41 — the
  margin is unchanged because a dead stone inside your own territory nets
  zero). The module applies the rules strictly.
- A safety ply cap (2 x cells + 16, unreachable in normal play: placements are
  finite and any lone pass must be followed by a placement or the game ends)
  guarantees termination; the position is scored as it stands.

## Sources

- *Abstract Games* magazine issue 5 (Spring 2001), pp. 6–7 — complete rules,
  Figures 1–3 (primary source, rules as implemented).
- [BoardGameGeek entry 23235](https://boardgamegeek.com/boardgame/23235/anchor)
  (Steven Meyers, 2000).
- [Board and Pieces: Anchor](https://sites.google.com/site/boardandpieces/list-of-games/anchor)
  (corroborates board size, scoring, and the 2000 invention date).
