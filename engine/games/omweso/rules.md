# Omweso

Omweso is the traditional **four-row Mancala** of Uganda (the national game of
the Baganda). It is a "sow-and-capture" game, but unlike two-row Mancalas
(Oware, Kalah) it has **no stores** — captured seeds are re-sown back onto the
board, so the number of seeds on the board is a constant **64** for the whole
game. You do not win by *collecting* seeds; you win when your opponent can no
longer make a legal move.

This page documents the rules **exactly as implemented** in this package. Omweso
has regional variation; where sources differ or a rule is simplified, that is
stated below.

## Board & setup

- An **8 × 4** board of 32 **pits**. Each player owns the **two rows nearest
  them** (16 pits).
  - **Player 0 = South** owns the bottom two rows: **row 0 = outer** (closest to
    South) and **row 1 = inner** (adjacent to the opponent).
  - **Player 1 = North** owns the top two rows: **row 3 = outer** and
    **row 2 = inner**.
- Columns 0..7 line up vertically across all four rows. The two **inner rows**
  (row 1 and row 2) face each other in the middle; the capture rule works by
  **column alignment**.
- **Starting position:** **4 seeds in each of the 8 pits closest to a player**
  (that player's **outer row**); the inner rows start **empty**. That is 32
  seeds per side, **64 total**. This is the standard "checking" opening
  (notation `4i-p; 4I-P`).
- Each pit's seed count is shown as the cell's label. There are no stores.

## Sowing (a move)

On your turn you pick one of **your own pits that holds at least 2 seeds**, lift
**all** its seeds, and **sow** them one per pit, counterclockwise, **around your
own two rows only** — you never sow into the opponent's rows.

South's fixed sowing circuit is:

```
inner row, left  -> right :  (0,1)(1,1)(2,1)(3,1)(4,1)(5,1)(6,1)(7,1)
outer row, right -> left  :  (7,0)(6,0)(5,0)(4,0)(3,0)(2,0)(1,0)(0,0)  -> wraps to (0,1)
```

North's circuit is the 180° mirror of South's (inner row right→left, then outer
row left→right, wrapping around).

## Relay (lap sowing)

The signature Mancala relay rule: if your **last seed lands in an occupied pit**
(one that already held seeds), you immediately **pick up that whole pit** and
**keep sowing** in the same direction. You relay over and over until the last
seed finally lands in an **empty pit**, at which point your turn ends.

## Capturing

A capture happens when the last seed of a lap lands in an **occupied pit in your
INNER row** (row 1 for South, row 2 for North) **and both of the opponent's pits
in that same column are occupied**. When that happens:

- You **capture** all the seeds from **both** opposing pits (the opponent's inner
  and outer pit in that column) — those two pits are emptied.
- The captured seeds are **immediately re-sown**, starting from **the pit where
  the capturing lap began** (i.e. they are dropped one per pit, continuing
  counterclockwise from that pit). This re-sow is itself a lap: it can relay
  again, or trigger another capture, following all the rules above.

Captured seeds therefore stay in play — they move from the opponent's side onto
**your** side. If the last seed lands in an occupied inner pit but the opposing
column is **not** both occupied, no capture occurs and the pit simply **relays**
like any other occupied pit. Landing in your own **outer** row never captures.

## Ending & winning

- The game ends when the **player to move cannot make a legal move** — i.e. none
  of their 16 pits holds 2 or more seeds. That player **loses**; their opponent
  (the last player able to move) **wins**. Because a player can only ever add
  seeds to their *own* rows (or remove the opponent's via capture), a "starved"
  opponent stays starved.
- A **hard ply cap** (500 plies) is a platform-friendly anti-loop safety net; if
  it is somehow reached with both sides still mobile, the game is scored a
  **draw**. In normal play it is never reached.

## Documented simplifications (vs. some traditional rules)

Omweso has an elaborate traditional layer that this package intentionally omits
in favor of a clean, well-defined core:

- **Free opening arrangement (*okwakya*).** Traditionally each player may secretly
  arrange their own 32 seeds across their 16 pits before play. This package uses
  the fixed standard checking position (4 in each outer pit) instead.
- **Reverse (clockwise) capturing (*emitwe*).** Some rulesets let a player sow
  *clockwise* from their four leftmost pits when doing so captures. This package
  uses a **single fixed counterclockwise direction** (so a move is just the pit
  you sow from — no direction choice), which is the common simplified ruleset.
- **Special alternate wins** (e.g. capturing at both ends of the board in one
  turn, or capturing before the opponent captures at all) are not modeled;
  winning is strictly by leaving the opponent unable to move.

## Notes on variants

The four-row board, own-side-only counterclockwise sowing, the relay rule, the
inner-row column capture with re-sowing of the loot, and loss-by-no-legal-move
are the core of Omweso as described by Wikipedia and the mancala references. The
free arrangement and reverse-capture rules above are the main traditional
additions left out here.
