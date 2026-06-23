# Dara (Dakon / Doki / Derrah)

Dara is a traditional two-player game of the West African "running-three"
family, played by the Dakarkari, Hausa and other peoples of Niger and northern
Nigeria. The goal is to keep forming rows of **exactly three** of your own
pieces, each of which lets you take one enemy piece, until your opponent can no
longer make a three.

## Board and pieces

- **Board:** a rectangular grid of empty cells. The standard size is
  **6 columns × 5 rows = 30 cells** (the size used here by default). The option
  selector also offers 6×6 and 7×6, both of which appear in the literature.
- **Pieces:** each player has **12 pieces**. White moves first.
- Cells are addressed `"col,row"` with column `0..W-1` and row `0..H-1`.

## Phase 1 — Placement ("the drop")

Players alternately drop **one piece per turn** on any empty cell until all 24
pieces are on the board.

- **Three-in-a-rows formed during the drop do NOT count** — you may make a row
  of three while dropping, but you do **not** capture for it (capturing only
  happens in the movement phase).
- **Forming a line of four or more of your own pieces is illegal at all times,
  including during the drop.** Such a placement is simply not offered as a legal
  move.

## Phase 2 — Movement

Once all pieces are placed, players alternate **sliding one of their pieces one
step orthogonally** (up/down/left/right) into an adjacent **empty** cell. There
are no diagonal moves and no jumps.

- If the slide forms a **new orthogonal line of EXACTLY THREE** of the mover's
  pieces, the mover **removes one enemy piece**:
  - The captured piece must **not itself be part of an enemy three** (a piece
    standing in an enemy three is protected). If *every* enemy piece is in a
    three, any enemy piece may be taken.
  - **A line of four or more does NOT capture**, and a move that would create a
    line of four or more is **illegal** (not offered).
  - If a single move completes **more than one** three, the mover still removes
    only **one** enemy piece.

### Anti-shuffle rule

To stop a player from oscillating one piece to re-score the same three forever:

1. A three only scores if the **piece that just moved came from outside that
   line** — sliding a piece out of a three and straight back into the same
   three does not re-score it.
2. In addition, a move may **not re-score the exact same three** that the same
   player scored on their immediately preceding scoring move.

A hard no-progress cap (60 movement plies with no capture) ends the game in a
**draw**, guaranteeing termination.

## Winning

A player **loses** when they can no longer form a three with their remaining
pieces — in practice when they are **reduced below three pieces** — or when they
have **no legal move** on their turn. The opponent then wins. If the no-progress
cap is reached first, the game is a draw.

## Documented ruleset choices / flags

- **Board size:** sources disagree (Wikipedia gives 5×6; other references cite
  6×6 or 7×6). This package defaults to the Wikipedia **6×5 = 30 cells** and
  exposes the others as an option. *(FLAGGED: size is genuinely ambiguous across
  sources.)*
- **Placement three:** implemented as *"allowed but never captures"* (the
  Wikipedia rule), rather than *"forbidden"*. Forming a **four** is forbidden in
  both phases.
- **Anti-shuffle:** the running-three family needs an anti-oscillation rule, but
  no single canonical wording exists in the sources. We use the two-part rule
  above (moved piece must enter the three from outside it; cannot immediately
  re-score the identical three). *(FLAGGED: the exact anti-shuffle wording is a
  documented interpretation, not a universally agreed rule.)*
- **Win threshold:** "can no longer make a three" is implemented as *fewer than
  three pieces on the board, or no legal move* — the standard formulation.
