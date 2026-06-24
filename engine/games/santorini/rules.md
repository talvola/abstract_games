# Santorini (base game)

**Designer:** Gordon Hamilton · **Publisher:** Roxley Games

A pure-abstract build-and-climb game on a 5×5 grid. This package implements the
**base game only** — *no god powers and no hero/Simple-God variants.*

## Board & pieces

- A **5×5** grid of spaces. Each space has a **building level 0–4**:
  - **0** = ground
  - **1 / 2 / 3** = building tiers
  - **4** = **dome** — caps the space; nothing may stand on it and nothing may
    be built on it ever again.
- Each space holds **at most one Worker**. A Worker may stand on a level-1/2/3
  building, but never on a dome.
- **2 players**, **Red** (player 0) and **Blue** (player 1), each with **2
  Workers** (4 Workers total). The two Workers of a colour are interchangeable.

## Setup — placement phase

Following the Roxley rulebook, the **Start Player places first**:

1. **Red** (the Start Player) places **both** of their Workers on any two
   unoccupied spaces.
2. **Blue** then places **both** of their Workers on any two unoccupied spaces.

In this app a placement move is a **single click on an empty space**. The seat
order of the four placements is therefore **Red, Red, Blue, Blue**. After all
four Workers are down, the play phase begins with **Red**.

## A turn (play phase) — MOVE, then BUILD

On your turn you choose **one** of your Workers and do both of the following
with that same Worker:

1. **MOVE** it to one of the up-to-8 adjacent spaces (orthogonal or diagonal).
   The destination must be **unoccupied** (no Worker, not a dome) and **at most
   one level higher** than the Worker's current space. You may step **up one
   level**, stay **level**, or step **down any number of levels**.
2. **BUILD** on one of the up-to-8 spaces adjacent to the Worker's **new**
   position. The build space must be **unoccupied** (no Worker — the space your
   Worker just vacated is allowed) and **not already a dome**. Building **raises
   that space's level by one**; building on a level-3 space places a **dome**
   (level 4).

A move is encoded as the path **`wfrom > wto > buildcell`** (three spaces:
source → destination → build space) — click your Worker, click where it moves,
then click where it builds.

## Winning

- **Climb to level 3 (primary win):** if you **move a Worker up onto a level-3
  building**, you **win immediately** — no build happens. A winning climb is
  encoded as the 2-space path **`wfrom > wto`** (no build space).
- **Opponent stuck:** if the player to move has **no legal move** — every
  Worker is either unable to move, or after every possible move cannot build —
  that player **loses** and the opponent wins.

## Draw safeguard (non-original)

Santorini cannot loop indefinitely in practice (domes accumulate and the board
fills, forcing a climb or a stuck loss). As a defensive engine safeguard **not
in the original rules**, a hard cap of **400 play-phase turns** ends the game in
a **draw**. Real games end via a climb or stuck win long before this.

## Notes / interpretations

- The "at most one level up" rule applies only to **climbing**: descending is
  unrestricted (you may drop from a level-3 building straight to the ground).
- A Worker's **vacated origin** is a legal build space (you have already moved
  off it).
- This implementation omits all **god powers**, the **hero** powers, and the
  **golden-fleece / advanced** variants — base game only.
