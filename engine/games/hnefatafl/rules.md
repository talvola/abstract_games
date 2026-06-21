# Hnefatafl (11×11, Copenhagen ruleset)

An asymmetric siege game from the Norse **tafl** family, played here on an
**11×11** board with the modern **Copenhagen** tournament rules. Player 0 is the
**Attackers** (24 soldiers in four groups at the edge midpoints) and moves first.
Player 1 is the **Defenders** — a **King** on the central **throne** plus 12
soldiers in a diamond around him.

## Setup

- **King** on the central **throne** (f6 / `5,5`).
- **12 defenders** forming a diamond/cross around the throne: two soldiers out
  along each orthogonal arm, plus the four diagonal points of the diamond.
- **24 attackers** in four **T-shaped groups of 6**, one centred on each board
  edge (five soldiers along the edge plus one stepping inward).
- **Attackers move first.**

## Moving

Every piece moves like a **rook**: any number of empty squares orthogonally, with
no jumping.

There are two kinds of **special square**:

- **The throne** (centre). Only the **King** may *stop* on the throne. Any piece
  may *pass over* the throne while it is empty.
- **The four corners.** Only the **King** may enter a corner. The corners are
  **restricted** to every other piece — soldiers can neither stop on nor pass
  through a corner.

## Capturing

Capture is **custodial and active**: when you move a piece so that an enemy
**soldier** is sandwiched orthogonally between the piece you just moved (or
another of your pieces) and a friendly piece — or a **hostile square** — that
soldier is removed. A soldier is **safe** if it moves *between* two enemies
itself.

- **Hostile squares.** The four **corners** are always hostile. The central
  **throne** is hostile while it is **empty** (the King is not standing on it).
  A hostile square acts as a friendly flank for either side's captures.
- The **King may assist** in captures, flanking an attacker like any defender.

## Capturing the King

The King is **not** taken by simple flanking. He is captured when **all four**
of his orthogonal neighbours are attackers and/or hostile squares:

- On an open square, **four attackers** must surround him.
- When the King stands orthogonally next to the **(empty) throne**, the throne
  counts as one wall, so **throne + 3 attackers** capture him.
- A **corner** next to the King also counts as a wall.
- A King on a **board edge** (with one "side" off the board) **cannot** be
  surrounded, so he is safe there.

## Winning

- **Defenders win** if the **King reaches any corner** square (the Copenhagen
  **corner-escape** rule).
- **Attackers win** if they **capture the King**.
- A side with **no legal move loses**.

## Ruleset choices and omissions

Tafl rules vary between sources; this package fixes the modern Copenhagen rules,
with the following explicit decisions:

- **Corner escape**, not edge escape: the King must reach a corner to win.
- **Restricted throne *and* corners**: only the King may stop on them; corners
  also block non-king sliders entirely.
- **Hostile squares**: the four corners (always) and the empty throne aid
  captures and help surround the King.
- **Four-sided King capture**, with the throne/corner counting as a wall (so a
  King beside the empty throne falls to throne + 3 attackers).

**Omitted advanced Copenhagen rules** (documented here so the implementation is
unambiguous):

- **Shield-wall captures** (capturing a row of pieces pinned against the edge) —
  *not* implemented.
- **Exit forts** (a defender-win impregnable formation on the edge) — *not*
  implemented.
- **"Clear path to a corner" defender win** (an immediate defender win when the
  King has an unobstructed run to a corner) — *not* implemented; the King must
  actually reach a corner.
- A **400-ply cap** draws the rare game that would otherwise shuffle on forever.
