# Emulsion

By **Luis Bolaños Mures** (2020). 2 players. Rules as implemented here, from the
designer's own Zillions of Games edition (its ReadMe is the authoritative text).

## Setup

An **n×n** board (choose 7–14; default 9) starts **completely full** of black and
white pieces in a checkered pattern. On odd-sized boards the **centre square is
White** (so the corners are White too). **Black moves first.**

## Definitions

- A piece's **value** = the number of pieces of its own colour **orthogonally**
  adjacent to it, **plus half** the number of board edges adjacent to its square
  (a corner square adds 1, any other rim square adds ½).
- A **group** = a maximal set of same-coloured pieces connected **orthogonally**.
  Its size is its number of pieces.

## Play

On your turn, **swap two orthogonally or diagonally adjacent pieces of different
colours** so that **the value of your piece in the pair increases** (its value
after the swap must be strictly greater than before).

Because the board is always full, a swap changes both pieces' values by exactly
the same amount — so at every position **both players have the same set of
available swaps** (the designer notes this in the Zillions edition).

*Click your own piece, then the adjacent enemy piece to swap with.*

## End of the game and scoring

The game **ends when no swaps are available** (this happens for both players at
once — there is no passing).

Your **score is the size of your largest group**. If scores are tied, each
player adds the size of their **second-largest** group, then the third-largest,
and so on. **On even-sized boards, if the tie persists all the way down, the
player who made the last move wins.** (On odd boards a full tie is impossible,
because the two colours have different piece counts.)

## Source note (documented interpretation)

The designer has published two slightly different rule texts. This port follows
his **Zillions of Games edition** (submission #3089, 2020-10-31): full tie on an
even board → the **last mover wins**, and there is no pie rule. His current
**BoardGameGeek description** states the opposite tiebreak (the last mover
*loses*, phrased as pairwise removal of equal groups until the board is empty —
otherwise equivalent to the recursive comparison above) and adds a pie rule for
White. On the default 9×9 (odd) board the tiebreak never triggers either way.

## Implementation notes

- Every legal swap strictly increases a bounded whole-board potential
  (same-colour adjacencies plus the edge bonuses), so the game is provably
  finite. A generous ply cap (4·n²+100) is kept purely as a safety backstop and
  would score an honest draw; it is unreachable in normal play.
- In the theoretical corner case of a full tie with no move ever having been
  made (no "last mover"), the result is a draw — also unreachable, since the
  initial position always has legal swaps.
- Move notation: `from>to`, your own piece first.
