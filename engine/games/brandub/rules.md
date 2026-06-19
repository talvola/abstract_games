# Brandub (7×7 tafl)

An asymmetric siege game from the hnefatafl family. Player 0 is the **Attackers**
(8 men ringing the board edges) and moves first. Player 1 is the **Defenders** —
a **King** on the central **throne** plus 4 men.

## Moving

Every piece moves like a **rook**: any number of empty squares orthogonally, with
no jumping. Two squares are **restricted**: the central **throne** and the four
**corners**. Only the **King** may stop on a restricted square; any piece may pass
over one while it is empty.

## Capturing

Capture is **custodial and active**: when you move a piece so that an enemy **man**
is sandwiched orthogonally between the piece you just moved (or another of your
pieces) and a friendly piece — or a **hostile square** — that man is removed. A
man is **safe** if it moves *between* two enemies itself.

- **Hostile squares** for capture: the four corners (always), and the throne while
  the King is not standing on it.
- The **King** is *not* taken by simple flanking: he is captured only when
  **surrounded on all four orthogonal sides** by attackers and/or the throne. A
  King on a board edge (one side off the board) cannot be surrounded, so he is
  safe there.

## Winning

- **Defenders win** if the King reaches **any corner** (he escapes the siege).
- **Attackers win** if they **capture the King**.
- A side with **no legal move loses**.

## Notes

- Tafl rules vary between sources; the choices above (corner escape, four-sided
  King capture, corners + empty throne as hostile squares) are stated so play is
  unambiguous. A 200-ply cap draws the rare game that would otherwise shuffle on.
