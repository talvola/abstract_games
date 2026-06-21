# Oware (Awari / Awalé)

Oware is the canonical two-rank **Mancala** sowing-and-capturing game. This page
documents the rules **exactly as implemented** in this package. Oware has many
regional variants; where sources differ, the choice made here is stated.

## Board & setup

- A **6 × 2** board of 12 **pits**, plus a **store** (granary) for each player
  holding captured seeds.
- **Player 0 = South** owns the **bottom row** (row 0, columns 0..5).
  **Player 1 = North** owns the **top row** (row 1, columns 0..5).
- Each pit starts with **4 seeds** → **48 seeds** total.
- Each pit's seed count is shown as the cell's label. The two stores are shown
  in the caption: `South 0 — North 0`. **Stores are never sown into.**

## Sowing (a move)

On your turn you pick one of **your own non-empty pits** (a single cell `col,row`
on your row), lift **all** its seeds, and **sow** them one per pit, **counter-
clockwise**, into successive pits.

The fixed counterclockwise pit cycle is:

```
South row, left → right :  (0,0)(1,0)(2,0)(3,0)(4,0)(5,0)
North row, right → left :  (5,1)(4,1)(3,1)(2,1)(1,1)(0,1)  → wraps to (0,0)
```

- The two **stores are skipped** (they are not in the cycle).
- **12+ seed lap:** if a sowing wraps all the way around (12 or more seeds), the
  **originating pit is skipped** and left empty on that pass. Only the starting
  pit is skipped — all other pits are sown normally.

## Capturing

After sowing, look at the pit where the **last seed** landed:

- If that pit is in the **opponent's row** and now holds **exactly 2 or 3**
  seeds, you **capture** those seeds into your store.
- Then check the **immediately preceding** pit (one step backwards along the
  sowing cycle). If it is **still in the opponent's row** and also holds **2 or
  3**, capture it too. Continue back-propagating until the chain breaks (a pit
  not holding 2 or 3) or you leave the opponent's row.
- A last seed landing in **your own** row never captures.

## Grand-slam rule (documented choice)

This package uses the common **"Awari" convention**: a move whose captures would
take **all** of the opponent's remaining seeds is **legal and is played**, but it
**captures nothing** — the seeds stay on the board in the pits that would have
been captured. (Other variants forbid such a move outright; this package does not.)

## Starvation / feeding rule (documented choice)

You must not leave your opponent with no way to play:

- If, at the start of your turn, the **opponent has no seeds**, you **must** play
  a move that **gives them seeds** (sows at least one seed into their row), if any
  such move exists. Moves that fail to feed are illegal in that situation.
- If **no feeding move exists**, the game **ends**: each player **sweeps** all
  seeds remaining on their own side into their store, and the result is scored.

## Ending & winning

The game ends when any of the following occurs:

1. A player's store reaches **25 or more** seeds — an outright majority of the 48.
2. The player to move has an opponent with no seeds and **cannot feed** them — the
   board is swept (each side keeps its own remaining seeds).
3. A **hard ply cap** (400 plies) is reached — a safety net against endless
   shuffling cycles; remaining seeds are swept to their owners. (Real Oware uses a
   cycle/repetition rule; the ply cap is the platform-friendly stand-in and is
   effectively never reached in normal play.)

**Winner:** the player with **more seeds** in their store at the end. Equal seeds
(24–24) is a **draw**.

## Notes on variants

- Sowing direction, the 2/3 capture totals, the back-propagating multi-capture,
  the grand-slam "capture nothing" rule, and the must-feed rule are the most
  widely played Oware/Awari settings and are what this package implements.
- Capture thresholds other than 2-or-3, single-lap-only sowing, or "must capture
  if possible" obligations exist in other regional games and are **not** used here.
