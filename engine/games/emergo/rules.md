# Emergo

*Christian Freeling & Ed van Zon, 1986* — a **stacking draughts** game. "Emergo"
(Latin, *I rise / I emerge*) refers to a buried man re-emerging to take control of
a column once the men above it are captured.

## The board

Play is on the **41 dark squares of a 9×9 board** (dark squares in the corners,
the centre square dark). Rotated 45°, those dark squares form Freeling's
"diagonal plane" — a diamond. In this package the board is rendered as the 9×9
grid and a dark square is any cell `c,r` (0–8) with `c+r` even; all moves and jumps
run along the **diagonals** of that grid (exactly as in checkers/Lasca).

## Pieces and columns

A **piece** is a column (stack) of one or more men, drawn bottom-to-top. The man on
**top** is the *cap*; the men beneath are *prisoners*. **The colour of the cap owns
the whole column** — only that player may move it, and capturing the cap hands the
column to whoever is now on top. There are **no kings / no promotion** — every piece
behaves the same regardless of height.

Each player begins with **twelve men in hand, off the board.**

## A turn: enter, move, or capture

On your turn you do exactly one of:

1. **Enter** a man from your hand onto any vacant dark square (the *entering phase*).
   - You may enter **one man per turn**, *unless your opponent has already placed
     all twelve of their men*, in which case you must **enter all your remaining men
     at once as a single column** on one vacant square.
   - **You may not enter a man on a square that would force your opponent to
     capture** on their reply (unless you are yourself already obliged to capture —
     in which case you must capture, not enter).
   - **White may not enter on the centre square on the very first move** of the game.
   - You may always choose to **move a piece instead of entering** while you still
     have men in hand.
2. **Move** a piece you control **one square diagonally** to an adjacent **empty**
   square, in **any of the four diagonal directions**.
3. **Capture** — see below. **Capture is compulsory** and takes precedence over both
   entering and moving.

## Capture — the prisoner-under mechanic

You capture by **jumping an adjacent enemy column diagonally and landing on the empty
square immediately beyond**. The jumped column's **top man (its cap) is removed and
tucked *underneath* your moving column** as a prisoner — your column grows by one.
**The rest of the jumped column stays where it is**, now capped (and controlled) by
whatever man is newly on top.

- Captures are **mandatory**.
- A capture **must take the maximum number of men** ("majority capture"): among all
  jump sequences you must play one that captures the most men.
- Captures **chain**: after a jump, if the moving column can jump again it must
  continue. A chain may **revisit a square** and may **jump the same column more than
  once** (because that column is still standing). An **immediate 180° reversal** (back
  over the man you just jumped, in the same line) is **not allowed**.

## Liberation

There is no separate "liberation move". Liberation is the consequence of the
under-stacking: when a column's cap is captured, the prisoner directly beneath it
**emerges** as the new cap and the column changes hands. The classic Emergo tactic
**feeding** exploits compulsory + maximum capture: you deliberately let an enemy
column capture a string of your men so it rises tall, then capture *its* cap with a
finishing jump — freeing all the prisoners beneath and seizing the whole tower.

## Winning

You win when your **opponent has no man left** (every one of their men has been
captured and now rides as a prisoner under your columns, with none of their colour on
top anywhere and none in hand), **or when the opponent has no legal move** on their
turn.

## Draws (this implementation)

To guarantee termination the package draws on **threefold repetition** of the exact
position (board + side to move + hands), on **60 plies with neither a capture nor an
entry**, or at a hard **600-ply cap**. The original is "very decisive" and rarely
drawn; these caps only stop pathological shuffles.

## Ruleset choices / flags (read this)

- **"Cannot move" = loss.** Sources disagree: Wikipedia/Freeling say *the game ends
  when a player cannot move or has no men left* (a loss); one online server treats
  "has a piece but cannot move" as a draw. This package follows the **loss**
  interpretation (the more decisive, BGG/Wikipedia reading). In practice a player who
  still has men in hand can almost always enter, so the no-move case is rare.
- **No-force entry restriction.** Implemented as: an entry is illegal if, after it,
  the opponent would have any capture available. (If *every* end-of-entry stacked
  square would force the opponent, the restriction is relaxed for that final stacked
  entry so the game cannot dead-end.)
- The **diagonal board** is modelled as the dark squares of a 9×9 grid with diagonal
  movement — geometrically identical to the physical diamond, and consistent with the
  platform's other draughts games.

## How Emergo differs from Lasca & Bashni

Emergo shares the **column / prisoner-under-the-cap** idea with Lasca and Bashni
(all "column checkers"), but is a **distinct game**, not a re-skin:

All three are "column checkers": the captured **top man is tucked under** the
moving column, and **whoever's on top controls** it. What makes Emergo its own
game is everything *around* that shared core.

| | **Emergo** | **Lasca** | **Bashni** |
|---|---|---|---|
| Board | **41 dark squares of 9×9** | 25 dark squares of 7×7 | 32 dark squares of 8×8 |
| Start | **All 12 men off-board → ENTER them** (an entering phase) | 11 men pre-placed | 12 men pre-placed |
| Kings / promotion | **None** — every piece is identical | Soldier → officer (4-way) | Man → flying king |
| Move | **One step, any of 4 diagonals** (no forward rule) | Soldier forward-only; officer 4-way | Man forward-only; king flies |
| Capture range | **Adjacent jump only** (one step) | Adjacent jump | King captures at a distance |
| Capture obligation | Compulsory **and maximum** (majority capture) | Compulsory, full chain | Compulsory |
| Win | **Capture ALL enemy men** (or opponent has no move) | Opponent cannot move | Opponent has no men/move |

The signature Emergo features — none of which Lasca or Bashni share as a set — are
the **off-board entry phase** (no fixed starting array, with the no-force and
first-move-centre restrictions), the **king-less, fully omnidirectional**
single-step move, **maximum** capture, and the **capture-everything** victory. So
although it reuses our stacking/column renderer, it is mechanically distinct, not a
re-skin of Lasca.
