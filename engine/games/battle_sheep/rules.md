# Battle Sheep

*Designer: Francesco Rotta. Publisher: Blue Orange Games. The "Splitter" mechanism: spread your flock to claim the most pasture.*

This package implements the **2-player** game with a **fixed board** (see the note below). Rules here are *as implemented*.

## Components

- A hex **pasture** of 32 hexes.
- Each player has **16 sheep**, starting as one tall stack (a tower).
- Player 0 = **Orange**, player 1 = **Blue**.

## The board (a FIXED choice — flagged)

The physical game builds the pasture from **4-hex tiles**: each player contributes 4 tiles of 4 hexes, so a 2-player game uses **8 tiles = 32 hexes**, and players take turns placing tiles to shape the field (it must stay connected; holes are allowed).

**This package does NOT model tile placement.** It bakes in one fixed, symmetric 32-hex arrangement:

- An **8-wide × 4-row axial parallelogram**: hexes `q,r` with `q` in `0..7` and `r` in `0..3`.
- It is fully connected and has **180° rotational symmetry** about its centre, so the two fixed starting corners are mirror images and the opening is balanced.

This is a deliberate, documented simplification; the real game's board varies with how the tiles are laid.

## Setup (also fixed)

Each player's tower of 16 sheep starts on a **perimeter hex**. We fix:

- **Orange** starts on corner `0,0`.
- **Blue** starts on the opposite corner `7,3`.

These are mirror-symmetric perimeter corners.

## Your turn — split and slide

On your turn you must, if able:

1. Pick **one of your stacks of height ≥ 2** (a height-1 stack cannot move).
2. **Split** it: leave **at least one** sheep behind and take the rest off the **top** — any number from `1` to `height − 1`.
3. **Slide** the taken group in **one of the six straight hex directions**, moving it **as far as it can go**: it travels in a straight line and stops on the **last empty hex** before it would hit the board edge or any occupied hex.
   - The group **must move at least one hex** (a direction whose first step is blocked is not a legal move).

There are **no captures** — sheep never leave the board and stacks never merge with an enemy.

If you cannot move any stack, you are **skipped** (a pass). Play continues until **neither** player can move.

Move notation: `from>to=count`, e.g. `0,0>0,3=5` slides 5 sheep from `0,0` to `3` (the far hex reached). `pass` when you have no move.

## End and scoring

The game ends when **no player can make any move**. Each move slides sheep onto a previously empty hex, so the occupied-hex count strictly increases — the game always terminates.

- **Winner = the player occupying the MOST hexes** (count distinct hexes where your sheep sit; the size of each stack does not matter for this count).
- **Tie-break:** if both occupy the same number of hexes, the winner is the one with the **largest single connected herd** — the biggest group of your own hexes connected to each other by a shared side.
- If those are also equal, the game is a **draw**.

## Implementation notes / choices

- **Fixed 32-hex board** (8 tiles of 4) instead of tile-laying — flagged above.
- **Fixed starting corners** (`0,0` / `7,3`) instead of free perimeter placement.
- Tie-break uses the official rulebook's "largest contiguous herd" rule (verified against the published rules).
- Stacks render as owner-coloured **towers** with a height badge equal to the number of sheep on that hex.
