# Veletas

Luis Bolaños Mures, 2013 (nestorgames). A drawless territory game, a close
relative of Amazons, played with **shared neutral shooters** ("veletas" =
weathervanes). Won the BGG Best Combinatorial 2-Player Game of 2013 Award.

Rules as implemented, from the official rulebook
([nestorgames PDF](https://nestorgames.com/rulebooks/VELETAS_EN.pdf)).

## Board and material

- **10×10** board with **7 shooters** (the official game), or the rulebook's
  suggested shorter variants: **9×9 / 5 shooters** (the default here) and
  **7×7 / 3 shooters**. Pick via the *Board size* option.
- Shooters are neutral (shown as green ✦); both players use them.

## Setup (pie rule)

1. **Player 1** places the first shooters — 3 on 10×10, 2 on 9×9, 1 on 7×7 —
   and then **one Black stone**, all on empty squares. Setup shooters may
   **not** be placed on the board perimeter (the stone may).
2. **Player 2** then chooses sides: **swap** (take Black, i.e. adopt the
   placed stone and move first) or **stay** (keep White).
3. **White** places the remaining shooters (4 / 3 / 2, again not on the
   perimeter) and then **one White stone**.

From then on the players alternate turns, **Black first**. The perimeter
restriction applies only to the setup — shooters may later *move* to the edge.

## Your turn

1. *(Optional)* **Move one unclaimed shooter** like a chess queen (any
   distance, straight orthogonal or diagonal line) to an **empty** square.
   The path may jump over shooters (claimed or unclaimed) but **never over
   stones**; it may not land on any piece.
2. *(Mandatory)* **Shoot**: place a stone of your colour on an empty square a
   straight queen-line away **from the shooter you just moved** — or **from
   any unclaimed shooter** if you moved none — with no stones in between
   (shooters in between are fine). Claimed shooters cannot move or shoot.

## Claiming shooters

A shooter is **trapped** when it has no legal move (no queen-line empty
square, jumping shooters but blocked by stones/edges — note this also means
it could not shoot). After your shot, **every trapped unclaimed shooter is
claimed**:

- by the player who owns the **biggest group of stones orthogonally adjacent**
  to it (a *group* = like-coloured, orthogonally connected stones; diagonal
  contact does not count, and claim markers are not part of any group);
- if there is **no adjacent group**, or the biggest groups of each colour are
  **the same size**, it is claimed by the **opponent of the player who just
  moved** (so trapping a shooter without winning the surround gives it away).

Claimed shooters are marked in the claimer's colour and never change again.

## Winning

Claim a **majority** of the shooters: **4 of 7** (10×10), **3 of 5** (9×9),
**2 of 3** (7×7). Per the rulebook, **draws are not possible**: shooter counts
are odd, every turn adds a stone to a finite board, and a trapped shooter
never survives a turn unclaimed, so a shot is always available until someone
reaches the majority.

## Notation (this implementation)

- Setup: click empty squares (shooters first, then the stone).
- Pie choice: the **swap** / **stay** buttons.
- Turn: click a shooter, its destination, then the shot square
  (`from>to>shot`) — or just click the shot square to shoot without moving.
- Seat colours in the UI are fixed (Player 1 red, Player 2 blue); the caption
  tracks who is Black/White after the pie choice.
