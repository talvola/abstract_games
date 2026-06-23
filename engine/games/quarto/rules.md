# Quarto

Quarto (Blaise Müller, 1991; published by Gigamic) is an abstract two-player game
played on a **4×4 board** with **16 unique pieces**. Its signature twist: *you do
not choose your own piece — your opponent does.*

## The 16 pieces

Every piece is a unique combination of **four binary attributes**:

| Axis   | Values                |
|--------|-----------------------|
| Height | **T**all / **S**hort  |
| Colour | **L**ight / **D**ark  |
| Shape  | **R**ound / **Q** square |
| Fill   | **H**ollow / **F** solid |

That gives 2×2×2×2 = **16 distinct pieces**, one per combination. In this
implementation each piece is shown as a 4-letter code in the fixed order
**height–colour–shape–fill**, e.g. `TLRH` = tall light round hollow, `SDQF` =
short dark square solid. Light pieces are drawn light, dark pieces dark, so the
colour attribute is also visible at a glance.

Pieces are **shared** — they are not owned by either player. You always place
whichever piece your opponent has handed you.

## The turn

On your turn you do two things, in order:

1. **Place** the piece your opponent gave you on any **empty** cell.
2. **Choose** one of the remaining unused pieces and **hand it to your opponent**
   for their turn.

The **very first move** of the game is only step 2: the first player picks a
piece and gives it to the second player (nothing is placed yet). From then on
play alternates, each turn being place-then-give, until the board is full or
someone wins. (When the 16th piece is placed there is nothing left to give, so
the final move is just a placement.)

## Winning

Immediately **after a placement**, check every full **line of four** — each row,
each column, and the **two main diagonals**. If any such complete line consists of
four pieces that **all share at least one attribute** (all tall, *or* all light,
*or* all round, *or* all hollow, etc.), the player who just placed **wins**.

Note the subtlety this rule produces: because you choose your opponent's piece,
it is entirely possible to hand them the exact piece that completes a winning line
for them — a core tension of the game.

A **full board with no shared-attribute line is a draw**.

### Advanced 2×2 option

The optional Gigamic advanced rule (manifest option **"2×2 square win"**, default
off) adds a fifth kind of winning group: any full **2×2 square** of four adjacent
cells whose pieces all share an attribute also wins. With the option off, only
rows, columns, and the two main diagonals count.

## Move notation (this implementation)

- **First move:** `give=<code>` — e.g. `give=TLRH`. (Shown as action buttons.)
- **Normal move:** `c,r=<code>` — place the in-hand piece on cell `c,r`, then give
  `<code>` to the opponent. In the web UI you click the empty cell, then pick which
  piece to hand over from the choice menu.
- **Final placement** (no piece left to give): `c,r`.

Cells use `c,r` with `c` the column and `r` the row, both `0..3`. The piece you
must place this turn (your "in hand" piece) is shown in the caption and in a
reserve slot above the board.
