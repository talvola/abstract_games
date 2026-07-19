# Mattock

By Drew Edwards (2020; formerly *Las Médulas*). Rules as implemented, from the
designer's article in *Abstract Games* magazine #21 (pp. 14-20), cross-checked
against the Mindsports (Dagaz) implementation.

Two players — **Red** and **Blue** — mine a labyrinth of neutral **tiles**
(corridors) through the rock of a hexhex board. Each player's **miners** stand
on tiles and walk the corridors. **If you cannot mine on your turn, you lose.**

## Board and setup

- **Full game** (default): hexhex-7 board (127 spaces), 6 miners each.
- **Short game**: hexhex-5 board (61 spaces), 3 miners each.
- **Fixed setup** (default): one tile with a miner on it on each of the
  positions from the magazine's setup diagram (centrally symmetric).
  Red moves first.
- **Freestyle setup** (option): players alternate placing one tile plus one of
  their miners on any space **not adjacent to any earlier placement** (Blue
  places first). The player who places last takes the first turn — with
  alternating placement that is Red, so Red still moves first.

## The collapse rule

A newly mined tile may not:

- touch **more than three** other tiles, nor
- touch a tile which **already touches three** other tiles.

(A miner's tile counts as a tile. Consequently no tile ever touches more than
three tiles.)

## Connections

Tiles occupied by a miner **block** paths for everyone else: a corridor runs
through tiles that are free of miners. Something is *connected to* a miner if
it is adjacent to that miner's tile or joined to it by a chain of miner-free
tiles.

## Your turn — three steps in order

1. **Mine** (mandatory). Place one tile on an empty space that is adjacent to,
   or connected by miner-free tiles to, at least one of **your** miners
   (opponent's miners block connections; your own miners are themselves
   connection endpoints). The placement must obey the collapse rule. If any of
   your miners were removed on previous turns, one of them is placed onto the
   new tile automatically. **If you cannot mine, you lose the game.**
2. **Move** (optional). Move one of your miners any distance through connected
   tiles to a miner-free tile. You may pass **through** your own miners;
   opponent's miners block your path. Choose *End turn* to skip.
3. **Remove** (automatic). Every **opponent** miner that is now both
   - **not** connected to another of its own miners, **and**
   - connected to **two or more** of your miners
   is removed from the board and returned to its owner, who will re-place one
   per turn via step 1 (its tile stays). All removals are evaluated
   simultaneously. Two adjacent miners of the same colour are immune.

The game always ends with a winner: mining is mandatory and fills the board
monotonically, until one player has no legal placement left.

## Move input

- Setup / mine: click an empty space (move string `q,r`).
- Move: click your miner, then a destination tile (`q,r>q',r'`), or press
  **End turn (no move)** (`pass`).

## Notes on this implementation

- The physical set's tile supply (90 / 45) is treated as unlimited, following
  the Mindsports implementation; the collapse rule keeps the number of placed
  tiles well below the space count anyway.
- The hex-5 fixed setup equals the inner marked cells of the magazine's
  diagram and matches the Mindsports *base5* setup up to board symmetry.
