# Agon (Queen's Guard)

*Also known as Queen's Guards, Royal Guards. A traditional two-player game,
popular in Victorian England (commercial editions from 1842).*

This page documents the rules **as implemented** by this package. Where sources
disagree, the choice made here is noted as a **[ruleset choice]**.

## The board

A **hexagonal board of hexagons** (a "hexhex") with **6 cells per side = 91
hexagons**. Cells use axial coordinates `q,r` (cube third coordinate
`s = -q-r`); a cell is on the board when `max(|q|,|r|,|s|) ≤ 5`.

Cells are organised into concentric **rings** by distance from the centre:

- **Ring 0** — the single central hex, the **THRONE** (highlighted gold).
- **Ring 1** — the six hexes adjacent to the throne (the inner ring the guards
  must fill).
- …out to **Ring 5** — the **outer ring** of 30 hexes.

## Pieces and starting position

Each player has **7 pieces: 1 Queen + 6 Guards**, all starting on the **outer
ring**. The two players sit on opposite sides:

- The two **Queens** start on **opposite corners** of the hexagon
  (Red on `5,0`, Blue on `-5,0`).
- Each player's **six Guards** are spread symmetrically over their half of the
  outer ring. The layout is **180°-rotationally symmetric** (Blue's position is
  exactly Red's, rotated half a turn), so neither side has an advantage.

Concretely (Red): Queen `5,0`; Guards `5,-1`, `5,-3`, `5,-5`, `0,5`, `2,3`,
`4,1`. Blue is the point-reflection of this through the centre.

**[ruleset choice]** Historical Agon boards mark the exact starting hexes with
printed circles, and editions vary slightly. This package uses a clean,
fully symmetric outer-ring layout with the queens on opposing corners — faithful
to the standard "queens on opposite corners, guards on the outer ring" picture
that every source agrees on, while pinning down the precise hexes deterministically.

## Movement — inward or sideways only

On your turn you move **one** of your pieces **one step** to an **adjacent,
empty** hex, subject to the defining Agon constraint:

- You may move **inward** (to a hex one ring closer to the centre) or
  **sideways** (to a hex on the **same** ring).
- You may **never move outward** — never to a hex on a ring **farther** from the
  centre.
- Only the **Queen** may enter the **throne** (ring 0). A Guard may never stand
  on the throne.

## Capture — the custodial sandwich

Captures are **custodial**: immediately after a move, **any piece (Guard or
Queen) that is flanked between two enemy pieces along a straight line** — the two
enemies on directly opposite sides of it — is **captured**.

- Capture happens to the **moving player's enemy**: only the player who just
  moved can create a new sandwich, so you never capture yourself by moving into
  a gap between two enemies.
- A single move can capture **several** pieces at once.

**Captured pieces are NOT removed from the game** — they are lifted into their
owner's reserve ("hand") and must be **re-entered**:

- On each of your following turns, **before** you make a normal move, you **must
  rescue one captured piece** by placing it back on the board:
  - a **Guard** onto any vacant **outer-ring** hex of your choice;
  - the **Queen** onto any vacant hex **except** the throne.
- You rescue **only one piece per turn**, and you must rescue the **Queen first**
  if she is among your captured pieces. A rescue *is* that turn's action — you do
  not also move that turn.

**[ruleset choice]** Sources agree the captured piece returns to the outer ring
on the owner's *next* turn (it is relocated, not eliminated) and that the queen
is rescued first / placed anywhere but the centre. This package implements that
"rescue-then-resume" timing exactly.

## Winning

You **win** the instant your **Queen stands on the throne** *and* **all six
ring-1 hexes around her are occupied by your own Guards** — the queen enthroned
and fully guarded.

## The self-block forfeit (loss)

If your **six Guards fill all six ring-1 hexes** but your **Queen is NOT on the
throne**, you have walled your own queen out of the centre: you **forfeit** and
your opponent **wins**. This is the classic Agon trap — guard the throne only
*with* your queen on it.

## Draws / termination

Agon almost always ends decisively, but to guarantee the engine terminates a
**ply cap of 400** forces a **draw** if neither player has won by then. (No
historical draw value; this is a defensive cap only.)

## Move notation

- Normal move: `fq,fr>tq,tr` (click the piece, then its destination).
- Rescue: an action that places a hand piece onto a highlighted target hex
  (queen first, then guards).

## Sources

- *Agon (game)* — Wikipedia (board, movement, custodial capture, relocation,
  win, and the empty-throne forfeit).
- Double Helix / CSIRO, "Queen's Guard"; bead.game "Agon"; Board Game Guys
  "Queen's Guard (1842)" (starting position, rescue timing, queen-first rescue).
