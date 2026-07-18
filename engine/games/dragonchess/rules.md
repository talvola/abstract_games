# Dragonchess

**Gary Gygax, Dragon Magazine #100 (August 1985).** A three-dimensional
fantasy chess variant whose pieces are characters and monsters from *Dungeons &
Dragons*. A Recognized Chess Variant.

These rules follow the standard reference transcription by Edward Jackman
(edited by Hans Bodlaender) at
[chessvariants.com/3d.dir/dragonchess.html](https://www.chessvariants.com/3d.dir/dragonchess.html),
which resolves the ambiguities and typos in Gygax's original text, cross-checked
against Wikipedia's "Dragonchess". Where the original was ambiguous this package
follows the CVP standard interpretation; every such choice is flagged **[ruling]**
below.

## The boards

Three stacked **8×12** boards (12 files **a–l**, 8 ranks **1–8**):

- **Sky** (top board, level **1**)
- **Ground** (middle board, level **2**)
- **Underworld** (bottom board, level **3**)

"Directly above" a cell means the same file/rank on the next board up (Sky is
above Ground is above Underworld). **Gold** (uppercase pieces) moves first, from
ranks 1–2; **Scarlet** (lowercase) moves second, from ranks 7–8. "Forward" is
toward the enemy: +rank for Gold, −rank for Scarlet. The near-right corner of
every board is a light square. There is **no** pawn double-step, no *en
passant*, and no castling (a nod to Gygax's beloved Shatranj).

### Coordinates and move notation (this implementation)

A cell id is **`level,file,rank`** with `level ∈ {1,2,3}` (1 = Sky, 2 = Ground,
3 = Underworld), `file ∈ 0..11` (a–l) and `rank ∈ 0..7` (1–8). A move is
`from>to`, e.g. `2,4,1>2,4,3`; the Warrior's forced promotion appends `=H`. The
three boards are drawn **stacked vertically** — Sky on top, Underworld on the
bottom — because three 12-wide boards side-by-side would be extremely wide; the
vertical stack also matches the physical "boards above each other".

## Starting setup

Each side has **42** pieces (84 total):

- **Sky:** Sylphs on the pawn rank at files a c e g i k; Griffins at c/k and the
  Dragon at g on the back rank.
- **Ground:** back rank **O U H T C M K P T H U O** (Oliphant, Unicorn, Hero,
  Thief, Cleric, Mage, King, Paladin, Thief, Hero, Unicorn, Oliphant) with 12
  Warriors on the pawn rank.
- **Underworld:** Dwarves on the pawn rank at files b d f h j l; Basilisks at
  c/k and the Elemental at g on the back rank.

The **Dragon is the letter `R`** (to distinguish it from the **Dwarf `D`**), per
Gygax. Icons: the Dragon shows a dragon, the Mage a wizard, the Unicorn a
unicorn, and the Paladin a centaur (its King+Knight move); every other piece
shows its letter.

## The pieces

### Sky

- **Sylph (S)** — a Berolina-style pawn. On the Sky it moves **one step
  diagonally forward** (non-capturing), captures **one step directly ahead**, and
  may capture **straight down** onto the Ground (removing the piece directly
  below). This capture is the only way a Sylph reaches the Ground; once there it
  **cannot move at all except to return to the Sky**, non-capturing, to the cell
  directly above it **or** any empty one of its six home cells (the files a c e g
  i k on its own pawn rank). **Sylphs never promote.**
- **Griffin (G)** — on the Sky, an unblockable **(3,2) leap** (three one way,
  two perpendicular). It may hop **Sky→Ground** to any cell diagonally adjacent
  to the cell directly below it. On the Ground it moves **one square diagonally**
  or returns **Ground→Sky** to a cell diagonally adjacent to the cell above it.
  The Griffin never touches the Underworld.
- **Dragon (R)** — confined to the Sky, where it moves as a **Bishop or King**
  (diagonal slides plus a one-step orthogonal). Instead of moving it may
  **capture from afar**: without moving, it removes one enemy piece on the Ground
  that is in the cell **directly below** it or **orthogonally adjacent to that
  cell** (a 5-cell cross). It may **not** both move and capture-from-afar in the
  same turn. **[ruling]** The CVP editor suggests optionally weakening the Dragon
  to only the cell directly below; this package implements the **full 5-cell**
  standard rule.

### Ground

- **Oliphant (O)** — a **Rook**; never leaves the Ground.
- **Unicorn (U)** — a **Knight**; never leaves the Ground.
- **Thief (T)** — a **Bishop**; never leaves the Ground.
- **Hero (H)** — on the Ground, **one or two cells diagonally, jumping** over any
  piece between. It may step to the **Sky or Underworld** onto a cell diagonally
  adjacent to the cell above/below it, and while on the Sky or Underworld it can
  do nothing but return to the Ground the same way.
- **Cleric (C)** — a **King on whichever board it stands on**, and may also step
  to the cell **directly above or below**.
- **Mage (M)** — a **Queen** on the Ground, and may step to the cell directly
  above/below. On the Sky or Underworld it moves **one cell orthogonally**, or
  **one or two cells straight up/down** — but the two-step vertical **may not
  leap over a piece on the Ground**.
- **King (K)** — a **King** on the Ground, and may step to the cell directly
  above/below. Driven onto the Sky or Underworld it is a *sitting duck*: its only
  move is to drop back to the cell directly below/above on the Ground. **No
  castling.**
- **Paladin (P)** — **King + Knight** on the Ground (**King** only on the Sky or
  Underworld), plus an unblockable **3-D Knight** move between boards (two cells
  one way then one perpendicular, using the level axis).
- **Warrior (W)** — a pawn without the double-step: pushes **one cell forward**
  (non-capturing), captures **one cell diagonally forward**. On the enemy back
  rank it **promotes to a Hero** (the only promotion). Restricted to the Ground.

### Underworld

- **Basilisk (B)** — moves/captures **one cell directly or diagonally forward**
  and may move (not capture) **one cell straight back**; confined to the
  Underworld. It **freezes** any *opposing* piece on the cell **directly above**
  it on the Ground (see below).
- **Elemental (E)** — on the Underworld, **one or two cells orthogonally** (no
  leaping) plus a non-capturing **one cell diagonally**. It may step to the
  **Ground** by moving one cell orthogonally (the intermediate Underworld cell
  must be empty) then one cell up, and returns to the Underworld by moving one
  cell down (intermediate must be empty) then one cell orthogonally.
  **[ruling]** Gygax's text calls the Ground step a "capturing move" but his own
  diagram marks those cells `x` (move **or** capture); this package follows the
  diagram — the board-change is **move-or-capture** in both directions.
- **Dwarf (D)** — on the Underworld or Ground: captures **one cell diagonally
  forward**, or moves (non-capturing) **one cell forward or sideways**. It climbs
  **Underworld→Ground** only by **capturing** the cell directly above, and drops
  **Ground→Underworld** only with a **non-capturing** move to the cell directly
  below. It never reaches the Sky and never moves backward (Gygax's original;
  Sean Shubin's optional "Dwarf may reverse at the far edge" house rule is **not**
  implemented).

## Freezing (the Basilisk)

Freezing is **automatic and continuous**: whenever an opposing piece stands on
the Ground cell directly above a Basilisk — whether the piece moved there or the
Basilisk moved under it — that piece is **frozen** and **cannot move**. It thaws
the instant the Basilisk moves away or is captured. **[ruling]** Gygax says only
that a frozen piece "cannot move" and "regains its normal powers" on thaw; this
package reads *powers* literally — a **frozen piece exerts no power** (it neither
moves nor gives check nor defends), but it still **occupies its square** (it
blocks sliders and can be captured). A Basilisk freezes only *enemy* pieces, and
a King can itself be frozen (and thereby unable to escape check).

## Winning, check and draws

The **King is royal**: you may never leave your own King attacked, a piece
capturing the enemy King from afar (Dragon) or on any board delivers check just
as a normal capture would, and **checkmate wins**. A King with no legal move that
is **not** in check is **stalemate = an honest draw**. The game is also drawn by
**threefold repetition**, by 50 full moves with no capture and no Warrior move,
or at a hard ply cap (termination guarantee — Gygax notes real games "can be long
and slow").

## Correctness anchors (see `selftest.py`)

No engine oracle exists for Dragonchess, so this package is anchored by:

- **Opening perft**, hand-derived piece-by-piece and asserted: **perft(1) = 90**
  for Gold's first move. It breaks down as Griffins 3+2, Dragon 13 (incl. the
  a7/…-Sylph capture CVP notes), Sylphs 11, Unicorns 4, Heroes 8, Cleric 2, Mage
  2, Paladin 8, Warriors 12, Basilisks 2, Elemental 6, Dwarves 17 — with the
  Oliphants, Thieves and King boxed in for 0. Deeper (frozen) counts:
  **perft(2) = 8094**, **perft(3) = 736740** (the latter a one-time check, too
  slow for the standard selftest).
- A **fast reverse-attack scan** verified **identical to a forward reference**
  over thousands of (cell, side) queries across random games — this is the check
  detector, so it is cross-validated rather than trusted.
- **Exact destination sets** for every piece type from representative cells
  (matching Gygax's diagrams), including inter-level moves and the Dragon's
  capture-from-afar.
- **Rule positions:** Basilisk freeze/thaw and the enemy-only rule; Sylph
  return-home; Warrior→Hero promotion; a constructed checkmate and a constructed
  stalemate.
