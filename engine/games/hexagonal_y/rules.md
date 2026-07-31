# Hexagonal Y

**Designer:** Mark Steere (September 2023) · **Players:** 2 · **Red** (seat 0) moves first.

Steere's adaptation of the connection game **Y** to a *regular* hexagon — a board that,
unlike Y's triangle, has no corners to aim at. His answer is a pair of rules that work
together: a placement on the rim automatically fills the cell diametrically opposite it,
and you win by owning **more than half of the rim** with a single group.

> "I think of Hexagonal Y as, if not my magnam opus, at least one of my top two or
> possibly three designs." — Mark Steere

These are the rules **as implemented here**.

## The board

A regular hexagonal grid of hexagonal cells (a "hexhex") with all six sides of equal
length `n`, initially empty. The **perimeter** is the outer ring of cells.

| Board side `n` | Cells `3n²−3n+1` | Perimeter cells `6(n−1)` |
|---:|---:|---:|
| 4 | 37 | 18 |
| 5 | 61 | 24 |
| 6 | 91 | 30 |
| **7 (default)** | **127** | **36** |
| 8 | 169 | 42 |
| 9 | 217 | 48 |
| 11 | 331 | 60 |

Steere's sheet says "of any size" and every figure on it uses **side 4** (37 cells). The
default here is **side 7** (127 cells), which is also AbstractPlay's default for the game.
The perimeter always has an **even** number of cells, so every perimeter cell has a unique
**opposite** (antipodal) partner — the cell reached by rotating 180° about the board's
centre. The perimeter ring is tinted on the board.

## Play

- **Red** moves first; players then alternate. Stones are never moved, captured or removed.
- **Place one stone** of your colour on any empty cell.
- **Perimeter placements.** If the cell you place on is a **perimeter** cell, you must
  immediately **also place a stone of your colour on the opposite perimeter cell**, and
  that concludes your turn. So a rim move puts **two** stones on the board, an interior
  move puts **one**.

A consequence worth knowing at the table: *the rim always fills in matched opposite
pairs of the same colour*. It starts empty, and only ever changes two-at-a-time.

## Winning

> You win the moment one **connected group** of your stones satisfies **both**:
> 1. at least **two** of the group's stones occupy perimeter cells, and
> 2. the **shortest perimeter path** that includes all of the perimeter cells occupied by
>    that group comprises **more than half** of the perimeter.

Cells are connected to their six neighbours. "Shortest perimeter path" means: walk around
the rim; the shortest stretch of the rim that contains every one of the group's rim
stones. It is measured in **cells**, and it is exactly the whole rim **minus the largest
unbroken gap** between two of the group's rim stones.

**"More than half" is strict.** On a side-7 board the perimeter is 36 cells, so the path
must be **at least 19** cells. A path of exactly 18 is not a win.

*(Curiously, the strictness never actually decides a game: a covering path of exactly half
the rim is impossible. If one ran from rim cell `a` round to rim cell `b`, half the rim
long, then the cell just past `b` would be `a`'s opposite — the same colour as `a` by the
pairing rule — and it sits next to `b`, so it would join the group and make the path
longer. The engine asserts that no reachable position ever has a half-length path.)*

### The equivalent, easier-to-see form

Because the perimeter has an even number of cells, the following is **provably the same
condition** (the package asserts the equivalence over thousands of random cases):

> **You win iff the shortest covering path contains a pair of *opposite* perimeter cells.**

The two smallest wins follow directly:

- One group holding **any two opposite rim cells** wins — its covering path is half the
  rim plus one. This is exactly the position of **Figure 4** of the rule sheet.
- One group holding two rim cells that are *one short* of opposite spans exactly half the
  rim and does **not** win.

### The rule sheet's worked examples

`selftest.py` transcribes all four figures of the official PDF cell-for-cell out of its
vector art and checks the engine against them. Figures 2 and 3 print the shortest covering
path itself as black + green dots, so the check is on the **path**, not just the verdict:

| Figure | Sheet says | Engine says |
|---|---|---|
| 1 | Blue's first turn placed two stones on opposite rim cells | the two Blue stones are an antipodal pair; Red's lone stone is interior |
| 2 | "Thus Red has won" | Red wins; covering path = **12 of 18** cells, exactly the sheet's 3 black + 9 green dots |
| 3 | "not a winning position for Red" | Red does not win; longest covering path = **8 of 18**, exactly the sheet's 3 black + 5 green dots |
| 4 | "Red has won" | Red wins; the group's two rim stones are opposite, path = **10 of 18** |

## Draws

**There are none.** Stones are never removed, so play always reaches a full board, and a
full board always has a winner:

- Every game ends because each turn fills at least one empty cell — the number of empty
  cells strictly decreases, so a side-`n` game lasts at most `3n²−6n+4` turns (109 on the
  default board), and random play does reach exactly that. With the optional **pie** rule
  switched on the ceiling is `3n²−6n+5`: the swap is the one turn that places no stone,
  and it can be played at most once. There is **no ply cap** in the code; termination is
  proved, not capped.
- The rim can always be finished: empty rim cells come in opposite pairs, so you can never
  be left with a single unplayable rim cell.
- Exhaustively, for sides 2 and 3, **every** full board that respects the opposite-pair
  rule has exactly **one** winner (16 and 8,192 boards); random sampling on sides 4, 5, 7
  and 11 has never produced a draw or a double win either.
- The opposite-pair rule is what does it: the same exhaustion **without** that rule finds
  24 drawn boards out of 128 on side 2, and 54,480 out of 524,288 on side 3.

A genuine tie would still be scored as an honest draw (`0–0`) rather than a fabricated
tiebreak; the branch simply never fires.

## Interpretations

The sheet is short, so a few points had to be settled. Each was settled by evidence, not
by preference:

1. **"What if the opposite perimeter cell is already occupied?"** The prose never says,
   and AbstractPlay's implementation would silently overwrite whatever is there. **The
   situation cannot arise.** A rim cell and its opposite start empty together and can only
   be filled together, so they are always both empty or both the same colour. All four of
   the sheet's figures obey this, and the package asserts it after **every ply** of random
   games on every board size. (The code therefore never overwrites an existing stone; if a
   hand-built position somehow violated the invariant, the placement would simply put down
   the one stone it can.)
2. **The path is measured in cells, not steps**, and includes both end stones — this is
   forced by Figure 2, where the sheet's own 12 dotted cells are exactly `18 − 6`, the rim
   minus its largest gap.
3. **"More than half" is strict.** Figure 4 pins the boundary from the winning side (an
   opposite pair spans half + 1 and *does* win); Figure 3 pins it from the losing side.
4. **Only the player who just moved can win**, so only their groups are checked. A move
   adds stones of one colour only, so the opponent's groups are unchanged — had they had a
   winning group, the game would already have ended.
5. **The win is checked after *both* stones of a rim placement land**, since the sheet
   makes the double placement a single turn ("concluding your turn").
6. **Pie (swap) rule — optional, OFF by default.** Steere's sheet has no swap rule, so the
   default game is exactly his. AbstractPlay flags the game as pie-enabled, so it is
   offered as an option: with it on, the second player may answer the opening by playing
   **swap** instead of placing, taking over the opening stone (or the opening *pair*) and
   handing the move back.

## Notation

A move is the cell id `q,r` (axial). The move log shows AbstractPlay-compatible algebraic
names — a row letter counted up from the bottom row, then the cell's position from the
left within that row, so `a1` is the bottom-left cell. A rim placement is logged as the
**pair**, e.g. `m1+a7` on the default board (the top-left rim cell and its opposite); an
interior placement logs the single cell, e.g. the centre `g7`. The pie move is `swap`.

## How this differs from the other Y-family games here

| Game | Board | Goal |
|---|---|---|
| **Hexagonal Y** | regular hexagon, rim fills in opposite pairs | one group covering **more than half the rim** |
| **Y** | triangle | one group touching **all three sides** |
| **Poly-Y** | pentagon | own a **majority of the 5 corners**, each corner won by a Y |
| **Odd-Y** | pentagon / heptagon | one group touching three sides whose midpoint triangle contains the centre |
| **YvY** | serrated hexagon | territory scoring on **sprouts**, or an instant win by enclosing a loop |
| **Atoll** (also Steere) | hexagonal grid with **eight pre-placed islands** | join **two opposite islands of your own** with one group; no double placement |

Atoll is the closest relative — same designer, same hexagonal field, same
"link two opposite points of the rim" idea — but Atoll hands each player four fixed
islands to work between, while Hexagonal Y lets you *create* your own rim anchors, two at a
time, anywhere you like.

## Sources

- **Mark Steere, *Hexagonal Y* rule sheet** (2023) —
  [marksteeregames.com/Hexagonal_Y_rules.pdf](https://www.marksteeregames.com/Hexagonal_Y_rules.pdf).
  The live sheet and the archived 2023 revision differ only by one grammar fix in the
  prose (`on an regular` → `on a regular`); their artwork is byte-for-byte identical
  (all 327 vector paths match), so **no rule or figure has ever changed**.
- [Hexagonal Y on BoardGameGeek](https://boardgamegeek.com/boardgame/432211/hexagonal-y) (id 432211).
- AbstractPlay's `hexy` implementation was used as an independent oracle (board state,
  legal moves and results agreed over complete games on every board size).
