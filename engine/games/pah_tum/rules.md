# Pah Tum

**Pah Tum** (also *Pa Tum*) is an ancient Near-Eastern / Assyrian grid game,
described in R. C. Bell's *Board and Table Games from Many Civilizations*. It is a
pure positional placement game: fill the board, then score your longest rows.

## Board

A **7x7** grid of 49 cells (coordinates `col,row`, 0-based). A **9x9** option is
also offered.

A fixed, symmetric set of cells is **blocked** (shown shaded). Blocked cells never
hold a stone and break any row/column run that passes through them.

- **Diamond** (default): the four diagonal neighbours of the centre — on 7x7 these
  are `2,2`, `4,2`, `2,4`, `4,4`.
- **Cross**: the four orthogonal neighbours of the centre — `3,2`, `2,3`, `4,3`,
  `3,4`.

Both layouts have **4** blocked cells (an even number, symmetric under reflection
and 180° rotation), leaving **45** playable cells on 7x7. Player 1 (Red) therefore
places 23 stones and Player 2 (Blue) places 22.

### Ruleset choice — fixed blocked layout

Historical descriptions vary: the board starts empty and an **odd** number of
"boulders" (commonly **5**, beginning with one in the centre) are placed
*alternately by the players* as the opening phase. To keep this implementation
fully **deterministic** from the first move (no random / negotiated boulder
phase), we instead use a **fixed, symmetric, even** preset of blocked cells, as
the task specifies. This is a documented simplification of the boulder-placement
phase, not a change to the placement-and-scoring core of the game.

## Play

Players alternately place **one stone of their colour** on any **empty,
non-blocked** cell. Red moves first. There is no movement, capture, or removal —
stones stay where placed. Play continues until **every playable cell is filled**.

## Scoring

When the board is full, each player scores every **maximal run of 3 or more
consecutive same-colour stones** in a **row or column**. **Diagonals never score.**
A "maximal" run is one not extendable at either end (a longer run is *not* also
counted as its shorter sub-runs — only the full length scores).

| Run length | Points |
|-----------:|-------:|
| 1 or 2     |   0    |
| 3          |   3    |
| 4          |  10    |
| 5          |  25    |
| 6          |  56    |
| 7          |  88    |

The player with the **higher total wins**; **equal totals are a draw**.

### Ruleset choice — scoring table

The table above (3→3, 4→10, 5→25, 6→56, 7→88) is the de-facto standard cited
across game references and is the one implemented here. Prose descriptions of a
"recursive" formula (each length = its pieces plus a per-piece bonus plus the two
shorter strings) are approximate and do **not** reproduce the published 88 at
length 7; some online implementations (e.g. BrainKing) instead list 7→119. We
follow the standard fixed table. On the 7x7 board the maximum possible run is 7,
so the table is exhaustive there; on the 9x9 option, runs of 8–9 extend the
table's escalation (strictly increasing, super-linear) — these are off the
standard table and are flagged as an implementation extension.

## Result

Most points wins. Equal points is a draw. The winner is fixed (stored in state) at
the moment the board fills — a "win as an event" game.
