# Zanzibar-XL

Jean-Louis Cazaux's large chess variant (2020), played on a **12×12** board with
**80 pieces of 19 types** (40 per side). It sits between the smaller Zanzibar-S
and the larger Zanzibar-XXL (Maasai Chess). Checkmate the enemy King to win.

## The armies

Each side has 1 King, 1 Queen, 1 Eagle, 1 Lion, 1 Duchess, 1 Sorceress,
1 Rhinoceros, 1 Buffalo, 2 Princes, 2 Bishops, 2 Knights, 2 Camels, 2 Rooks,
2 Cannons, 2 Elephants, 2 Giraffes, 2 Archers, 2 Machines and 12 Pawns.

## Setup

The paired pieces and pawns start on a fixed formation (files a–l = columns
0–11; White on ranks 1–4, Black mirroring on ranks 9–12):

- **Rank 1:** Cannon, Camel, Giraffe, Archer, –, –, –, –, Archer, Giraffe, Camel, Cannon
- **Rank 2:** Elephant, Rook, Knight, Bishop, –, –, –, –, Bishop, Knight, Rook, Elephant
- **Rank 3:** Pawn ×4 (a–d), Prince, Machine, Machine, Prince, Pawn ×4 (i–l)
- **Rank 4:** Pawn ×4 (e–h)

The centre files e–h on ranks 1–2 are left empty for the eight **chiefs**.

**Then Black arranges the chiefs.** Black freely places its **King, Queen,
Eagle and Lion** on the four centre squares **f12, g12, f11, g11**, and its
**Duchess, Sorceress, Rhinoceros and Buffalo** on the four flank squares
**e12, h12, e11, h11**. White's chiefs are then placed in mirror symmetry (Black
King on f12 → White King on f1) and **White makes the first move**. This balances
White's first-move advantage against Black choosing the position. There are 288
essentially different starting setups.

*In this implementation the arrangement is a sequence of explicit placement moves
by Black (its reserve is shown as a drop tray, and the legal target squares are
tinted); the mirror is applied automatically once Black has placed all eight
chiefs.*

## Piece moves

- **King (K):** one step in any of the 8 directions, to a square not attacked.
  **No castling.** Instead, on its **first move only**, the King may leap to an
  empty square two squares away in any of the 16 directions (orthogonal, diagonal
  or knight-wise), jumping over any occupant. The jump is forbidden while in
  check and forbidden over a *threatened* square; a knight-wise jump has two
  intermediate squares and needs only **one** of them safe.
- **Queen (Q):** slides any distance orthogonally or diagonally (as in chess).
- **Rook (R) / Bishop (B) / Knight (N):** as in chess.
- **Eagle (G):** one step diagonally, then an outward orthogonal slide of any
  distance. It may stop after the diagonal step; it never jumps, and the path
  must start with the diagonal step. (Inspired by the Aanca of Grande Acedrex.)
- **Rhinoceros (U):** the Eagle's counterpart — one step orthogonally, then an
  outward diagonal slide of any distance.
- **Lion (L):** moves as a King, or leaps two squares away in any orthogonal
  (Dabbaba), diagonal (Alfil) or knight direction — i.e. to any of the 24 squares
  within two king steps. Blocking is irrelevant. (No double move.)
- **Elephant (E):** one step diagonally, or a two-square diagonal leap over the
  intermediate square (Ferz + Alfil). Stays on one colour.
- **Camel (A):** a (1,3) leaper. Stays on one colour.
- **Giraffe (Z):** a (2,3) leaper (a "zebra").
- **Machine (W):** one or two squares orthogonally, leaping the first square if
  it is occupied (Wazir + Dabbaba — the orthogonal counterpart of the Elephant).
- **Duchess (D):** steps or leaps one, two or three squares in any of the eight
  queen directions, jumping over any intermediate squares on a 2- or 3-step.
- **Buffalo (F):** combines the leaps of the Knight (2,1), Camel (3,1) and
  Giraffe (3,2).
- **Cannon (C):** as in Xiangqi — moves without capturing like a Rook; captures
  by hopping over exactly one screen (of either colour) along a rank or file and
  taking the first piece beyond it.
- **Archer (V):** the diagonal Cannon (Vao) — moves without capturing like a
  Bishop; captures by hopping over one screen along a diagonal.
- **Sorceress (O):** the queen-line Cannon (Cannon + Archer) — moves without
  capturing like a Queen; captures by hopping over one screen along any rank,
  file or diagonal.
- **Prince (M):** a non-royal King — moves and captures one square in any
  direction (it is not hindered by check). Like a pawn it may also make a
  non-capturing double step straight forward from any square. Promotes.
- **Pawn (P):** steps one square straight forward without capturing; captures one
  square diagonally forward; and may make a **non-capturing double step from any
  square** (the passed square must be empty).

## Promotion and en passant

- A **Pawn or Prince** reaching the last rank is immediately replaced by a chief:
  **Queen, Eagle, Lion, Duchess, Sorceress, Rhinoceros or Buffalo** (free choice;
  no other type). Promotion to a type still on the board is allowed.
- **En passant:** when a Pawn or Prince takes a double step through the capture
  square of an enemy Pawn, that Pawn may capture it en passant on the very next
  move. Only a **Pawn** may capture en passant; the Prince may not.

## Ending

Checkmate wins. Stalemate is a draw. This port also draws by the 50-move rule,
threefold repetition, bare kings (or a lone piece that cannot mate) and a hard
ply cap (a safety net that does not affect normal play).

## Implementation notes / interpretations

- The port fixes no default array: Black actually chooses the setup as described.
  The 288-setup symmetry argument (King on the f- or g-file being equivalent) is
  not enforced — every arrangement within the centre/flank groups is offered,
  which is faithful (the "288" merely counts equivalence classes).
- The optional Marshal/Cardinal variant (an older version using a Marshal and
  Cardinal instead of the Duchess and Sorceress) is **not** implemented.
- The "good etiquette" suggestion to avoid promoting to an uncaptured type is a
  courtesy, not a rule, and is not enforced.

*Official source:* <https://ftp.chessvariants.com/rules/zanzibar-xl>
