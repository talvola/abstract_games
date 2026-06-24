# Shako

Jean-Louis Cazaux's 10×10 chess variant (1990). The name means "chess" in
Esperanto. The standard chess army is joined by two pieces from older traditions:
the **Cannon** (from Chinese chess) and the **Elephant** (from medieval shatranj).

## Objective
Checkmate the opponent's king. Stalemate and the usual draw conditions are as in
standard chess.

## Board & setup (10×10)
Files **a–j**, ranks **1–10**. Each side has the full FIDE army (king, queen, 2
rooks, 2 bishops, 2 knights, 10 pawns) **plus 2 Cannons and 2 Elephants** — 22 men
per side.

White:

| rank | a | b | c | d | e | f | g | h | i | j |
|---|---|---|---|---|---|---|---|---|---|---|
| **1** | C | · | · | · | · | · | · | · | · | C |
| **2** | E | R | N | B | **Q** | **K** | B | N | R | E |
| **3** | P | P | P | P | P | P | P | P | P | P |

- **Cannons** sit in the **corners of rank 1**.
- **Elephants** sit in the **corners of rank 2**.
- The rest of rank 2 is the familiar **R N B Q K B N R**, with the **queen on e2**
  and the **king on f2**.
- Pawns fill **rank 3**.

Black mirrors this: pawns on rank 8, the back rank `E R N B Q K B N R E` on rank 9
(queen e9, king f9), and cannons on a10/j10.

## The two new pieces

### Cannon (C)
The **Xiangqi (Chinese-chess) cannon**:
- **Without capturing**, it moves like a **rook** — any distance along an empty
  rank or file (no jumping).
- **To capture**, it must **jump over exactly one piece** (a *screen*, of **either
  colour**) along a straight line and land on the **first enemy piece beyond** it.
  There must be exactly one piece between the cannon's start and the captured
  square. It cannot capture without a screen, and cannot jump two or more pieces.

A cannon gives check the same way: it checks the king if there is exactly one
screen between them on a rank or file.

### Elephant (E)
The **medieval (shatranj) elephant = Ferz + Alfil**:
- It moves **one or two squares diagonally** only.
- The **two-square** move is a **leap**: the intermediate diagonal square may be
  occupied (by anything, of either colour) and is ignored.
- It never moves orthogonally and always stays on its starting square colour.

From a central square an elephant reaches up to **eight** squares: the four
diagonal neighbours (one step) and the four squares two diagonal steps away
(leaping the square in between).

## The standard pieces
King, queen, rook, bishop, knight and pawn move exactly as in orthodox chess.

## Pawns
Pawns step one square forward, or **two from their starting rank** (rank 3 for
White, rank 8 for Black), and capture one square diagonally forward. **En passant**
applies.

## Promotion
A pawn reaching the **far rank** (rank 10 for White, rank 1 for Black) **must**
promote, to the player's choice of **Queen, Rook, Bishop, Knight, Cannon or
Elephant**. There is no captured-piece restriction.

## Castling
Castling follows **orthodox rules** (king and rook unmoved, the squares between
them empty, and the king neither in check nor passing through / landing on an
attacked square). Because the king starts on the **f-file**, the squares are:

- **Kingside:** King f→h, rook i→g (White: f2→h2, rook i2→g2).
- **Queenside:** King f→d, rook b→e (White: f2→d2, rook b2→e2).

Black mirrors on rank 9.

## Winning & draws
Checkmate wins. The game is a draw by **stalemate**, the **fifty-move rule**,
**threefold repetition**, or insufficient material; a hard ply cap guarantees
termination.

## Notes & sources
- Official rules (Cazaux & Bodlaender, refreshed by Cazaux in 2022):
  <https://www.chessvariants.com/rules/shako>.
- The exact castling target files (king→h/d, rook→g/e) are the canonical reading
  of "castling as in orthodox chess" for an f-file king, and match the
  Fairy-Stockfish implementation of Shako. As implemented here the king moves two
  squares toward the rook and the rook hops to the square the king crossed.
- The Elephant is the **Ferz+Alfil** (one *or* two diagonal squares, leaping),
  per the authoritative chessvariants.com text — not a pure (2,2) alfil and not
  orthogonal.
