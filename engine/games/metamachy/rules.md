# Metamachy

Jean-Louis Cazaux's flagship large chess variant (2012), played on a **12×12**
board with 30 pieces per side (12 types). The name is Greek for "beyond the
fight". Checkmate the enemy King to win.

## Setup

Files a–l, White on ranks 1–3 (Black mirrors on the same files on ranks 10–12):

- **Rank 3:** twelve Pawns.
- **Rank 2:** Elephant, Rook, Knight, Bishop, Prince, **Lion (f2)**, **Eagle (g2)**, Prince, Bishop, Knight, Rook, Elephant.
- **Rank 1:** Cannon, Camel, –, –, –, **Queen (f1)**, **King (g1)**, –, –, –, Camel, Cannon.

*In the published game, Black first chooses how to arrange King, Queen, Lion
and Eagle on f12/g12/f11/g11 and White mirrors (12 essentially different
setups). This implementation fixes the standard default array shown above
(the default of the source page's Interactive Diagram).*

## Piece moves

- **King** – one step in any direction (royal). **No castling.** Instead, on
  its **first move only**, the King may leap to an **empty** square exactly two
  king-steps away in any of the 16 directions – orthogonal (like a Dabbaba),
  diagonal (like an Alfil) or knight-wise. It may jump over any piece, but:
  - it may **not** jump while in check;
  - it may not jump **over a threatened square** (a square it could not have
    legally moved to, were it empty). A knight-wise jump passes over *two*
    candidate squares (the orthogonally- and the diagonally-adjacent one) and
    is prevented only if **both** are threatened;
  - the jump never captures, and the destination must be safe as usual.
- **Queen / Rook / Bishop / Knight** – exactly as in orthodox chess.
- **Eagle** (Gryphon/Aanca) – one square diagonally, then any number of squares
  **outward** orthogonally. It may stop after the single diagonal step. It
  cannot jump: an occupied bend square blocks the slide (an enemy there can be
  captured), and the first piece on the slide blocks (enemies capturable).
- **Lion** – leaps directly to **any square within two king-steps** (the 24
  squares at Chebyshev distance ≤ 2, including knight squares). Intervening
  pieces are irrelevant. (The Chu-Shogi "lioness" – no double capture.)
- **Cannon** (Xiangqi) – moves like a Rook but **cannot capture that way**;
  it captures only along an orthogonal line by **jumping over exactly one
  screen** (either colour) and taking the first piece beyond it.
- **Elephant** – one square diagonally, **or** leaps two squares diagonally
  (the intermediate square may be occupied).
- **Camel** – a (1,3) leaper (an "elongated Knight"); jumps over anything.
- **Prince** – a **non-royal** king: moves and captures one square in any
  direction, is not hindered by check, and additionally has the Pawn's
  **non-capturing double step** straight forward from any square (the passed
  square must be empty). A Prince **promotes** like a Pawn on the last rank,
  and a double-stepping Prince can be captured *en passant* by a Pawn – but a
  Prince can **never** capture en passant itself.
- **Pawn** – one square straight forward without capturing; captures one
  square diagonally forward. The **double step is available from any square
  on the board** (not just the home rank); the passed square must be empty.

## En passant

Whenever a Pawn **or Prince** makes a double step and passes through a square
attacked by an enemy **Pawn**, that Pawn may – on the immediately following
move only – capture it as if it had moved just one square. This can happen
anywhere on the board. Only Pawns capture en passant.

## Promotion

A Pawn or Prince reaching the last rank **must** immediately promote to a
**Queen, Eagle or Lion** (free choice; no other piece type is allowed, and
promotion is allowed even to a type not yet captured).

## End of game

- **Checkmate wins.** Moves that leave one's own King in check are illegal.
- **Stalemate is a draw.**
- Draws (as implemented, to guarantee termination): 50 moves without a capture
  or pawn move, threefold repetition, a hard 800-ply cap, and dead positions
  (bare kings, or a lone Bishop/Knight/Elephant/Camel).

## Implementation notes / interpretations

- **Fixed setup:** the initial free placement of King/Queen/Lion/Eagle (Black
  chooses, White mirrors) is **not** implemented; the standard default array
  (Q f1, K g1, Lion f2, Eagle g2) is used, per the Interactive Diagram on the
  source page.
- The King-jump intermediate-square rule follows the source's wording: the
  square jumped over is tested as if the King had legally moved onto it *with
  that square emptied* (so a jump stays illegal if an enemy line to that
  square opens once the King leaves its own square).
- A double step that lands **on the last rank** promotes immediately and does
  not create an en-passant opportunity (no legal e.p. reply can exist there).
- The 50-move counter resets on captures and **Pawn** moves (Prince moves do
  not reset it); termination is guaranteed by the repetition and ply-cap rules
  regardless.

Sources: [chessvariants.com/rules/metamachy](https://www.chessvariants.com/rules/metamachy)
(H.G. Muller & J.-L. Cazaux) and
[Cazaux's own page](http://history.chess.free.fr/metamachy.htm).
