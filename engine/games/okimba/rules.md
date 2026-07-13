# Okimba

Luis Bolaños Mures (2026). A **drawless** square-board connection game — the
"no captures" successor of the designer's Rhode and Akimbo. Instead of
consolidating diagonal links or capturing, Okimba answers the crosscut problem
with a single global constraint: **there may never be more than one naked
diagonal on the board.**

## Board and goal

- Played on the points of an initially empty square grid (**default 11×11**;
  this package also offers 9×9 and 13×13).
- **Black** owns the **top and bottom** edges, **White** the **left and right**
  edges.
- You win by completing a chain of **orthogonally adjacent** stones of your
  colour touching your two opposite edges. Diagonal adjacency does *not*
  connect.
- Black moves first. **Pie rule**: on White's first turn only, White may play
  `swap` to take over Black's opening instead of placing — the lone stone is
  reflected across the main diagonal and recoloured White (Okimba is symmetric
  under transpose + colour swap, so White inherits a position exactly as strong
  as Black's was).

## Definition

- A **naked diagonal** is a pair of like-coloured, **diagonally adjacent**
  stones with **no other like-coloured stone adjacent to both** — i.e. neither
  of the two points completing their 2×2 square holds a friendly stone (an
  *enemy* stone on such a point does not rescue the pair; a *friendly* one
  does).

## Playing a turn

1. Place a stone of your colour on **any empty point**, subject to one rule:
   **immediately after your placement there must be at most one naked diagonal
   on the whole board, counting both colours together.** A placement that would
   leave two or more naked diagonals is illegal.
2. **Nothing is ever removed.** You simply add your stone.
3. The winning connection is checked after the placement.
4. **Passing** is allowed *only* when you have no legal placement; then your
   turn is skipped.

Because a *crosscut* (a filled 2×2 with two interlocking opposite-colour
diagonals) is by definition **two** naked diagonals at once, the "at most one"
rule makes completing a crosscut illegal — which is exactly why Okimba needs no
capture/removal step and remains drawless without any loss of material.

## Moves in this implementation

- Placement: click any empty point whose placement keeps the naked-diagonal
  total at ≤ 1 (only those are offered as legal).
- `swap` (pie rule) appears as a button on White's first turn.
- `pass` is offered only when you have no legal placement (a forced skip).

## Interpretations / notes

- **Legality rule.** Verified against the designer's own reference
  implementation (`Okimba.html`, author luigi87 = Bolaños Mures):
  `isValidOkimbaMove` places the stone and accepts the move iff
  `nakedDiags[0].size + nakedDiags[1].size <= 1` — a cap of one naked diagonal
  **summed over both colours**, tested on the raw post-placement board. This
  package computes the same total and offers exactly the placements that
  satisfy it.
- **No removal.** Unlike Akimbo, Okimba's reference `play()` does **not** call
  the crosscut-resolution routine; the stone is placed and that is all. This
  package mirrors that — `apply_move` never deletes a stone.
- **Passing / silent skip.** The reference silently flips the turn when a player
  has no legal move. This package models that as a forced `pass` pseudo-move,
  offered only when there are zero legal placements.
- **Pie rule.** The designer's description states the swap option for White's
  first turn. It is implemented as the value-preserving single-stone mirror
  (diagonal reflection + recolour), the same convention as this library's Rhode,
  Hex and Konobi.
- **Default board size.** The reference UI's dropdown happens to default to
  13×13, but the designer's BGG metadata (item 468749) lists the family tag
  "Components: 11 × 11 Grids", so this package defaults to **11×11**.

## Draws / termination

Okimba is drawless in real play. As the platform's standard defensive backstop,
reaching a hard ply cap of 8×N×N — or a double pass, reachable only if both
players are simultaneously stuck with nobody connected — is scored as an honest
**draw**, never a fabricated winner.

## How Okimba differs from its siblings

All are Bolaños Mures square-board orthogonal-connection games (Black top/bottom
vs White left/right); the crosscut treatment differs:

- **Rhode** (2016): you must spend a turn *consolidating* each weak/naked pair,
  and your stones caught in a crosscut are **removed**.
- **Akimbo** (2026): a placement is legal iff each colour has ≤ 1 naked diagonal
  (a *per-colour* cap), and completing a crosscut **captures** your other stone
  in it.
- **Okimba** (2026): a placement is legal iff there is ≤ 1 naked diagonal in
  **total** (a *combined* cap) — strictly tighter, forbidding crosscuts
  outright, so there are **no captures at all**.

Sources: [Okimba (BGG item 468749)](https://boardgamegeek.com/boardgame/468749/okimba);
the designer's reference implementation `Okimba.html`.
