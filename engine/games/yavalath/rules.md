# Yavalath

A two-player game by **Cameron Browne**, discovered in November 2007 by the
**LUDI** system — an evolutionary game-design program guided by Browne — and
published by nestorgames. It is one of the first commercially published games
designed (in part) by a computer. Yavalath is the **hex analogue of Squava**: a
*misère/positive hybrid* n-in-a-row where one length of line wins and a shorter
one loses.

## Board

The board is a **hexagon of hexagons** (a "hexhex") of **side 5 = 61 cells**.
Cells are addressed with **axial coordinates `q,r`**; the implied third cube
coordinate is `s = -q-r`, and a cell is on the board iff
`max(|q|, |r|, |s|) <= 4`. Each interior cell has the **6 hex neighbours**.

The three line directions ("rows") run along the **three hex axes**:

- `q` axis: `(q+1,r)` / `(q-1,r)`
- `r` axis: `(q,r+1)` / `(q,r-1)`
- `s` axis: `(q+1,r-1)` / `(q-1,r+1)`

## How to play

- White moves first; players alternate placing **one stone of their colour on
  any empty cell**.
- Stones **never move and are never captured** (exactly like Hex or Gomoku) —
  the game is **placement only**.

## Winning and losing

After you place a stone, the lines running through it along the three hex axes
are evaluated as the **longest unbroken run** of *your* stones through that cell:

- If you now have **four or more** in a row, you **WIN** immediately.
- Otherwise, if you now have **exactly three** in a row (and no four), you
  **LOSE** immediately. This is the misère twist: you are **forbidden from making
  three-in-a-row unless it is part of a four**.

### Four takes precedence

If a single placement creates a three **and** a four at the same time (a line of
four necessarily contains a sub-run of three), it counts as a **four — and
therefore a WIN**. A four always beats a three; you are only punished for a three
that is *not* part of a four. Because the implementation tests the *longest* run
through the placed stone, a run of length ≥ 4 always reports a win before any
three is considered.

Only the **player who just moved** can win or lose on that placement — the
outcome is always judged from the just-placed stone. You cannot lose because of a
three formed by your opponent.

## Draw

If the board fills with all **61** stones placed and no four was ever made and no
losing three ever decided the game, the result is a **draw**. Because there is no
movement and no capture, the game always ends within 61 placements.

## Ruleset notes (as implemented)

- **Overlines** (five or more in a row) are treated like any other four-or-more
  and **win**.
- **Pie / swap rule (option, default ON).** Yavalath has a known first-player
  advantage. To balance it, the second player, on their *first* turn only, may
  play the action move **`swap`** instead of placing: this adopts White's opening
  stone as their own (it becomes the swapper's colour) and passes the move back.
  This mirrors the platform's other placement games. Set the **Pie (swap) rule**
  option to *Off* for the strict base game with no swap.

## Source

Designed by Cameron Browne via the LUDI system (2007); published by nestorgames.
See the [BoardGameGeek page](https://boardgamegeek.com/boardgame/33767/yavalath).
