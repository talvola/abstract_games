# Onitama

Onitama (Shimpei Sato, 2014) is a sharp little chess-like duel where **cards**, not
the pieces, decide how you may move. These are the rules **as implemented** here.

## Setup

A 5×5 board. Each player has **five pawns and a master** on their back row, the
master in the centre. From a deck of 16 **movement cards**, five are dealt: two to
each player and one to the **middle**. (The deal is random; everything is then
open information.) Player 1 (red, bottom) moves first.

## A turn

Your turn has two steps:

1. **Pick one of your two cards** (click it in the card strip).
2. **Move one of your pieces** by one of the offsets shown on that card. Each card
   shows a 5×5 pattern: the centre square is the piece, the highlighted squares are
   where it may go (the pattern is shown oriented toward its owner).

Landing on a piece — yours never, the enemy's to **capture** it — ends the move.
Then the card you used goes to the **middle**, and you take the card that was in
the middle into your hand. (If you have no legal move at all, you must still pass a
card to the middle.)

## Winning

Two ways to win:

- **Way of the Stone** — capture the enemy **master**.
- **Way of the Stream** — move your **master** onto the square where the enemy
  master started (its temple).

## Notation

A card pick shows as `pick <Card>`; a move shows as `<Card> from-to` (or `from x to`
for a capture). The master is drawn as `K`, pawns as `·`, in each player's colour.
