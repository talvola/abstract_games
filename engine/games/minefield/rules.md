# Minefield

**Mark Steere (May 2024).** A square-board connection game in which *every
point is a mine*: two small stone patterns — the **hard corner** and the
**switch** — may never be formed, by either player, in any orientation or
colour. A filled board always has a winner. *(Rules as implemented in this
package.)*

## Board and goal

- Played on the points of an initially empty square grid (default **11×11**;
  this package also offers 9, 13, 15 and 19 — Steere's sheet says "any size").
- **The top and bottom edges are black; the left and right edges are white.**
- **Black** (player 0) wins by forming an **orthogonally** (horizontally and/or
  vertically) interconnected path of black stones joining the two black edges.
  **White** (player 1) joins the two white edges.
- **Diagonal adjacency does NOT connect.** Minefield is, in the designer's
  words, an *SPO OOSCG* — a **S**ingle **P**lacement **O**nly, **O**rthogonal
  **O**nly **S**quare **C**onnection **G**ame.

## Playing a turn

Starting with Black, players alternate placing **one stone of their own colour
on any unoccupied point**, subject only to the glyph rule below. Nothing is
ever moved, removed or captured.

**Passing is not allowed, but if you have no available placement your turn is
skipped** and your opponent plays again. (In this implementation the skip
happens automatically — you are never offered a "pass" button.)

**Pie rule.** On White's first turn only, White may play **swap** instead of
placing: he "switches colours and becomes Black, claiming the first placement
as his own".

## The prohibited glyphs

No player may **form** either of these patterns — **nor any reflection,
rotation or colour reversal of them**. In the diagrams `B`/`W` are stones and
`.` is an unoccupied point; a *pattern is a glyph only if the marked points are
unoccupied*.

### Hard corner

Two stones of one colour and one stone of the other colour contained in a
**2×2** area. The two same-coloured stones are diagonally adjacent, and one
point within the area is unoccupied.

```
W .        (the two W stones are diagonally adjacent;
B W         the B stone is the odd one out; one point is empty)
```

Equivalently: a 2×2 area holding exactly three stones, in which the two stones
that are diagonally opposite **each other** share a colour and the third stone
does not.

### Switch

Two stones of **each** colour contained in a **2×3** ("short switch") or a
**2×4** ("long switch") area. Two stones of one colour occupy diagonally
opposite corner points of the area, the two stones of the other colour occupy
the other two corner points, and **all the non-corner points of the area are
unoccupied**.

```
short switch (2x3)     long switch (2x4)

   W B                    W B
   . .                    . .
   B W                    . .
                          B W
```

Both orientations count (a 3×2 and a 4×2 area are the same glyphs rotated).
A 2×2 checkerboard ("crosscut") is *not* on the list — it does not need to be;
see below.

### How the restriction is applied

The glyph rule is judged on the position **after** your placement. Both glyphs
require an unoccupied point, so adding a stone can only ever *destroy* existing
glyphs — a glyph therefore never exists on the board, and the only patterns
that need checking are those containing the point you just played. That is what
makes Minefield's mechanism purely **local**: you only have to look at the
2×2 / 2×3 / 2×4 areas around the point you are considering.

## Draws, stalls and termination

**No crosscut can ever appear.** Take a 2×2 with two black and two white
stones on its diagonals and remove any one of them: the three that remain are
always a hard corner. So the fourth stone of a crosscut could never have been
legally placed.

That is what makes a **full board decisive**: if Black has no orthogonal
top–bottom chain on a full board, then White has a *diagonally* connected
left–right chain (4-connectivity for one colour is dual to 8-connectivity for
the other on a square grid). Take any diagonal step of that chain: the two
points completing its 2×2 are occupied (the board is full), and if either is
white the step can be rerouted through it. Both being black would make that
2×2 a crosscut — impossible. So every diagonal step can be replaced, White's
chain is orthogonal after all, and White has won.

Stones are never removed and every ply either places a stone on a previously
empty point or is the one-off pie swap, so a game lasts **at most
`size × size + 1` plies**. This package therefore ships **no ply cap, no
repetition rule and no draw counters**.

The one loose end is the sheet's silence about what happens if **neither**
player has a legal placement while empty points remain. This implementation
ends the game as an **honest draw** (`0 – 0`), never a fabricated tiebreak; the
same verdict AbstractPlay's implementation reaches via a double pass. It has
never been observed: the complete reachable-position enumerations of the 3×3
(2,980 positions) and 4×4 (2,916,147 positions) boards contain **no** such
position — all 879,863 of their terminal positions are wins — and neither do
thousands of random games nor an adversarial hunt that plays deliberately to
strangle mobility on the 4×4 – 9×9 boards. (Single-player
skips, on the other hand, are quite real and do occur on small boards.)

## Pie rule (swap) — how it is represented here

Seats are fixed in this platform, so "White becomes Black and claims the first
placement" is represented by the **value-preserving transposition**: Black's
lone opening stone at *(c, r)* becomes a **White** stone at *(r, c)*, and Black
(seat 0) is on move again — which is exactly the position the swapper obtains,
because Minefield is symmetric under reflection in the main diagonal combined
with colour reversal (the transpose exchanges the black row-goal with the white
column-goal, and the glyph set is explicitly closed under both reflections and
colour reversals). Recolouring the stone *in place* would **not** preserve the
value, since the two colours aim at different edges. Same convention as this
platform's Crossway, Konobi, Rhode, Cation, Akimbo and Okimba packages.

## How Minefield differs from the other square connection games here

| Game | Connection | Restriction |
|---|---|---|
| **Minefield** | **orthogonal only** | may not form a **hard corner** or a 2×3/2×4 **switch** |
| Crossway | orthogonal *or diagonal* | may not complete a crosscut |
| Konobi | 8-adjacency (strong + weak links) | the *kosumi* rule + no crosscuts |
| Cation | orthogonal only | crosscuts are legal and are resolved by **moving** a stone (ko fights) |
| Rhode | orthogonal only | diagonal links must be **consolidated**, costing a turn; crosscut stones are **removed** |
| Akimbo | orthogonal only | at most one naked diagonal **per colour**; crosscut stones are **removed** |
| Okimba | orthogonal only | at most one naked diagonal on the **whole board** |

Minefield is the only one of them whose restriction bans a **three**-stone
pattern (the hard corner) and a pattern spread over a **2×4** area (the long
switch), and the only one that never moves or removes a stone while still
having no per-turn obligation. Its ban is also strictly stronger than a
crosscut ban — a crosscut is impossible here as a *consequence* of the hard
corner rule, not as a rule of its own — and unlike Akimbo/Okimba it counts
nothing globally: legality is decided entirely inside a 4×4 window.

## Ruleset choices made in this implementation

1. **The 2026 revision of the sheet is the source.** The rule sheet at
   `marksteeregames.com/Minefield_rules.pdf` was silently revised (ModDate
   2026‑05‑17) from the version archived on 2024‑05‑09. The revision **adds the
   pie rule**, adds "or **colour reversals**" to the list of prohibited
   transformations, replaces the two old example figures with one worked
   example (Figure 3) and drops the old "local mechanism" paragraph. This
   package implements the **current** sheet, pie rule included.
2. **"Form a glyph" = the position after your placement contains one.**
   Equivalent to the local test, as argued above.
3. **A switch area is 2×3 or 2×4 only.** Not 2×5 or larger, and not 2×2 —
   taken verbatim from the sheet and confirmed by Figure 2, which prints
   exactly one hard corner, one 2×3 switch and one 2×4 switch.
4. **Non-corner points** in the switch definition means the non-corner points
   *of that area* (2 of them in a 2×3, 4 in a 2×4) — confirmed by the blue dots
   in Figure 2 (1 + 2 + 4 = the 7 blue dots the artwork actually contains).
5. **The skip is not a move.** The sheet says the turn "is skipped", not that
   you play a pass, so no pass move is offered; the skip is applied inside the
   turn change. If neither player can place, the game ends in a draw (see
   above).
6. **Orthogonal connection only**, per both the OBJECT OF THE GAME paragraph
   and the design note. *AbstractPlay's implementation awards the win on a
   diagonally connected chain* (its win graph is built with 8-adjacency); this
   package follows the rule sheet. Its `pass` move also fails its own
   validation, so the skip rule is unreachable there.
7. **Default board 11×11** — the size AbstractPlay's engine falls back to.
   Steere specifies no size.
8. **No `pinwheel` / `cartwheel` variants.** AbstractPlay offers two extra
   rulesets under those names (they drop the long switch and add an 11-point
   pinwheel glyph, one of which even treats the board edges as coloured
   stones). They come from a BGG discussion thread, not from Steere's rule
   sheet, so they are not shipped here.

Official rules: <https://www.marksteeregames.com/Minefield_rules.pdf>
