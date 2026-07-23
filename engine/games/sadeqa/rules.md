# Sadéqa

**Sadéqa** is a traditional two-row *mancala* (sowing game) of the **Selus**
family, played by the **Jimma** people of western Ethiopia. It was recorded by
Richard Pankhurst as *"Sadeqa V"* (Game 84) — a popular pastime at the court of
Abba Jifar, where the king owned wooden boards called *bolo sadéqa*. This
implementation follows the rules written up by **Ralf Gering** in *Abstract
Games* magazine, **issue 16 (Winter 2003)**. Sadéqa is described there as *"almost
identical to Sulus Nishtaw, except that it is played on a two-row board with 20
holes and four seeds in each hole initially."*

## Board and setup

- **20 holes** in **two rows of ten**. Each player owns the row nearest him.
- **Player 0 = South** (bottom row), **Player 1 = North** (top row).
- Every hole starts with **4 seeds** (*lon*) — **80 seeds** in all.
- There are **no store pits**; captured seeds are simply tallied.

Hole numbering (from the article's notation figure): South's holes are numbered
**1..10 left-to-right**, North's holes **10..1 left-to-right** (so each player's
own holes run 1..10 from his own left hand).

## Sowing (counter-clockwise, multi-lap)

A move begins by lifting the **entire contents** of one of your own holes that is
**not a warana**, then dropping the seeds **one per hole, counter-clockwise**,
into the following holes. The counter-clockwise ring is fixed:

> South 1 → 2 → … → 10 (along the bottom), up the right edge to North 1, then
> North 1 → 2 → … → 10 (back along the top), down the left edge to South 1.

Seeds are dropped into **every** following hole, including warana (which simply
accumulate them).

**Multi-lap relay.** If the last seed lands in an **occupied, non-warana** hole,
you take up that hole's whole contents (including the seed you just dropped) and
sow another lap. You keep relaying until the last seed finishes in one of the
terminal cases below.

## What ends a move

The move ends when the last seed of a lap lands in:

1. **An empty hole** — *kwah*. Nothing is captured.
2. **An opponent's hole holding exactly three seeds** (now four) — a **new
   warana** is *speared* (*wagika*), owned by the mover, on the opponent's side.
   The four seeds stay in that hole. Nothing is captured. The move ends.
3. **A warana:**
   - **Owned by the opponent** — you **capture**: the seed you dropped **plus one
     more** seed from that warana (only the **single** dropped seed if the warana
     was empty beforehand). The warana keeps its remaining seeds. You then make a
     **bonus move** (*belu'eka sini*, "escorting"), starting again from any of
     your own non-warana holes.
   - **Owned by you** — nothing is captured and the move ends.

A **warana** ("speared"; the same object the shared *Selus* rules call a *wegue*,
"wound") is a marked hole owned by whoever created it. The renderer tints warana
holes with the **owner's seat colour**.

### Interpretations pinned to the source (in priority order: Sadéqa text → Sulus Nishtaw → shared Basic Rules)

- **Counter-clockwise ring** — derived from the notation figure so that each
  player's own holes are sown in increasing order (1→10) before crossing to the
  opponent; this is the unique ring consistent with both rows' printed numbering.
- **A warana can only be made on the opponent's side** (Sulus Nishtaw). If the
  last seed makes a hole on **your own** side reach four, that is **not** a
  warana — **all four seeds are re-lifted and sown in a new lap** (the relay
  continues). Any other occupied non-warana landing also relays.
- **First-move exception** (shared Basic Rules): on the **very first move of the
  game** a hole reaching four never creates a warana — it relays instead. (After
  the opening this restriction is gone.)
- **Starting a move from a warana is forbidden** — you may only start from a
  non-warana hole in your own row. (Every warana in your row is one your opponent
  speared, since warana are made only on the opponent's side.)

## Passing, and the end of the game

- **Passing is illegal while you have a legal move.** A player who has **no**
  legal move is **skipped** — the other player continues (this includes the case
  where you capture but then have no legal bonus move: the turn simply passes).
- **The game ends when neither player has a legal move** — i.e. all remaining
  seeds are locked inside warana (or holes are empty). As anti-loop backstops the
  engine also ends the game after a long run of moves with no capture and no new
  warana, or at a hard ply cap; in every case the result is decided purely by the
  score actually on the board — never a fabricated winner.

## Scoring

Each player's score = **seeds he has captured** + **seeds sitting in warana he
owns** at the end of the game. **Most points wins.** An **equal split is an
honest draw** (an early symmetric line can genuinely tie).

## Notes on this implementation / verification

- Move notation: a move is the source hole's cell id `"col,row"`. A bonus move is
  just the same player's next move (the engine keeps the turn with that player).
- **No printed numeric solution exists for Sadéqa in issue 16** — the two
  "capture as many as possible" problems on that page are for the 3×6 games
  *Selus (Massawa)* and *Sulus Nishtaw*, not Sadéqa. The correctness anchor is
  therefore: the exact starting position, hand-checked unit cases for every rule
  branch (warana creation, own-hole relay, capture + bonus, empty-warana capture,
  own-warana landing, the first-move gate, an honest 2–2 draw), and a **frozen
  maximum-capture** value.
- **Frozen max-capture anchor:** on a constructed position with three
  North-owned warana of three seeds each in South's row (at South holes 3, 6 and
  9), each fed by a single seed, South can spear all three via successive bonus
  moves for **6** captured seeds in one turn. (A single sowing move captures at
  most 2 — landing in a warana ends the move — so larger totals only arise across
  the bonus chain.) See `selftest.py`.

*Attribution: Jimma people (western Ethiopia); recorded by R. Pankhurst (1971);
this ruleset by Ralf Gering, Abstract Games issue 16 (Winter 2003).*
