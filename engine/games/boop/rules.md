# boop.

Scott Brady, 2022 (Smirk & Dagger Games). 2 players, 6×6 board (the quilted "bed").
Red moves first.

## Pieces

Each player has **8 Kittens** and **8 Cats** in their colour. You start with the
8 Kittens in your pool (in hand); the 8 Cats start *out of play* and are earned by
graduation. You always have exactly **8 active pieces** (pool + board).

## Your turn

Place one piece from your pool — a Kitten, or a Cat once you have one — on **any
empty square** (click the square, then pick Kitten or Cat).

### The boop

The placed piece pushes ("boops") **every adjacent piece, in all 8 directions**,
one square directly away from it:

- A booped piece does **not** move if the square directly behind it is occupied
  (by any piece, either colour).
- A piece booped **off the bed** returns to its **owner's pool** (staying a
  Kitten or a Cat).
- Booped pieces cause **no chain reactions** — only the placed piece boops.
- **Kittens cannot boop Cats.** Cats boop both Cats and Kittens.

### Graduation (after the boop — your pieces only)

If three of your pieces stand in a row (horizontally, vertically or diagonally)
and at least one is a Kitten: **all three are removed and three Cats go to your
pool** (Kittens graduate out of the game; Cats in the row return as Cats).

- With **several rows** (or more than 3 in a row), you **choose one** group of 3
  to graduate; the rest stay on the board.
- If **all 8 of your pieces are on the bed**, you must resolve your turn by
  either graduating a row (if you have one) **or picking up any one of your
  pieces** — a picked-up Kitten graduates into a Cat, a picked-up Cat returns to
  your pool as a Cat.
- When exactly one resolution is possible it is applied automatically; otherwise
  click a highlighted piece and pick from the choices.

## Winning

Checked **after** the boop settles, **for the mover only** (official FAQ: "only
the active player can win on their turn"):

- **Three of your Cats in a row**, or
- **all 8 of your pieces on the bed are Cats.**

If your boop pushes your *opponent's* pieces into a row, it scores for them only
at the end of *their* next turn — if it survives your opponent's own boop.

## Draws (engine backstops — as implemented)

The physical game has no draw rule, but pieces cycle between bed and pool, so
this implementation adds honest backstops: **threefold repetition** of a full
position (board + pools + player to move) or **600 total moves** is a draw.

Source: the official Smirk & Dagger rulebook (SND 1009) and the publisher's
Dized FAQ. This implementation follows them exactly except for the added draw
backstops.
