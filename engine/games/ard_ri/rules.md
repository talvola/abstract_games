# Ard Ri (7×7 Scottish tafl)

**Ard Ri** ("High King" in Scottish Gaelic) is a small game from the **hnefatafl
/ tafl** family — the same family as the shipped **Brandub** (7×7) and **Tablut**
(9×9). It plays on a 7×7 board. Player 0 is the **Attackers** (16 soldiers in
four groups at the edge midpoints) and moves first. Player 1 is the **Defenders**
— a **King** on the central **throne** plus 8 men clustered around him.

It is essentially Brandub with a heavier garrison: where Brandub gives the King
just 4 defenders, Ard Ri gives him 8, against 16 attackers.

## Setup

- **King** on the central throne (d4 / `3,3`).
- **8 defenders** filling the full ring of squares around the throne — the 3×3
  block centred on the throne, minus the throne itself.
- **16 attackers** in four T-shaped groups of 4, one centred on each board edge
  (three soldiers along the edge plus one stepping inward).
- **Attackers move first.**

## Moving

Every piece moves like a **rook**: any number of empty squares orthogonally, with
no jumping. The only special square is the central **throne**: only the **King**
may stop on it; any piece may pass over it while it is empty. Ard Ri has **no
special corner squares** — the corners are ordinary edge squares, which (because
of edge escape, below) are perfectly good escape squares for the King.

## Capturing

Capture is **custodial and active**: when you move a piece so that an enemy
**man** is sandwiched orthogonally between the piece you just moved (or another of
your pieces) and a friendly piece — or a **hostile square** — that man is removed.
A man is **safe** if it moves *between* two enemies itself.

- The **King may assist captures**: he pairs up with a defender to flank an
  attacker just like any other defender piece.
- The only **hostile square** for capture is the **throne while the King is not
  standing on it** (an empty throne flanks for either side).
- The **King** is *not* taken by simple flanking: he is captured only when
  **surrounded on all four orthogonal sides** by attackers and/or the empty
  throne. A King on a board edge (one side off the board) cannot be surrounded.

## Winning

- **Defenders win** if the King reaches **any edge square** of the board (he
  escapes the siege).
- **Attackers win** if they **capture the King**.
- A side with **no legal move loses**.

## Ruleset choices

Tafl rules vary between sources; this package fixes the following, and documents
them because the small-tafl literature is inconsistent:

- **Edge escape** (the chosen ruleset): the King wins by reaching *any* square on
  the board's outer edge. This is the traditional Scottish Ard Ri goal and is why
  the corners get no special treatment here. It **differs from this platform's
  Brandub and corner-Tablut variants**, where the King must reach a **corner** and
  the corners are hostile/restricted squares; in Ard Ri the whole perimeter is the
  goal and no square other than the throne is special.
- **Four-sided King capture**: the King is captured only when attackers (or the
  empty throne) occupy all four orthogonal neighbours, including when the throne
  supplies one of the four walls.
- **King assists capture**: the King counts as a flanking piece for custodial
  capture of attackers.
- **Hostile squares**: only the empty throne aids capture; corners are ordinary.
- A **200-ply cap** draws the rare game that would otherwise shuffle on forever.
