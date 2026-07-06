# Odd-Y

**Odd-Y** is Bill Taylor's (2015) generalisation of the classic connection game
**Y** to equilateral boards with any **odd number of sides**. The 3-sided case
is the Game of Y itself (shipped separately as *Y*); this package plays the
**pentagon** (5 sides — the game **5-Y**, independently discovered by Ea Ea as
**"Star Y"**) and the **heptagon** (7 sides, **7-Y**).

## The board

A polygon of **hexagonal cells** with `m` equal sides (m = 5 or 7), built as
`m` rhombic sectors meeting at a central cell (the same "mudcrack" pie
construction as our *Poly-Y* board). With **Board side** `n` (cells per spoke,
3–5) the board has `m·n² + m·n + 1` cells; each side has `2n + 1` boundary
cells.

- The **m corners** (gold) are the outer tips where two sides meet.
- **A corner cell counts as part of BOTH sides that meet there.**
- Each side's other boundary cells are tinted their own colour.

## How to play

- **Black** moves first. Players **alternately place one stone** of their
  colour on any empty cell. Stones **never move** and are never captured.
- **Pie (swap) rule** (on by default): on the second player's first turn they
  may play **swap** instead of placing — adopting the lone opening stone as
  their own and handing the move back.

## Winning

> A player wins the moment one of their connected groups touches **three sides
> such that the triangle drawn between the midpoints of those three sides
> contains the board's centre.**

Equivalently: going around the board, **no gap between consecutive connected
sides may exceed half the perimeter** — i.e. every gap is at most `(m−1)/2`
sides.

- **Pentagon (5-Y):** connect **any 3 of the 5 sides EXCEPT 3 consecutive
  ones** — 5 winning triples out of 10; the 5 losing triples are the rotations
  of `{k, k+1, k+2}`.
- **Heptagon (7-Y):** a triple of sides wins iff **it does not fit within 4
  consecutive sides** (no gap of 4 or more) — 14 winning triples out of 35.

**Odd-Y is drawless:** by the generalised Y theorem, a completely filled board
always contains exactly one winning group, and the win is detected on the move
that completes it, so play always ends with a winner.

## Options

- **Board sides:** pentagon (5-Y, default) or heptagon (7-Y).
- **Board side (cells per spoke):** `n = 3, 4, 5` — the default pentagon at
  `n = 4` has 101 cells.
- **Pie (swap) rule:** on/off.

## Implementation notes

- The winning-triple table is derived from the midpoint-triangle rule via the
  cyclic-gap criterion above; the package selftest verifies it against a
  brute-force geometric containment check for both board shapes.
- The board-full-with-no-winner case is unreachable (Y theorem) but is guarded
  as a terminal draw for engine-termination safety.

## Sources

- [Odd-Y on BoardGameGeek](https://boardgamegeek.com/boardgame/223551/odd-y)
  (rules text via the 2021 Wayback snapshot).
- Dr Eric Silverman, "Quick Picks: interesting abstract games in brief" (2021)
  — describes 5-Y: "connect any three sides to win, so long as all three sides
  are not adjacent."
