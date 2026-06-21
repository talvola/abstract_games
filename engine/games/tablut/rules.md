# Tablut (9×9 tafl)

An asymmetric siege game from the hnefatafl family, recorded by Linnaeus among
the Sami in 1732. Player 0 is the **Attackers** (16 Muscovite soldiers in four
groups at the edge midpoints) and moves first. Player 1 is the **Defenders** —
a **King** on the central **throne** plus 8 Swedish soldiers in a cross around
him.

## Setup

- **King** on the central throne (e5 / `4,4`).
- **8 defenders** forming a **plus/cross** on the orthogonal axes — two soldiers
  reaching out along each of the four arms from the throne.
- **16 attackers** in four T-shaped groups of 4, one centred on each board edge
  (three soldiers along the edge plus one stepping inward).
- **Attackers move first.**

## Moving

Every piece moves like a **rook**: any number of empty squares orthogonally, with
no jumping. The only special square is the central **throne**: only the **King**
may stop on it; any piece may pass over it while it is empty. (Tablut has no
special corner squares.)

## Capturing

Capture is **custodial and active**: when you move a piece so that an enemy
**soldier** is sandwiched orthogonally between the piece you just moved (or
another of your pieces) and a friendly piece — or a **hostile square** — that
soldier is removed. A soldier is **safe** if it moves *between* two enemies
itself.

- The only **hostile square** for capture is the **throne while the King is not
  standing on it** (an empty throne flanks for either side).
- The **King** is *not* taken by simple flanking: he is captured only when
  **surrounded on all four orthogonal sides** by attackers and/or the throne. A
  King on a board edge (one side off the board) cannot be surrounded.

## Winning

- **Defenders win** if the King reaches **any edge square** of the board (he
  escapes the siege). This is Linnaeus's **edge-escape** rule.
- **Attackers win** if they **capture the King**.
- A side with **no legal move loses**.

## Ruleset choices

Tafl rules vary between sources; this package fixes the following:

- **Edge escape**: the King wins by reaching *any* square on the board's outer
  edge (the rule reported in Linnaeus's account), not only the corners.
- **Four-sided King capture**: the King is captured only when attackers (or the
  empty throne) occupy all four orthogonal neighbours.
- **Hostile squares**: only the empty throne aids capture; corners are ordinary.
- A **200-ply cap** draws the rare game that would otherwise shuffle on forever.
