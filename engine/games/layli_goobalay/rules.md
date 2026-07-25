# Layli Goobalay

**Layli Goobalay** ("exercise with circles"; also *Leelo Goobalay*, *Laylo
Goobalay*) is the Somali **multiple-lap mancala** — one of the two mancalas
played in Somalia, alongside *Bosh*. The board is a set of holes dug in the
ground and the balls are dry camel dung (*salo*).

> *Layli Goobalay / Nin grad liyi / Geelu kugu yuus*
> — "Oh, Layli Goobalay! The most intelligent men and the camels prefer you."

The rules below are the rules **as implemented**. They follow **Ralf Gering's
article in *Abstract Games* magazine, issue 13 (Spring 2003), pp. 9, 14, 29**,
which is in turn based on the game **G. Marin** recorded near Berbera in 1931
(*Somali Games*, JRAI 61), with additional information from **Jama Musse Jama**.

## Board and setup

- Two parallel rows of **12 holes** each (the *Holes per side* option also offers
  the smaller **8** and **6** boards that are more common today; Marin's long
  12-hole board is the one the article — and the endgame problem — uses).
- **4 balls in every hole** at the start: **96 balls** on the 2×12 board.
- **Player 0 = South** (the bottom row), **Player 1 = North** (the top row). Each
  player controls the 12 holes on his own side.
- There are **no store pits**; captured balls are simply tallied (shown in the
  caption). South moves first.

**Hole numbering** (the article's notation, used in the move log): each player's
holes are numbered **1 … 12 from that player's right**. South sits below the
board, so South's hole 1 is the **right-hand** column; North sits above it, so
North's hole 1 is the **left-hand** column.

## Sowing — clockwise, multiple laps

On your turn, empty **one of your own holes that is not an *Uur*** and drop the
balls **one per hole, clockwise**, into the holes that follow. The ring runs

> North's row left → right (North 1 … 12), down the right edge, South's row
> right → left (South 1 … 12), up the left edge, and round again

so **each player sows his own holes in increasing hole-number order**. Every
hole on the ring receives a ball, **including *Uur* holes** and (on a very long
lap) the hole you started from. Nothing is ever skipped.

**Relay (multiple laps).** If the last ball falls into an **occupied** hole, you
take that hole's whole contents — **including the ball you just dropped** — and
sow another lap from there. You keep relaying until a lap ends in one of the two
terminal cases below. (Very rarely a chain never ends — see *Endless relay*
below.)

## How a move ends

1. **The last ball falls into an *Uur*** — the move simply ends. Nothing is
   captured; the ball belongs to the *Uur*'s owner.
2. **The last ball falls into an empty hole.** Then:
   - **On the opponent's side** → *abar* ("famine"): nothing is captured.
   - **On your own side**, look at the hole **directly opposite** (same column,
     other row):
     - it holds **1, 2, or 4-or-more** balls → **you capture** its whole contents
       **plus the ball you just dropped**; both holes are left empty;
     - it holds exactly **3** → one of the three is moved across so that **both
       holes hold two**. Those two holes now form an **Uur** (see below);
     - it is **empty** → *abar*, nothing is captured;
     - it is an **Uur** → *abar* (an *Uur* may never be emptied).

## The *Uur*

An **Uur** ("pregnancy") is a **pair of opposite holes**, one on each side of the
board, and **both belong to the player who created it** — no matter whose row
they sit in. The renderer tints both holes with their owner's seat colour.

- An *Uur* may **never be emptied** by either player: neither owner nor opponent
  may start a move from one, and a relay never lifts one.
- Balls **are** sown into an *Uur* during normal distribution, and a ball that
  **lands** in one ends the move.
- Every ball that ever falls into either hole of an *Uur* **belongs to its
  creator** and is counted for him at the end of the game.
- A player may create **several** *Uur*s.

## End of the game and scoring

The game is over when the player to move **has no legal move** (all his holes are
empty or *Uur*s). Each side then counts

> balls **captured** + balls sitting in **his own *Uur*s** + balls left on **his
> own side** outside *Uur*s

and the player with **more balls wins**. Every ball is counted exactly once, so
the two scores always add to 96 — and since 96 is even, **a genuine tie is a
genuine DRAW** (it does happen: 2% of random games on the 2×12 board end level,
rising to ~4% on 2×6).

Because the loser-to-move keeps nothing on the board, "often the game is won by
the player who moves last" — players hoard balls on their own side to protract
the game.

## Implementation notes and interpretations

- **Direction.** Marin observed **clockwise** sowing, which is the default; "in
  some parts of Somalia the game is played in an anti-clockwise direction" and
  the modern short-board game promoted by Jama Musse Jama is anti-clockwise, so
  a *Sowing direction* option offers that too (it simply reverses the ring).
  The article gives no direction arrow with its diagrams, so the clockwise sense
  was **pinned by brute force**: all eight combinations of (direction ×
  numbering origin × which printed row is South) were replayed against the
  magazine's published solution, and **exactly one reproduces it** — the one
  implemented here. See `selftest.py`.
- **Opposite hole = same column.** "Opposite" is geometric (directly across the
  board), which under the pinned numbering means South's hole *n* faces North's
  hole *13 − n*.
- **Landing opposite an existing *Uur*** is treated as *abar*: the rule that "an
  *Uur* may never be emptied by either player" outranks the capture rule. The
  article does not spell this case out.
- **Endless circulation.** The article: *"Sometimes towards the end of the game
  the balls continue to circulate in a repeating pattern. No rule is given by
  Marin for such a case, but according to Jama Musse Jama the remaining balls are
  divided between both players, as in Oware."* Oware's rule is that each player
  takes the balls on his own side — which is already exactly how Layli Goobalay
  scores — so this package implements it as: after **300 plies with no capture,
  no new *Uur* and no ball added to any *Uur*** the game stops and is scored
  normally (which can, of course, be a draw). A hard **4000-ply cap** backs that
  up. Neither fires in real play — random games on the 2×12 board last ~55 moves
  and the longest no-progress streak observed is 15.
  *(Gering's own longer write-up on Mancala World instead says an endless cycle
  is "considered a draw". The magazine text is this package's primary source, so
  the Oware split is what is implemented; in practice a cycle is a near-balanced
  position and usually scores as a draw anyway.)*
- **Endless relay** — a *different* thing from the above, and one no source
  mentions. A **single move's** relay chain can circulate for ever: 8 balls out
  of South's hole 6 in the 2×6 position `S 8·1·8·1·2·3 / N 0·1·0·3·0·1` start a
  chain that never dies. It is rare and small-board-only — about **0.04 % of
  moves on 2×6**, and **none** in 33 000 moves on the 2×8 and 2×12 boards. The
  chain is a deterministic function of (balls in hand, board), so a repeated
  configuration proves it is periodic. The engine sows normally for up to 512
  laps (the longest chain that *does* end, over ~2400 random games, is 95); if it
  is still going it re-runs the move from the start, recording configurations,
  and ends it at the **first repeat** as an ***abar***, which by definition
  captures nothing. Every such chain observed is periodic from its very first
  lap, so the move resolves to a **null move**: the balls end up exactly where
  they were and the turn simply passes. Stopping at the first repeat rather than
  after some number of laps is what makes the result independent of any cap
  constant.
- **Move log notation** follows the article: `South 4x2` = South played his hole
  4 and captured 2 balls; `North 8U` = North played his hole 8 and made an *Uur*.

## Correctness anchor

`selftest.py` replays the magazine's **endgame problem** (position pixel-read
from the PDF figure; it checks out against ball conservation, 28 on the board +
24 + 44 captured = 96) and its **published solution**, both lines, asserting
every printed `U` / `x n` annotation:

- **North to move:** `1 / 12 / 4 (x2) / 10 (x3) / 1` — reproduced exactly,
  including both capture sizes; South is then left without a legal move and
  **North wins by two points** (49–47), exactly as printed.
- **South to move:** `10 / 9 / 1U / 8 / 12 / 1 / 11` — reproduced exactly, and
  **all eight** of North's replies then die inside South's new *Uur*, as the
  article claims.
- **Variation:** `10 / 1 / 11U / 2 / 1 / 1` — reproduced exactly; South is then
  left without a move and wins, as printed.

It also replays the opening analysis from Gering's Mancala World write-up
(`1` captures 6; `1 / 5 / 5 / 3 / 4 / 8 / 11` = x6, abar, abar, x9, x9, x11,
x13; and the threats "8 makes a Qur", "10 captures 12 stones") — an independent
second anchor that reaches the same convention.

> **Erratum in the published solution.** The article (and Gering's Mancala World
> page) say South's main line wins **"by one point"**. That is impossible: the 96
> balls are conserved and every ball is counted for exactly one player, so every
> margin is **even**. Under the unique convention that reproduces the rest of the
> solution the margin is **two** (49–47) — the same margin the article states
> correctly for the North line.
