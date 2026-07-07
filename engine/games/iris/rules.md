# Iris

By **Craig Duncan, 2019** (BGG [286792](https://boardgamegeek.com/boardgame/286792/iris);
a finalist in BGG's *Best Combinatorial 2-Player Game Contest of 2019*). Named
for Iris, the Greek goddess of the rainbow. Iris is a close sibling of Duncan's
**Exo-Hex** (2019) and **Side Stitch** (2017): the same best-group scoring with a
recursive tiebreak, but the scoring targets here are the board's own **coloured
rim cells** rather than off-board or side-of-board markers.

## Board

- Played on a **hexhex** board (a hexagon of hexagons) of side length *n*
  (options **4, 5** — default, or **6**; the designer recommends 5–8, with 5 for
  beginners). A hexhex-*n* board has **6(n−1) perimeter cells** and an interior
  of gray cells; hexhex-5 = 24 coloured perimeter + 37 gray = 61 cells.
- The perimeter is **rainbow coloured** so that **each rim cell's same-coloured
  partner is exactly its 180° rotation image** — the antipode. In axial
  coordinates this is `(q, r) → (−q, −r)`. A rotation preserves distance from the
  centre, so a perimeter cell maps to a perimeter cell and a **corner maps to the
  opposite corner**. The 6(n−1) rim cells therefore split into **3(n−1) antipodal
  pairs**, one colour per pair (12 pairs on hexhex-5).
- **Coloring scheme (as implemented):** each rim cell is tinted by a hue derived
  from its screen angle folded into a half-turn, so antipodes (180° apart) share
  a hue while distinct pairs span the colour wheel. Only the *pairing* is
  mechanical — the exact hue is cosmetic. The UI supplies it via `board.tints`.

## Play

- **Black (seat 0) moves first.** On the very first turn Black plays a **single**
  stone on any empty **gray interior** cell.
- **Thereafter each player plays TWO stones per turn** (starting with White's
  first turn), subject to:
  1. **Coloured first stone → forced antipode.** If your first stone is on a
     coloured perimeter cell, your second stone **must** be its same-coloured
     antipode on the opposite side (a corner forces the opposite corner). Both
     cells must be empty — it is an atomic pair.
  2. **Gray first stone → non-adjacent gray.** If your first stone is on a gray
     interior cell, your second stone **must** be any empty **non-adjacent gray**
     cell. If every remaining empty gray cell is adjacent to your first stone,
     the **second stone is forfeited** and your turn is a single stone.
- Stones never move and are never captured. **There is no pie rule** — the
  1-then-2-2-2 protocol is self-balancing.
- You may also **pass**. (Passing is always available; it is the honest way to
  handle a position with no legal placement, and two passes in a row end the
  game.)

## End & scoring

- The game ends when the **board is full** or **both players pass in
  succession**.
- Each player's stones form connected groups under ordinary hex adjacency. **A
  group scores the number of coloured (perimeter) cells it occupies** (a group
  touching no coloured cell scores 0).
- **The owner of the single highest-scoring group wins.**
- **Recursive tiebreak:** if the best groups tie, set them aside and compare the
  next-best groups, and so on — equivalently, compare the two players' descending
  lists of group scores lexicographically (a missing entry counts 0).
- *Implementation note:* the designer states that "despite there being an even
  number of colored cells, for subtle reasons having to do with board geometry,
  it turns out that draws are impossible." This holds for genuinely played-out
  boards, but an early symmetric double-pass (e.g. both players pass at once on a
  near-empty board) really does tie all the way down. Such a total tie is scored
  as an **honest draw** (`winner = None`) rather than inventing a winner.

## Move notation

- Atomic pair (coloured-antipode or gray + non-adjacent gray): `"c1>c2"`.
- Single opening stone or a forfeited-second turn: `"c1"`.
- Pass: `"pass"`. Cells are axial ids `"q,r"`; the UI builds a pair by clicking
  the two cells in turn.

## Sources

- Designer's rules in the [BGG description](https://boardgamegeek.com/boardgame/286792/iris).
- Eric Silverman, [*Connection Games V: Side Stitch*](https://drericsilverman.com/2020/03/12/connection-games-v-side-stitch/)
  (the Iris / Exo-Hex / Side Stitch family).
