# Domain

*A tile game related to Othello* — by Larry Back (**Abstract Games** magazine,
issue 12, Winter 2002). Published in North America by **Parker Brothers** in
1983 as *Domain*; earlier marketed in Europe as *Boomerang* (France), *Kiss*
(Italy) and *Chameleon* (England).

Domain is Othello played with polyomino tiles instead of single discs. It is a
game of pure skill — two players, no chance, no hidden information — and a
typical game lasts no more than a dozen moves per side.

## Board and tiles

The board is a **9×9 grid** of empty squares. Each player owns the **same set of
26 reversible tiles**, blue on one side and white on the other. A tile is
identified by the number of squares it covers (2 to 5), which is also its point
value.

| Tile | Shape | Squares | Copies |
|------|-------|--------:|-------:|
| Short Bar  | 1×2 bar            | 2 | 6 |
| Medium Bar | 1×3 bar            | 3 | 6 |
| Long Bar   | 1×5 bar            | 5 | 2 |
| Angle      | L-corner (3 cells) | 3 | 4 |
| Square     | 2×2                | 4 | 2 |
| Small T    | T-tetromino        | 4 | 2 |
| Cross      | plus-pentomino     | 5 | 2 |
| Large T    | T-pentomino        | 5 | 2 |

That is **26 tiles covering 88 squares** per side. Every tile is
mirror-symmetric, so flipping it over (to show the other colour) lets it cover
exactly the same squares — which is why there is no plain L-tetromino, for
example.

## Playing a move

Players alternate. Seat 0 (Blue) moves first. To move, select one of your tiles
and place it over empty squares, fully on the board and not overlapping any tile
already there.

**Flip rule.** After you place a tile, *every opponent tile that is touching the
placed tile is flipped to your colour.* Two tiles touch only when they occupy
**horizontally or vertically adjacent** squares — **diagonal touches do not
count.** A whole enemy tile changes colour at once; only the tiles touching the
tile you just placed flip, and there is no chain reaction.

**Touch restriction.** Except for the very first move of the game, a tile must
be placed so that it **touches at least one of the opponent's tiles** — exactly
as, in Othello, a move must capture at least one enemy disc.

**Passing.** You may pass only when you have no legal move, and then passing is
mandatory. (A blocked player is simply skipped.)

## End and scoring

The game ends when **neither player can move** — usually with several tiles still
unplayed. Each player's score is the **number of board squares their colour
covers**. The higher score wins. An **equal cover is an honest draw**.

There are 171 distinct opening moves up to the board's symmetry (1,149 counting
every placement separately) — Domain is far too large to solve.

## Rule versions (the `variant` option)

The game ships with three rule sets; the default is the second.

- **First (basic)** — Both players draw from **one common pool** of the 26 tiles,
  and there is **no touch restriction**: you may place a tile anywhere it fits.
  The flip rule is unchanged.
- **Second (intermediate, default)** — Each player has their **own** 26 tiles,
  the touch restriction applies, and an opponent tile you touch flips to your
  colour. This is the standard game described above.
- **Third (advanced)** — Like the second, except that **all** tiles touched by a
  placed tile — your own as well as the opponent's — flip to the **opposite**
  colour.

## Notes on this implementation

- Moves are entered with the polyomino-palette syntax `KEY:o@c,r` (tile key,
  orientation index, anchor cell); the board UI handles this by clicking a tile
  in your tray, choosing an orientation, and clicking a highlighted target.
- Under the *basic* variant the tray is a single shared **Pool**.
- The touch restriction is exempt only on the literal first move of the game; if
  a later position offers no placement touching an enemy tile you have no legal
  move and are skipped.
