# Unlur

**Designer:** Jorge Gómez Arrausi (2001) — winner of the 2002 *Unequal Forces*
game-design competition. One of the very few balanced *asymmetric* connection
games.

These are the rules **as implemented** in this package.

## Board

A hexagonal board of hexagons (a "hexhex") with **N hexes on each side**
(default **N = 6**, the designer's original recommendation; 7 and 8 are also
offered). The hexagon has **6 sides** and **6 corners**. The six sides are
numbered 0–5 around the board; side `i` and side `i+3` are **opposite**, and the
three sides `{0,2,4}` (and likewise `{1,3,5}`) are **mutually non-adjacent**.

Stones are placed on empty cells and are **never moved or captured**.

## The two roles and their goals (asymmetric)

There are two roles, **Black** and **White**, with *different* objectives:

- **Black wins** by forming a single connected chain of **black** stones that
  touches **three non-adjacent sides** of the board (a **"Y"**).
- **White wins** by forming a single connected chain of **white** stones that
  touches **two opposite sides** of the board (a **"line"**).

**You lose if you complete your opponent's goal.** Because the goals are
complementary:

- If **Black** ever connects two opposite sides (a line) *without* also having a
  Y, **Black loses** (White wins).
- If **White** ever connects three non-adjacent sides (a Y) *without* also having
  a line, **White loses** (Black wins).

If a single placement simultaneously completes *your own* goal, you win
regardless of also touching the opponent's pattern. **Draws are impossible** —
exactly one player always wins.

## The contract (opening) phase

The roles are not fixed in advance; a "contract" phase decides who plays Black
and who plays White, balancing the asymmetry:

1. Starting with the first player, the two players take turns. On a turn a player
   either **places a BLACK stone on any empty INTERIOR cell** (never on a
   border/edge hex) **or passes**.
2. All stones placed in this phase are **black**, regardless of who places them.
3. The **moment a player passes**, the contract ends: **the player who passed
   becomes Black** for the rest of the game (and owns every black stone already
   on the board), and **the other player becomes White**.
4. **White then makes the first move of normal play.**

Strategically you keep adding black stones until you judge Black has *just
enough* to be fair against White — then you pass to claim Black; pass too early
and White is too strong, too late and you have handed White a head start.

## Normal play

After the contract, players alternate turns (White having moved first). On a
turn a player **places one stone of their own colour** (Black or White) on any
empty cell — **border cells are now allowed**. After each placement the win/loss
conditions above are checked; the game ends the instant someone wins.

## Notation

- A placement move is the cell id `"q,r"` (axial hex coordinates).
- The contract pass is the action button **`pass`** ("pass (become Black)").

## Board colouring (visual aid only)

The six sides are tinted in two alternating shades to make the goal patterns
visible: the three sides `{0,2,4}` share one shade and `{1,3,5}` the other.
**Black** needs one whole alternating triple (three same-shaded sides); **White**
needs any opposite pair (one cell of each shade on opposite edges). The tinting
is purely a visual aid — *any* non-adjacent triple works for Black and *any*
opposite pair for White.

## Sources

- HexWiki — Unlur: https://www.hexwiki.net/index.php/Unlur
- Ludoteka — Unlur rules: https://www.ludoteka.com/clasika/unlur-en.html
- Dr Eric Silverman, "Connection Games IV: Unlur":
  https://drericsilverman.com/2020/03/09/connection-games-iv-unlur/
- BoardGameGeek — Unlur: https://boardgamegeek.com/boardgame/3826/unlur
