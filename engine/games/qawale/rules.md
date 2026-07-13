# Qawale

Romain Froger & Didier Lenain-Bragard, Gigamic 2022. 2 players, 4×4 board.
Rules as implemented here, from the official Gigamic rulebook (USA/GB page).

## Setup

- Each player takes **8 pebbles** of their colour (Red = first player, Blue = second).
- **Two neutral pebbles** (green here, tan in the physical game) are stacked
  on **each of the four corners**.

## Your turn

1. **Place**: choose any stack on the board (a single pebble counts as a
   stack) and put one pebble from your hand **on top of it**. You may *not*
   place a pebble on an empty square.
2. **Sow**: pick up that whole stack and play its pebbles out one at a time,
   **starting with the bottom pebble**, one pebble per square:
   - the first pebble goes on a square **orthogonally adjacent** to the
     stack's square; each following pebble goes orthogonally adjacent to the
     previous one (never diagonally);
   - you may **not** go straight back onto the square you just came from
     (including stepping back onto the lifted stack's own square as your
     second drop) — but you **may** return to a square by **circling round**
     to it, giving it another pebble;
   - pebbles land **on top** of anything already on a square. Since your own
     pebble was placed on top before lifting, it is dropped **last**.

Every stack always has a legal sow, so there is never a pass.

## Winning

The first **visible line of four pebbles of one colour** — a row, a column
or a diagonal, where *visible* means the top (or only) pebble of its stack —
wins the game **for that colour's player, whoever made the move**. Sowing
your opponent's buried pebbles back on top can complete *their* line and
lose you the game on your own turn.

- A vertical **stack** of four of one colour is *not* a line.
- If both players have played all eight of their pebbles and no line has
  been made, the game is a **draw** (so a game never exceeds 16 moves).

### Documented interpretations

- The rulebook says "the first player to make a visible line of 4 pebbles of
  *their* color … wins" and does not state who wins if a single sow completes
  lines of **both** colours at once. We rule (per the Quixo precedent, same
  publisher family of line-race games): **the non-moving player wins**. This
  also means a move that completes only the opponent's line loses immediately.
- Neutral pebbles are rendered in the platform's neutral colour (**green**),
  not tan.

## Move notation

`c,r>p1>p2>…>pn` — the first cell is the stack you top and lift; the rest is
the full sowing path (one pebble per listed square, bottom pebble first). In
the UI: click the stack to place on, then click out the sowing path square by
square.
