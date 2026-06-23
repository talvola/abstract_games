# Clobber

**Clobber** is a two-player combinatorial game invented by Michael Albert, J.P.
Grossman, Richard Nowakowski, and David Wolfe (2001). It is a favourite test-bed
for combinatorial game theory (CGT): every position decomposes into independent
regions, so it is studied with game values and the *temperature theory* of CGT.

## Board and setup

The board is a rectangular grid. The default is **5×6**; a **Board size** option
also offers 6×5, 4×5, and 8×8. Cells are addressed `c,r` (column, row), both
0-based.

At the start **every cell holds a stone** in a strict **checkerboard** pattern:

- cell `c,r` with `c + r` **even** → **Player 1** (player 0)'s stone,
- cell `c,r` with `c + r` **odd** → **Player 2** (player 1)'s stone.

So no two same-colour stones are orthogonally adjacent at the start, and the board
is completely full. Player 1 moves first.

## The move (the only move)

On your turn you **pick one of your own stones and move it onto an orthogonally
adjacent cell that holds an *opponent's* stone**. The opponent's stone is removed
("clobbered") and your stone occupies that cell.

- Movement is one step **up, down, left, or right** — never diagonal.
- The destination must hold an **enemy** stone. You may **not** move onto an empty
  cell, onto your own stone, or onto a non-adjacent cell.
- There are **no non-capturing moves**: a stone only ever moves by clobbering an
  adjacent enemy. Every move therefore removes exactly one stone from the board.

Move notation is the cell path `c,r>c2,r2` (e.g. `2,1>2,2`).

## Goal — normal play (last to move wins)

Clobber uses the **normal-play** convention: **the player who cannot move loses.**
Equivalently, the last player to make a legal move wins. A player is unable to move
when none of their stones has an orthogonally adjacent enemy stone (including when
they have no stones left).

There are **no draws**, and the game always ends: each move removes exactly one
stone, so play lasts at most (number of cells − 1) moves and can never cycle.

## Notes / implementation choices

- Both standard rectangular orientations are offered via the `size` option (5×6
  and 6×5 are different starting checkerboards because the corner colour differs);
  4×5 and 8×8 are included as smaller/larger study boards. To keep things faithful
  the board is always completely filled in the canonical `(c+r) % 2` checkerboard.
- The result is decided purely by who is stuck (normal play); the engine does not
  score by material or compute CGT values — it simply detects the no-move terminal.
- Small fully-solved cases (used as the package's correctness anchor): 1×2, 1×3,
  1×4, 2×2, and 3×3 are wins for the first player, while **2×3 is a win for the
  second player**.
