# Donuts

**Bruno Cathala** (Funforge, 2023 — first published/playtested as **INSERT**). A
tactical alignment game for **2 players**. These are the rules *as implemented in
this package*.

## The board (random, `has_randomness: true`)

The board is a **6×6 grid** assembled from **four 3×3 tiles** dropped in at
**random** — each tile is placed in one of the four quadrants and rotated a random
number of quarter-turns. Every one of the 36 squares carries a printed **line** in
one of four orientations:

- **horizontal** (`—`), **vertical** (`|`), **`/` diagonal**, or **`\` diagonal**.

The random layout is dealt in `initial_state` and the resulting per-cell line map
is **stored in the state** (the EinStein/Onitama pattern) — there is no chance
node, so the generic UI and bot need no special handling. Two different shuffles
give different boards.

> **Interpretation.** Text sources describe the board as "four 3×3 tiles arranged
> at random" with a "vertical, horizontal or diagonal" line per square, but do not
> publish the exact art on each physical tile. This package ships four faithful
> stand-in tile faces (a balanced mix of all four orientations) and assembles them
> with random placement **and rotation**. Only the *mechanic* — a randomly
> assembled V/H/D line map — affects play; the specific printed art does not.

## Donuts (rings)

Each player owns **15 double-sided donuts** (30 total). A donut shows the owning
player's colour; "flipping" a donut (see Insertion) turns it to the other colour.

## Playing a ring

On your turn you place one of your rings on an **empty** square.

**Forced direction.** The line printed on the square you *just* played dictates the
direction your **opponent** must play next: their ring must lie somewhere on the
straight **line through your ring** in that orientation (the whole row / column /
diagonal, not just the adjacent square). If **every** square on that line is
already occupied, your opponent is free to play on **any** empty square. The very
first move of the game may go anywhere.

## Insertion (capture / flip)

If your placement leaves a **run of your own rings** flanked, along any straight
line (row, column, or either diagonal), by exactly **one opponent ring on each
end**, those two **bracketing opponent rings flip to your colour**. The rulebook's
two illustrated cases are both instances of this single rule:

- **`O _ O`** — you drop your ring into a one-cell gap between two opponent rings
  → the two opponent rings flip (`X X X`).
- **`O X X _ O`** — you complete a bracket around a run of your own rings → the two
  end rings flip (`X X X X X`, which also wins).

Captures are resolved on every straight line at once, from the position right
after your ring lands. Only the opponent's *bracketing* rings flip — never the
rings in between (this is the opposite of Reversi). Flipping never returns donuts
to a supply; each player still places their own 15 over the game.

## Winning

You **win immediately** when you align **5 rings of your colour** in a row,
column, or diagonal — including a five-line created by a flip.

Because there are only 30 donuts on 36 squares, the board never fills completely.
When **all 30 donuts have been placed** with no five-line, the game ends and the
player with the **largest orthogonally connected group** of rings wins. If the two
largest groups are the **same size**, the game is an **honest draw**.

Termination is guaranteed: exactly one donut is placed per turn, so the game lasts
at most 30 turns.

## Rendering

The board is a plain 6×6 square grid. Each square's **line orientation** is drawn
as a short **overlay segment** in its printed direction (horizontal / vertical /
`/` / `\`). Rings render as **hollow donuts** in the owner's colour, so the line
mark reads through the donut hole. The last-played square is highlighted, and the
caption states the direction the player to move is forced into.

## Move notation

A move is just the placed cell id `"c,r"` (columns and rows 0–5). The
forced-direction constraint is computed by the engine from the last move and the
stored line map — no extra token is needed.
