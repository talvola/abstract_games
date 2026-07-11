# Urbino

Dieter Stein, 2018. Two players jointly develop the town of Urbino; the player
who builds the most valuable districts wins. Rules as implemented, verified
against the designer's official rules
([spielstein.com/games/urbino/rules](https://spielstein.com/games/urbino/rules)).

## Material

- 9×9 board, initially empty.
- Each player: **18 houses** (worth 1), **6 palaces** (worth 2), **3 towers**
  (worth 3). On screen a building is drawn as a stack of 1 / 2 / 3 bands.
- **Two shared architect figures** (green triangles) — they belong to neither
  player.

## Opening

1. **Dark** places the first architect on any square.
2. **Light** places the second architect on any other square.
3. **Dark decides who erects the first building** (the two buttons). That
   player takes the first turn, which consists of the build action only; from
   then on players alternate full turns.

## A turn

1. **Reposition an architect (optional).** Pick either architect and *place*
   it on any unoccupied square (architects teleport — they do not travel along
   lines), or press **pass** to leave both in place. Whatever you choose must
   leave at least one legal build — the UI only offers such choices.
2. **Erect a building (mandatory).** Place one building from your supply on a
   legal square (tinted on the board), then the picker asks H / P / T:
   - **Sight:** each architect sees along clear horizontal, vertical and
     diagonal lines, not over occupied squares. A building may only go on an
     empty square seen by **both** architects. (Two architects on one clear
     line see every square between them.)
   - **Districts:** all orthogonally connected buildings form a *district*.
     A district may contain **at most one block per player** — all of your
     buildings inside a district must remain orthogonally connected
     (diagonal does not connect).
   - **Neighbours:** a tower may never be orthogonally adjacent to another
     tower, nor a palace to another palace — regardless of colour. Houses are
     unrestricted.

**Skipping:** voluntary passing of the whole turn is not allowed. If no
combination of (reposition or stay) + build exists, you must **skip** (the
single button offered). You may re-enter play later if new openings appear.

## End and scoring

The game ends when **both players skip in a row** (it also ends at a 500-ply
safety cap, scored the same way).

- Only **two-coloured** districts score. One-colour districts and lone
  buildings score nothing.
- In each scoring district, the player whose buildings there have the **higher
  total value** (houses 1, palaces 2, towers 3) scores **his own total**; the
  loser's value is wasted. If the values tie, compare counts of towers, then
  palaces, then houses; if still tied, **neither player scores** the district.
- Highest grand total wins. A tied total is broken by the scored buildings
  (towers, then palaces, then houses, over the districts each player won);
  a full tie is an honest **draw**.

## Monuments variant (option, off by default)

Three of your buildings in a straight orthogonal line score double as a
monument: **town wall** H-H-H = 6, **ducal palace** P-H-P = 10,
**cathedral** T-P-T = 16. Only **one monument per block** may be scored (the
best one is chosen automatically). A tied district is first broken by the more
valuable scored monument, then by the normal tower/palace/house comparison.

## Notes on this implementation

- Seat colours on screen: Dark = red, Light = blue (the physical game uses
  dark/light wood; architects are green here, red in the physical set).
- Move log notation: `A@e5` architect placement, `A e5-c3` reposition,
  `H@d4` build, `keep architects`, `skip (cannot build)`.
