# Makruk (Thai chess)

Makruk is the traditional chess of Thailand, played on an 8x8 board. It descends
from the same medieval ancestor as chess and shatranj, and is close in feel to
the older European game (short-range queen and bishops). **White (player 0) moves
first.**

## Board and setup

```
8  r n s k m s n r      (Black)
7  . . . . . . . .
6  b b b b b b b b      Black Bia (pawns), 6th rank
5  . . . . . . . .
4  . . . . . . . .
3  B B B B B B B B      White Bia (pawns), 3rd rank
2  . . . . . . . .
1  R N S M K S N R      (White)
   a b c d e f g h
```

Each side has, on its back rank: two **Ruea** (rooks), two **Ma** (knights), two
**Khon** (silver-generals), one **Met** (queen), and one **Khun** (king). The
**Bia** (pawns) start on the **third rank** (rank 3 for White, rank 6 for Black).

The Khuns stand opposite each other (White's Khun on e1, Black's on d8) so the two
Khuns share a file and the two Mets share a file.

## How the pieces move

- **Khun (King)** — moves one square in any of the eight directions, exactly like
  a chess king. It may not move into check. **There is no castling.**
- **Met (Queen)** — moves **one square diagonally only** (a *ferz*). This is a
  weak piece, much shorter-ranged than a chess queen.
- **Khon (Silver General / "bishop")** — moves **one square diagonally in any of
  the four diagonal directions, or one square straight forward** — five
  destinations in all. It cannot move straight backward or sideways, so its move
  is *directional* and depends on which side owns it.
- **Ruea (Rook)** — moves any distance orthogonally, exactly like a chess rook.
- **Ma (Knight)** — moves like a chess knight (the (1,2) leap), and can jump over
  pieces.
- **Bia (Pawn)** — moves **one square straight forward** (never two — there is
  **no double step** and therefore **no en passant**), and **captures one square
  diagonally forward**.

All pieces capture by moving onto an enemy piece (the Bia only on its diagonal
capture squares).

## Bia promotion

When a **Bia reaches the sixth rank** (rank 6 for White, rank 3 for Black) it
**promotes to a Met**. Promotion is mandatory and the Bia can only become a Met
(there is no choice of piece). In the move notation this is written with a `=M`
suffix.

> Note: in this implementation a Bia promotes immediately upon reaching the sixth
> rank, the most common modern Makruk rule. (Some historical descriptions promote
> on the square a friendly Bia originally stood; that variant is not used here.)

## Winning, check, and draws

- **Check / Checkmate** — the Khun may not be left in check. **Checkmating the
  enemy Khun wins the game.**
- **Stalemate is a draw** — if the side to move has no legal move and is not in
  check, the game is drawn.
- **Termination / no-progress** — to guarantee the game ends, this package also
  draws on a hard ply cap and a long no-progress (no capture / no Bia move) count.

### Counting rules: omitted

Traditional Makruk has an elaborate **counting / honour-counting** procedure that
forces the stronger side to deliver mate within a bounded number of moves in
material-up endgames, otherwise the game is drawn. **This package omits the
counting rules.** In their place, to keep every game finite, a position with
**insufficient mating material** (e.g. a bare Khun, or a lone Met / Khon / Ma that
cannot force mate) is scored as a **draw**, alongside the ply and no-progress
caps. This is a deliberate simplification noted here as the one ruleset choice
made in this implementation.

## Notation

Moves are entered as a `from>to` cell path (click the piece, then its
destination); a promoting Bia move carries a `=M` suffix, e.g. `0,4>0,5=M`.
