# PÜNCT

PÜNCT (Kris Burm, 2005) is the sixth game of the **GIPF project**. It is a
**connection game with stacking**: you race to link two opposite sides of a
hexagonal board with a contiguous chain of fields your colour shows on top.

This page describes the rules **as implemented** in this package (the BASE game)
and flags every ruleset choice.

## The board

A regular hexagon of **side 9** with the **6 single corner fields clipped off**,
giving **211 fields**. Fields use axial cube coordinates `q,r` (with `s = -q-r`)
centred on the middle field `0,0`; every field satisfies
`max(|q|,|r|,|s|) ≤ 8`, minus the six corners where two coordinates equal 8.

The hexagon has six sides, forming **three pairs of opposite sides** (one pair
per cube axis). A player wins by connecting **any one** of those three pairs —
there are no per-player assigned sides.

The **central hexagon** is the centre field plus its six neighbours (7 fields).

## The pieces

Each player has **18 playing pieces**:

- **6 straight pieces** — three fields in a line.
- **6 angular pieces** — an "elbow": three fields with a 120° bend, where the
  two ends are *not* adjacent to each other.
- **6 triangular pieces** — three mutually-adjacent fields forming a tight
  triangle (the two ends *are* adjacent).

Every piece has three dots, one of which is the coloured **PÜNCT** (the
principal dot); the other two are **minor dots**. A piece always covers exactly
**three adjacent fields**.

Geometrically, anchoring a piece at its PÜNCT, the two minor dots sit at offsets
that classify the shape: opposite directions → straight; adjacent directions →
triangular; otherwise → angular. The move generator enumerates every shape,
PÜNCT position and rotation, so all physical piece orientations are covered.

## A turn

Players alternate; **White moves first**. On your turn you do **one** of:

1. **Add a new piece** — place one of your remaining pieces **flat on three
   empty fields** (base level). The shape must be one you still have, but this
   implementation does not track which of the 6 of each kind remains — it tracks
   only your remaining count (18 total), so you may add any shape until your 18
   pieces are used. *(Ruleset simplification — see below.)*

2. **Move a piece already in play** — take one of your own pieces that is **not
   immobilised** and:
   - slide its **PÜNCT in a straight line** **at least one** field in one of the
     six directions, then
   - optionally **rotate** the piece about the PÜNCT (its shape is preserved).

   *(Ruleset simplification: the official game also lets you **rotate a piece in
   place without sliding it**; this base package requires the PÜNCT to move at
   least one field, so a pure rotate-in-place is not offered. This only ever
   removes a legal option — it never allows an illegal move.)*

   The piece may **stay flat** (landing on three empty fields) or **jump on top
   of other pieces** (stacking), subject to the support rule below.

If a player has no legal add or move, the turn passes automatically.

## Stacking and support

- The **PÜNCT must land on one of your OWN pieces** — i.e. on a field your
  colour currently tops. A PÜNCT may **never** land on an opponent's piece.
- A jumping piece lands **one level above** the existing stack at its PÜNCT
  field. Levels are unlimited; a piece may jump from any level to any other.
- **Every dot must be supported**: each of the three fields the piece covers
  must already have a piece directly beneath it at the new level — **except**:
- **Bridging** — a **straight or angular** piece may leave its **middle minor
  dot** unsupported (a bridge) if its two ends rest on pieces at the new level
  and the field under the middle is strictly lower (a genuine gap). The PÜNCT is
  never the bridged dot, because the PÜNCT must always land on a supporting
  piece. Triangular pieces cannot bridge.
- Minor dots **may** cover an opponent's top piece; the PÜNCT may not.
- Covering any dot of a piece **immobilises** that piece — it can no longer be
  moved while a higher piece sits on any of its dots.

## Winning

The game ends when a player **connects two opposite sides** of the board with a
contiguous chain of fields they show **on top**. Connection is a Hex-style BFS:
two fields are connected if they are **adjacent** (sharing an edge) regardless of
their stacking level — only the colour **visible from above** counts. The first
player to complete such a chain on any of the three axes **wins**.

## Move notation

A move is a `>`-separated path of cell ids (each `q,r`), with the leading tokens
tagged so the orientation is unambiguous:

- **Add**: `Pq,r>Aq,r>Bq,r` — the PÜNCT field, then the two minor-dot fields.
- **Move**: `q0,r0>Pq,r>Aq,r>Bq,r` — the source PÜNCT field, then the PÜNCT and
  minor fields it lands on.
- `pass` when no action is available.

## Ruleset choices (documented for review)

This is a faithful BASE implementation. The following are explicit choices where
the source rules were intricate or where the platform lacks a primitive:

1. **The PÜNCT-piece** (the single-dot marker each player owns) is part of the
   *standard* game's tie-break / central-control machinery, not the base
   connection game; it is **not implemented**. Flagged for review.
2. **Standard-rules central-hexagon restriction**: in the standard game new
   pieces may *never* be placed in the central hexagon and a central-control
   **tie-break** decides an unconnected game. This package implements the BASE
   restriction only — **the first player's first piece may not touch the central
   hexagon**; thereafter the centre is open and there is no central tie-break.
3. **Piece-shape inventory**: the engine tracks a per-player *count* (18) rather
   than the exact 6/6/6 split, so a player could in principle add more than six
   of one shape. This does not affect connection or stacking legality and keeps
   the move generator simple; flagged as a minor faithfulness gap.
4. **Termination**: pieces are finite, but moving pieces around could loop, so a
   hard **move cap (200 plies)** ends an unresolved game as a draw. Real PÜNCT
   games resolve well before this (36 placements plus tactical play).
5. **Rendering**: the platform has no multi-cell-shape primitive, so each covered
   field is drawn as its own disc in the top piece's colour (a three-field piece
   shows as three adjacent same-colour discs) with a small **height label** when
   stacked. A triomino-outline overlay primitive would make piece identity
   clearer — flagged as a rendering enhancement.

Sources verified: Wikipedia "PÜNCT"; UltraBoardGames PÜNCT rules; gipf.com;
BoardGameGeek.
