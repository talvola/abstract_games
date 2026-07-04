# Omega Chess

Daniel MacDonald (1992). Standard chess plus two new leapers on a 104-square
board. White moves first; checkmate wins.

## Board

A 10×10 playing field (files **a–j**, ranks **0–9** in official notation) plus
four **wizard squares** (w1–w4), one attached diagonally beyond each corner.
The wizard squares are ordinary squares of the board — any piece may occupy
them, though pawns and rooks can never reach one (their moves simply never
get there).

## Setup

- First rank (White rank 0, Black rank 9), files a–j:
  **Champion, Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook, Champion.**
- Ten pawns on each player's second rank.
- A **Wizard** on each of the player's two corner wizard squares.

## Pieces

- **King, Queen, Rook, Bishop, Knight** — exactly as in standard chess.
- **Champion** — a leaper: steps **one square orthogonally**, or jumps **two
  squares orthogonally or diagonally** (over anything in between). It cannot
  step one square diagonally.
- **Wizard** — a leaper: steps **one square diagonally**, or makes a
  **(1,3) camel jump** (over anything in between). Colour-bound, like a bishop.

## Pawns

- A pawn may advance **1, 2 or 3 squares straight forward on its first move
  only** (no jumping over pieces); afterwards one square at a time.
- Pawns capture one square diagonally forward, as in chess.
- **En passant:** a pawn that just advanced 2 or 3 squares may be captured en
  passant on **any square it passed over** (a 3-step pawn leaves two such
  squares). The capturing pawn moves onto the passed square and the moved pawn
  is removed. Only available on the immediately following move.
- **Promotion:** on reaching the far rank of the 10×10 field (rank 9 for
  White, rank 0 for Black) a pawn immediately promotes to any piece except a
  king: Queen, Champion, Wizard, Rook, Bishop or Knight.

## Castling

As in standard chess: the king moves **two squares** toward either rook and
that rook lands on the square the king crossed (White: king f0→h0 with the
i0-rook to g0, or king f0→d0 with the b0-rook to e0; Black likewise on rank 9).
Requires that the king and that rook have never moved, the squares between
them are empty, the king is not in check, and the king does not cross or land
on an attacked square.

## End of the game

- **Checkmate** wins.
- **Draws:** stalemate, threefold repetition, the 50-move rule (no capture or
  pawn move), or insufficient material (bare kings, or a lone knight/bishop —
  neither can force mate even on 10×10; Champions and Wizards always count as
  mating material since pairs of them can mate here).

## Notes on this implementation

- Cell ids embed the board in a 12×12 grid: the 10×10 field is columns/rows
  1–10 and the wizard squares are the four extreme corners. The move log uses
  the official notation (files a–j, ranks 0–9, wizard squares w1–w4).
- Omega Chess *Advanced* (the fool, guarding, templar knight) is not included.

Source: the official rules at chessvariants.com (used with the inventor's
permission) and the Wikipedia article on Omega Chess.
