# Reversi (Othello)

A two-player game on an **8×8** board (or **10×10** with the size option). Player 0
is **Black** and moves first; player 1 is **White**. The four centre cells start
filled diagonally (two of each colour).

## How to play

- On your turn, place one of your discs on an **empty** cell so that it
  **brackets** at least one straight line of opponent discs: starting from the
  new disc, in one or more of the eight directions, a run of one or more opponent
  discs must be capped by one of **your** discs.
- Every opponent disc in every bracketed line **flips** to your colour.
- If you have **no legal placement**, you must **pass**. A pass is only available
  when your opponent still has a move.

## Ending and winning

The game ends when **neither player can move** (usually a full board). The player
with **more discs** wins; an equal split is a **draw**. (Under the *Anti / misère*
goal option, this is reversed — see below.)

## Board size (option)

- **8×8 (standard)** — the default Othello board.
- **10×10 (Grand Othello)** — the larger board, otherwise identical rules. The
  four centre cells (e5/f5/e6/f6-equivalent) start filled diagonally.

## Goal (option)

- **Standard (most discs)** — the default; the player with more discs at the end
  wins.
- **Anti / misère (fewest discs)** — *Anti-Othello*; the player with **fewer**
  discs at the end wins. An equal split is still an honest **draw**.

## Opening (option)

- **Othello (fixed centre)** — the default. The four central squares start filled
  diagonally (two of each colour), as in the commercial Othello game.
- **Reversi (open centre)** — the original game. The board starts **empty**; the
  first four moves are placed into the **four central squares**, alternating, with
  **no captures**. Players choose where, so the centre can end up diagonal or
  "parallel". Normal flipping play begins once the centre is full.

## Notes

- Aside from the opening, both variants play identically. The score (Black–White
  disc count) is shown in the caption while you play.
