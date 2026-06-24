# Grasshopper Chess

Grasshopper Chess (introduced by **Joseph Boyer**, 1950s) is standard chess with one
extra piece type — the **grasshopper** — and an extra rank of them in the opening
setup. It is one of the best-known "fairy chess" armies.

## Board and setup

A normal 8×8 chess board. The orthodox army is unchanged, plus each side gets **8
grasshoppers** placed directly in front of its pawns:

- **White:** back rank (row 1) R N B Q K B N R; pawns on rank 2; **grasshoppers on
  rank 3**.
- **Black:** mirror image — pawns on rank 7; **grasshoppers on rank 6**; back rank
  (row 8) r n b q k b n r.

So each side starts with 24 men (8 back-rank pieces, 8 pawns, 8 grasshoppers).

A consequence of this setup worth knowing: at the very start, every pawn is blocked
by the grasshopper in front of it and the knights have nowhere to jump (their rank-3
squares are occupied by friendly grasshoppers). **The only opening moves are
grasshopper hops** — this is the game's signature.

## The grasshopper (G)

The grasshopper moves along the eight **queen lines** (the four orthogonals and four
diagonals), but it moves *only by hopping*:

1. Look along a chosen queen line from the grasshopper.
2. The first piece encountered on that line is the **hurdle** (it may be of either
   colour).
3. The grasshopper lands on the square **immediately beyond** the hurdle:
   - if that square is **empty**, it is a quiet move;
   - if it holds an **enemy** piece, it is a **capture**;
   - if it holds a **friendly** piece, or lies off the board, that direction is
     **blocked** (no move).
4. If a queen line contains **no piece at all**, the grasshopper has **no move** along
   that line. (Unlike a queen, it cannot move to an empty open line.)

A grasshopper therefore moves only next to a hurdle: it always lands one square past
the nearest man in the chosen direction. A king, a pawn, an enemy piece — anything —
can serve as the hurdle.

**Grasshoppers give check** exactly the way they move: a grasshopper checks the enemy
king if it could legally hop onto the king's square (i.e. there is a hurdle directly
beside the king, on the line toward the grasshopper, and the grasshopper is the first
piece beyond that hurdle).

## Everything else is orthodox chess

- **Pawns:** ordinary moves, double-step from the home rank, en passant, and
  promotion to **Q / R / B / N** on the last rank (no promotion to a grasshopper).
- **King, queen, rook, bishop, knight:** unchanged.
- **Castling:** standard king-side and queen-side (the squares between king and rook
  must be empty and the king may not pass through check).
- **Winning / drawing:** checkmate wins; stalemate is a draw. Draws also occur by the
  fifty-move rule and threefold repetition. A hard ply cap guarantees termination.

## Implementation note (interpretation)

- **Insufficient-material auto-draw is disabled.** A lone grasshopper's mating value
  is unclear, so this engine never declares an automatic material draw; the
  fifty-move rule and ply cap still guarantee the game ends.
- The grasshopper is rendered with the label **"G"**.

Official source: the grasshopper / Grasshopper Chess article on
[chessvariants.com](https://www.chessvariants.com/diffmove.dir/grasshopper.html)
and Wikipedia's "Grasshopper (chess)".
