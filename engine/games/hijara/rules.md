# Hijara

2-player alignment-scoring game by **Martin H. Samuel**. First printed as
*Excel* in American Airlines' *American Way* magazine (1985); sold as *Eclipse*
(1994) and as *Hijara* — Arabic for "small stones" — by Great American Trading
Company (1995) and later Games Above Board / Sterling Games (2003, 2006).
Reviewed by Kerry Handscomb in *Abstract Games* magazine issue 5.

## Board and placement

- The board is a **4×4 array of large squares**, each divided into four small
  squares **numbered 1–4** (on the physical board the numbers run
  clockwise from the bottom-left: 1 bottom-left, 2 top-left,
  3 top-right, 4 bottom-right — this port matches that layout).
- **Sun** (seat 0, moves first) and **Moon** (seat 1) each have 32 stones and
  alternate placing **one stone per turn** on any large square that still has
  an open small square.
- The game's single rule: **within each large square the small squares must be
  filled in numerical order 1 → 2 → 3 → 4.** The small square you fill is
  always the lowest-numbered open one, so there are at most 16 legal
  placements — click the highlighted small square itself. Squares need not be
  completed before starting others.

## Scoring

Points are scored **the moment a formation is completed** (stones never move,
so formations persist; this implementation scores automatically — the physical
game's "overlooked points are forfeited" bookkeeping rule does not apply).
One placement can complete **several formations at once; all of them score**.

- **10 points** — a line of 4 large squares (row, column, or main diagonal of
  the 4×4 array) in which your stones occupy the **same number** in all four
  squares.
- **15 points** — such a line in which your stones occupy the numbers
  **1, 2, 3, 4 in order along the line** (either direction — see
  interpretations below).
- **20 points** — **all four small squares of one large square** occupied by
  your stones.

**Optional rule — 4-corner formations** (the `4-corner formations` option,
off by default): the four corner large squares also act as a scoring group —
your stones on the **same number** in all four corners score **10**, and your
stones on the numbers **1, 2, 3, 4 one in each corner** (any arrangement)
score **15**. BGG's designer-sourced description lists these as "two
additional **optional** ways to score points"; the designer's current Games
Above Board rules text includes them, while the *Abstract Games* #5 review and
the Wikipedia rules summary (matching the original edition) omit them — hence
an option rather than a base rule.

## End of game

The game ends when the last stone is placed (all 64 small squares filled).
The **higher score wins**; equal scores are a **draw**.

## The 3-D equivalence

As Handscomb notes in AG#5, Hijara is exactly **4×4×4 Qubic with gravity plus
scoring**: read small square number *n* of large square (X, Y) as 3-D cell
(X, Y, height *n*−1). The fill-order rule is gravity (each vertical column
fills bottom-up), and the base-game formations are exactly Qubic's 76 lines:
the 40 horizontal lines score 10, the 20 diagonals that change height score
15, and the 16 vertical pillars score 20. (The optional corner formations are
an extra, non-Qubic pattern.) The package selftest verifies the implemented
formation set against an independent enumeration of the 76 lines.

## Implementation notes / interpretations

- **"In order" counts both directions.** A line whose squares read 1-2-3-4
  left-to-right reads 4-3-2-1 right-to-left; both patterns score 15 (players
  sit on opposite sides of a physical board, so a line has no canonical
  reading direction, and only this reading preserves Handscomb's "exactly
  equivalent to Qubic" statement — one-directional scoring would drop half the
  ascending diagonals). The ascending and descending patterns on one line use
  disjoint small squares, so both can in principle be scored, separately.
- **Corner-sequence arrangement** (optional rule only): the four corners have
  no canonical order, so "1-2-3-4 in the corner squares" is implemented as
  *any* assignment of the four numbers, one per corner; each distinct 4-stone
  set that shows all four numbers scores 15 (mirroring how distinct same-number
  sets each score 10).
- **First player.** Wikipedia's rules summary says "Blue starts"; colours are
  cosmetic (the roles are fully symmetric), and this port has **Sun move
  first**, with stones drawn in the platform's standard seat colours (Sun =
  seat 0/red, Moon = seat 1/blue) rather than the physical yellow/blue glass.
- Faint grey numbers on empty small squares reproduce the printed board; a
  stone covers its number, and its position within the large square (1
  bottom-left, 2 top-left, 3 top-right, 4 bottom-right) still identifies it.
- Sources: *Abstract Games* #5 review (complete base ruleset); Wikipedia
  "Hijara"; the designer's Games Above Board site (corner rule text); BGG
  entry 824 (year 1995, publishers, the corner formations marked optional);
  Wikimedia "Hijara layout" board photo (small-square numbering).
