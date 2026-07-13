# Rive

**Designer:** Mark Steere (December 2010). Rules as implemented here follow the
designer's one-page rule sheet (see *Official source* link) — Figures 1–3d.

Rive is a hexagonal placement-and-capture game. The board is an **odd-celled
hexagonal (hexhex) board** that starts **empty**. Two players, **Black** (moves
first) and **White**, alternate placing stones. You **cannot pass**. Because the
board has an odd number of cells, a full board can never tie — **draws cannot
occur**.

**Object:** own the **majority of stones** on the **filled** board.

This implementation uses the **side-3** board (19 cells, the size used in the
rule-sheet figures). Every hexhex has an odd cell count, so the majority is
always decided.

> *Board size (implementation note).* Rive can be played on any odd-sized hexhex,
> but on larger boards a single capturing placement can join large groups and so
> offer **thousands** of distinct non-splitting removal sets — each a separate
> legal move. That combinatorial blow-up makes automated move generation (the
> bot and the click-to-remove UI) impractically slow on side 5+ (a single legal-
> move enumeration can take tens of seconds), so only the canonical side-3 board
> is offered here. Side 5/7 could be re-enabled if removal-set enumeration is
> ever bounded.

## Groups

A **group** is a maximal connected clump of stones — of **both colours**. Two
adjacent stones belong to the same group regardless of colour (Fig 2). Adjacency
is the six hex neighbours.

## Placing a stone

1. **Isolation is mandatory.** If any empty cell is adjacent to **no** group,
   you **must** place on such a cell (a plain, non-capturing placement). Fig 1
   marks exactly the isolated cells.
2. **Otherwise minimise the largest group you touch.** Among all empty cells,
   you must place on one that makes the **largest group your stone touches as
   small as possible**. Every empty cell achieving that minimum is legal —
   whether it touches one group, two, or three. It is illegal to touch a bigger
   group than necessary (Fig 3a: you may not touch the size-3 group while a cell
   touching only size-2 groups exists).

   *Geometry note:* on a hexhex a stone can touch **at most three** distinct
   groups (the six neighbours form a ring in which no more than three are
   mutually non-adjacent) — exactly the rule sheet's "up to three groups".

## Capturing placements

If your placed stone connects **two or three** groups, you **must remove stones**
from the newly-combined group — of **either or both colours** — to bring it down
to **exactly one larger than the largest** of the groups that were combined. The
removal **must not split** the group: the survivors must remain a **single
connected component**.

- **Fig 3b:** White joins two size-2 groups; White removes 2 stones, leaving a
  connected group of size 3 (2 + 1).
- **Fig 3d:** Black joins two size-3 groups; Black removes 3 stones, leaving a
  connected group of size 4 (3 + 1).

You **choose** which stones to remove, so each valid non-splitting removal is a
distinct legal move.

### Multiple placements per turn

A **capturing** placement does **not** end your turn — you **must place again**,
and keep placing until you make a **non-capturing** placement, which ends your
turn (Figs 3c/3d). (The engine keeps the same player to move across a capturing
placement.)

## Winning

The game ends when the **board is full**. Whoever has **more stones** wins. The
odd cell count guarantees this is never a tie.

## Move notation

Moves are `>`-separated cell paths (axial `q,r` cell ids):

- **Non-capturing placement:** `q,r` — a single cell (one click).
- **Capturing placement:** `q,r>a,b>c,d…` — the placement cell first, then the
  removed cells (in a canonical order). The clickable removals let you pick the
  stones to take off; one legal move per distinct removal set.

## Interpretations / notes (this implementation)

- **The just-placed stone is never itself removed** — removals come only from the
  pre-existing stones of the combined group. A valid removal always exists (keep
  the largest joined group plus your placed stone and remove the rest), so a
  capturing placement is never a dead end.
- **Draws don't occur in real Rive.** But captures can un-fill cells, so the board
  is not strictly monotonic; a generous hard **ply-cap draw** is kept purely as an
  anti-loop backstop for the platform's termination guarantee. It is not reached
  in normal play (random self-play fills the board every game), and on the cap the
  result is an **honest draw**, never a fabricated winner.
