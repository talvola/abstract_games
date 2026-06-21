# Connect6

A two-player six-in-a-row invented by **Professor I-Chen Wu (2005)**, played on a
Go-style square grid (**13×13** or **19×19**, chosen with the board-size option;
default 19). Player 0 is **Black** and moves first; player 1 is **White**.

## How to play

- **Black's first move:** Black places exactly **one** stone on any empty
  intersection.
- **Every turn after that:** the player to move places exactly **two** stones,
  on any two **distinct empty** intersections. This applies to **both** colours
  on **all** subsequent turns.
- Stones never move and are never captured.
- Players alternate turns: Black (1 stone), White (2), Black (2), White (2), …

The two-stones-per-turn rule is what makes Connect6 **fair**: after the opening,
each player always has a one-stone net "tempo", so neither side gets a runaway
first-move advantage the way unrestricted Gomoku does.

## Winning

A player **wins immediately** upon forming an unbroken line of **six or more**
of their own stones. The line may run:

- **horizontally**,
- **vertically**, or
- **diagonally** (either direction).

Both stones placed on a turn are checked, so a turn can complete (or extend) a
winning line. If the board fills with no six-line, the game is a **draw**.

## Move encoding

Moves use the platform's `>`-separated cell-id path (cells are `"col,row"`,
0-indexed):

- **Opening single-stone move:** a single cell, e.g. `"9,9"`.
- **Normal two-stone move:** the two placements joined by `>`, e.g.
  `"3,3>10,10"`. The two cells must be distinct and empty; their **order does
  not matter**.

In the move log a turn is shown as e.g. `B:10,10` (opening, 1-indexed) or
`W:4,4+11,11` (a two-stone turn).

## Ruleset / implementation notes

- **`legal_moves` is pruned for tractability (a platform choice, not a rule
  change).** The full set of unordered two-empty-cell pairs is huge (~64,000 on
  a 19×19 board), so `legal_moves` returns a **representative, pruned** list: for
  a two-stone turn it forms pairs only among **candidate cells** — empty cells
  within Chebyshev distance 3 of an existing stone (on an empty board, just the
  centre point). This covers all relevant play (a stone placed far from every
  other stone can never contribute to a six-line on that turn) while keeping the
  list a manageable size.
- **`apply_move` accepts ANY legal move**, not just the ones in the pruned list:
  any move placing stones on the correct number of **distinct, empty, on-board**
  cells is applied. So the pruning never forbids a genuinely legal play — it only
  trims the suggestion list the UI/bot iterates over.
- This is **freestyle** Connect6: an **overline** (seven or more) also wins, and
  there are no opening-placement restrictions beyond "Black plays one stone
  first". These match the standard tournament Connect6 rules.
