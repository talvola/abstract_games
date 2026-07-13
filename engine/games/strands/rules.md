# Strands

A two-player abstract by **Nick Bentley (2022)**. Played on a hexagonal board
whose cells are pre-printed with numbers; you build the single largest
connected group of your own stones.

## Board

A hexagon with **N cells per side** (this port offers N = 5, 6 or 7; default
**6** — the "six cells per side" board igGameCenter calls canonical, 91 cells).
Every cell is labelled with a number. The centre is a single **1**; the numbers
increase outward, and the six geometric corners are the highest (**6**). The
fixed layouts are AbstractPlay's `size-{5,6,7}-fixed` boards — the same boards
served by igGameCenter and Board Game Arena.

Size-6 layout (centre `1`, corners `6`), rings from the middle row outward:

```
      6 4 4 4 4 6
     4 3 3 3 3 3 4
    4 3 2 2 2 2 3 4
   4 3 2 2 2 2 2 3 4
  4 3 2 2 2 2 2 2 3 4
 6 3 2 2 2 1 2 2 2 3 6
  4 3 2 2 2 2 2 2 3 4
   4 3 2 2 2 2 2 3 4
    4 3 2 2 2 2 3 4
     4 3 3 3 3 3 4
      6 4 4 4 4 6
```

## Play

- **Black** (seat 0) opens by covering **exactly one** empty cell marked **"2"**.
- From then on, starting with **White** (seat 1), players alternate turns.
- On your turn, choose a number **X** and cover **up to X** empty cells that are
  all marked **X** — for example, cover any one, two or three empty "3" cells.
  You must cover at least one; if fewer than X empty "X" cells remain, cover as
  many as are left.
- A covered cell holds one of your stones. Stones are never moved or removed.
- The game ends when the **board is full**.

## Winning

The winner is the player whose **single largest connected group** of stones is
larger (stones connect through the 6 hex neighbours). Tie-breaks, in order:

1. Larger single largest group.
2. If equal, **more groups of that size**.
3. If still equal, compare the **second-largest** groups, and so on.

If the two players' full sorted lists of group sizes are **identical**, the game
is an honest **draw**. (On the odd-celled boards a draw is very unlikely but is
handled correctly rather than fabricating a winner.)

## Move notation (this implementation)

A turn is entered as a sequence of single-cell placements by the same player.
Each placement is a cell id `q,r`. The first placement of a turn fixes the
number X; each further placement must be an empty "X" cell, and the UI offers
them in ascending order. While more X cells could still be covered you may play
**done** to stop early. The turn ends automatically once X cells are covered (or
no empty X cells remain). The opening covers one "2" and ends immediately.

Empty cells are drawn as neutral tan discs showing their number; covered cells
are solid discs in the player's colour.

## Notes on sources and interpretation

- **"Up to X" vs "exactly X".** Nick Bentley's rules (as mirrored by Board Game
  Arena) and this port allow covering **up to** X cells ("you may cover fewer").
  igGameCenter and AbstractPlay's open-source engine instead require covering
  **exactly** X (or all remaining "X" cells if fewer than X are left). This port
  follows the designer's stated "up to X"; every exactly-X move is of course
  still legal, so it is a strict superset.
- The numbering, opening-on-a-2 rule, board-fills termination, and the full
  largest-group tie-break chain were verified against igGameCenter, Board Game
  Arena (`Gamehelpstrands`), and the AbstractPlay `gameslib` source.
- No stones are ever captured or moved, so the board strictly fills and the game
  always terminates.
