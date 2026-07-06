# Permute

Invented by **Eric Silverman (2020)** — a strategy game inspired by twisty
puzzles like the Rubik's Cube. Rules as implemented here, per the designer's
writeup and the maintained ruleset on MindSports.

## Setup

- A square **9×9** board (13×13 optional). Every cell starts occupied: the
  stones form a two-colour **chequerboard**.
- Colour mapping: the source rules use **Orange** (moves first) and **Yellow**.
  Here **Red = Orange** (seat 1, moves first) and **Blue = Yellow** (seat 2).
  Blue holds the corner-parity cells, so on these odd boards Blue starts with
  the extra stone (41 vs 40 on 9×9) — the balance arrangement suggested in the
  original BGG discussion.

## Definitions

- **Face** — any 2×2 block of cells fully on the board.
- **Twist** — rotating all 4 stones of a face 90° clockwise or anticlockwise,
  like a face of a 2×2 Rubik's Cube.
- **Bandaged stone** — a stone marked **✕**; it can never be twisted again, so
  any face containing it is permanently locked.
- **Group** — same-coloured stones connected **orthogonally**. Bandaged stones
  count in groups like any other stone (bandaging only locks twisting).

## Play

1. Red moves first. **Pie rule:** after Red's first move, Blue may play
   **swap** to take over the opening side instead of making a normal move.
2. On your turn you must **twist one face** that:
   - contains **no bandaged stone**, and
   - is **not all one colour** (which also guarantees it contains at least one
     of your stones — so any twistable face is twistable by either player).
3. After the twist you **must bandage one of your own stones** in the
   just-twisted face. It is locked for the rest of the game.

To move in the UI: click the **bottom-left cell** of the face you want to
twist, then click **your stone** in that face that you want bandaged (its
current, pre-twist square), then pick **Clockwise / Anticlockwise**.

## End and scoring

The game ends when **no face can be twisted**. Compare each player's
**largest group**; if equal, the second-largest, then the third, and so on —
the first difference decides the winner (a side that runs out of groups counts
0 from there on). A tie all the way down is a draw; that is impossible on the
odd-sided boards offered here (the stone counts differ), and the game always
ends because every move permanently bandages one more stone.

## Implementation notes

- The designer's blog photo caption "taking away the bandaged pieces" refers to
  removing the bandage *markers* to read the final position; the formal rules
  define groups over all stones, which is what this implementation scores.
- Sources: the designer's rules post ("Permute: A Game About Twisting Things",
  drericsilverman.com, 2020) and the MindSports ruleset (linked as the official
  source), which agree on all points above.
