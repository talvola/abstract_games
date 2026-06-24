# Pallanguzhi

**Pallanguzhi** (Pallankuzhi, பல்லாங்குழி) is a traditional South Indian / Tamil
two-row **mancala** (sowing) game for two players. This package implements the
**standard single-round "cow / kashi" variant** — the most widely documented
ruleset across general references — and is described exactly *as implemented*
below.

## Board

- Two rows of **seven pits** (*kuzhi*) each — **14 pits** total.
- You own the **seven pits in your own row**. The bottom row is Player 1
  (Bottom); the top row is Player 2 (Top).
- Each player keeps captured seeds (cowrie shells / counters) in their own
  **store** (shown in the caption — it is not a board pit and is never sown into).
- Start: **6 seeds in every pit** = **84 seeds** total.

## Sowing

- On your turn, lift **all** the seeds from one of **your own non-empty pits**
  and sow them one per pit, moving **counterclockwise** around the whole loop
  (along your own row, then crossing onto the opponent's row, wrapping around).
- **Lap / relay:** when you drop the **last seed of the handful**, look at the
  **next** pit:
  - if it is **non-empty**, scoop up all of its seeds and **keep sowing** (a new
    lap) — your turn continues;
  - if it is **empty**, your turn **ends** (see capture below).

## Capture

Two ways to capture, both signatures of this variant:

1. **Kashi / cow (capture at four).** The **instant** a seed is dropped into a
   pit and that pit thereby holds **exactly four** seeds, you immediately capture
   all four into your store (they leave the board). This applies to **any** pit
   reached while sowing — your own or your opponent's.
2. **Empty-pit ending.** When your last seed lands and the **next** pit is
   **empty**, your turn ends and you capture all the seeds in the pit **beyond**
   the empty pit (the next-next pit), if it holds any. If that pit is also empty,
   you capture nothing. (So two empty pits ahead of you captures nothing.)

## End of the round and winning

- The round **ends** when the player to move has **no non-empty pit on their own
  row** to sow from (they cannot move).
- All seeds still loose on the board are then **swept** to the player on whose own
  row they sit and added to that player's store.
- The player with **more seeds** wins. Equal totals (42–42) is a **draw**.

A hard ply cap acts as an anti-loop safeguard, but with the capture-at-four rule
steadily draining seeds and every lap forced to stop at an empty next-pit,
ordinary games end long before it.

## Documented choices and interpretations

- **Variant chosen: standard single-round "cow" Pallanguzhi.** Counting captures
  at **four** seeds (the *kashi* / cow / *pasu* of the common 2×7, six-per-pit
  game), the empty-next-pit ending capturing the pit *beyond* the empty one, and
  scoring a **single round** by most seeds. This is the cleanest faithful version
  and the one most consistently described across general sources.
- **Not implemented (documented alternatives):**
  - The **Wikipedia "148-counter / pasu-six"** layout (12 per pit except two
    middle pits of 2, with capture at **six**) and its full **multi-round**
    game with "rubbish holes" (dead pits). We implement a single round at 6 per
    pit / capture-at-four instead, which is the most common tabletop ruleset.
  - The optional **"facing pit"** capture (some versions also take the directly
    opposite pit on the empty-pit capture). We take only the pit *beyond the empty
    pit*, matching Wikipedia's core wording.
- **Start count:** sources list 4–12 seeds per pit (5 and 6 most common). We use
  **6** (84 total), the common standard.

## Sources

- Wikipedia, "Pallanguzhi".
- Mancala World (Fandom), "Pallankuzhi".
- imp-art.org, "Pallanguzhi".
- pallanguzhiguide.com rules guide.
