# Gross Chess

Fergus Duniho's 2009 "natural extension of Chess" to a **12×12** board (144 squares = one gross). Files are `a`–`l`, ranks `1`–`12`. White (player 0) moves up the board. Everything is FIDE chess except as noted below.

## Setup

- **Rank 1 / 12** (a→l): Marshall, Archbishop, Vao, Wizard, Cannon, —, —, Cannon, Wizard, Vao, Archbishop, Marshall (f and g empty).
- **Rank 2 / 11** (a→l): —, Rook, Champion, Knight, Bishop, Queen, King (g-file), Bishop, Knight, Champion, Rook, — (a and l empty).
- **Rank 3 / 10**: twelve Pawns.

## Pieces

- **King (K)** — one square any direction; royal. Castles (see below).
- **Queen (Q)** — rook + bishop.
- **Marshall (M)** — rook + knight.
- **Archbishop (A)** — bishop + knight.
- **Rook (R)**, **Bishop (B)**, **Knight (N)** — as in chess.
- **Champion (S)** — leaps 1 square orthogonally, or exactly 2 squares orthogonally or diagonally (wazir + dabbaba + alfil; Omega Chess).
- **Wizard (W)** — one square diagonally, or a (1,3) camel leap (ferz + camel; Omega Chess). Colorbound.
- **Cannon (C)** — moves (without capturing) like a rook; **captures only by hopping** along a rook line over exactly one intervening piece of either colour (the screen) and taking the first piece beyond it.
- **Vao (V)** — moves like a bishop; captures by the same hop rule along diagonals.
- **Pawn (P)** — steps one square straight forward, captures one square diagonally forward. See below for initial moves, en passant and promotion.

## Pawns

- **Initial move**: from its starting rank a pawn may advance one, two or **three** squares (all squares passed must be empty).
- **En passant** (Omega-Chess style): after a double or triple step, an enemy pawn may capture the mover on **any square it passed over** — the capturer steps one square diagonally forward onto a passed square and the moved pawn is removed from where it landed. Only on the immediately following turn.
- **Promotion** (Grand-Chess style, on the last three ranks, only to a piece "held in reserve"):
  - The reserve = the player's captured pieces **plus** extras of 2 Queens, 4 Rooks, 4 Knights and 4 Bishops. Implemented as a cap: you may never have more pieces of a type in play than its pool (starting count + extras): Q 3, R 6, N 6, B 6, M/A/S/C/V/W 2 each.
  - **10th rank** (3rd-last): optional; only Bishop, Knight, Vao or Wizard.
  - **11th rank** (2nd-last): optional; those plus Champion, Cannon or Rook.
  - **12th rank** (last): compulsory; any available piece including Queen, Marshall, Archbishop.

## Castling

Flexible (Grotesque-Chess) castling: the king (g-file) moves **two or more** squares along its rank toward one of its rooks (b- or k-file), and that rook leaps over the king to the passed square nearest it, so king and rook end adjacent. Kingside the king may go to i or j; queenside to e, d or c. Conditions: neither king nor that rook has moved; **all** squares strictly between king and rook are empty; the king is not in check and does not pass through or land on an attacked square.

## End of game

- **Checkmate wins.** Stalemate is a draw.
- Draws: 50-move rule (100 halfmoves without a capture or pawn move), threefold repetition, bare kings or a lone minor piece (B/N/W/V/C — none can mate alone), and a hard 1000-ply cap (termination guarantee).

## Implementation notes / interpretations

- Promotion "reserve" is tracked as the per-type cap above (exactly equivalent to captured-pieces-plus-extras accounting, and the same approach the source's Grand Chess reference uses).
- Insufficient-material is claimed **conservatively** (bare kings or one lone minor). Pairs that the source's mating table says cannot mate (e.g. two Vaos, same-colour Bishop+Wizard) are not auto-drawn; the 50-move/repetition rules end those games.
- Source of truth: [Gross Chess at chessvariants.com](https://www.chessvariants.com/large.dir/gross.html) (the author's own page).
