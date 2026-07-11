# Tamerlane Chess

The great chess (*shatranj kamil / shatranj al-kabir*) played at the court of
Timur (Tamerlane, 1336–1405). Two players; White moves first.

## Board

11 files (a–k) × 10 ranks, uncheckered historically, **plus two citadels**:
one protruding left of rank 9 (Black's citadel, id `0,9`) and one right of
rank 2 (White's citadel, id `12,2`). White sits on ranks 1–3.

**Setup (White; Black mirrors by 180° rotation, kings facing on the f-file):**

- Rank 1: Elephant a1, Camel c1, War engine e1/g1, Camel i1, Elephant k1 (gaps between).
- Rank 2: Rook, Knight, Picket, Giraffe, General, **King f2**, Vizier, Giraffe, Picket, Knight, Rook.
- Rank 3 (pawns): of pawns a3, of war engines b3, of camels c3, of elephants d3,
  of generals e3, **of kings f3**, of viziers g3, of giraffes h3, of pickets i3,
  of knights j3, of rooks k3.

## Pieces

- **King (K)** – one step any direction. **Once per game, when checked**, it may
  exchange places with any friendly non-royal piece (if that resolves the check).
- **General / ferz (F)** – one step diagonally.
- **Vizier / wazir (V)** – one step orthogonally.
- **Giraffe (G)** – one square diagonally, then a **minimum of three** squares
  straight, continuing outward along either component; every passed square
  (including the diagonal one) must be empty. Not a jumper.
- **Picket / talia (T)** – a bishop that must move **at least two** squares
  (the first square must be empty to pass through).
- **Knight (N)**, **Rook (R)** – as in modern chess.
- **Elephant / alfil (E)** – jumps exactly two squares diagonally.
- **Camel (C)** – (3,1) leaper (a stretched knight). Jumps.
- **War engine / dabbaba (W)** – jumps exactly two squares orthogonally.
- **Pawns** (labels `pX`) – move and capture like modern pawns but with **no
  double step and no en passant**. Each pawn belongs to a piece type.

## Promotion (mandatory, on the last rank)

Each pawn promotes to **its own piece**: the pawn of rooks becomes a rook, etc.
Two exceptions:

- **Pawn of kings (`pK`)** promotes to a **Prince (Pr)** – an extra royal that
  moves as a king.
- **Pawn of pawns (`pP`)**, three stages:
  1. On first reaching the last rank it **stays there, immune from capture**
     (shown as `p2`). From there its only moves are *placements*: it may be put
     on any square where it **forks two enemy pieces** or attacks one enemy
     piece that **cannot escape being taken**. The placement may displace any
     occupant (friendly or enemy, never a royal), which is removed. It then
     plays on as a normal pawn.
  2. On reaching the last rank a second time it is **immediately moved to the
     pawn of kings' starting square** (f3 / f8) and plays on (shown as `p3`).
     If that square is occupied, the move to the last rank is not available.
  3. On reaching the last rank a third time it becomes an **Adventitious King
     (AK)** – another royal that moves as a king.

## Royals, check, and winning

Royal rank: **King > Prince > Adventitious King**. While a player owns two or
more royals **there is no check**: royals may be moved or left en prise and are
captured like ordinary pieces. Only when a single royal remains do
check/checkmate rules apply to it (whatever its type — it "takes the role of
king").

- **Checkmate wins. Stalemate also wins** (the player with no legal move loses,
  in check or not).
- There is **no baring rule** (following Gollon) and no castling.

## Citadels

- A player's **acting king** (his highest-ranking royal) may step into the
  **opponent's empty citadel: the game is immediately drawn** — the escape of a
  losing king.
- No other piece may ever enter a citadel, with one exception: a player's
  **adventitious king** (while not his only royal) may enter his **own**
  citadel, where it is immune and blocks the opponent's draw.
- If an adventitious king becomes its owner's only royal while inside the
  citadel, the owner must immediately place it on any empty square (his whole
  turn).

## Draws (termination guarantees)

Citadel entry (above); threefold repetition; 100 halfmoves without a capture
or pawn move; a hard 1000-ply cap; or a bare royal against a bare royal (a
lone *extra* royal is not dead — king + prince can still win by forced
stalemate, since stalemate loses). The
repetition/50-move/ply-cap rules are modern additions (the historic game had
none) required so games always end.

## Implementation notes (documented readings)

Sources: [chessvariants.com](https://www.chessvariants.com/historic.dir/tamerlane.html)
(primary) cross-checked against Wikipedia "Great chess" (Cazaux & Knowlton,
*A World of Chess*). Where the sources leave gaps:

- *Giraffe continuations*: both outward straight directions (along the file
  **and** along the rank) are allowed, per Wikipedia's "horizontally or
  vertically"; CVP's a1→b5+ example shows only one of them.
- *"Cannot escape being taken"* (pawn-of-pawns placement) is implemented as a
  static test: the attacked piece is trapped if no enemy piece attacks the
  placed pawn's square and the piece has no move to a square the pawn does not
  attack. Forks are exact (two enemy pieces attacked, royals included). CVP
  makes the placement optional ("may"); we follow CVP over Wikipedia's "must".
- *Royal exchange* is available only while checked (CVP), once per game, to the
  acting royal; a pawn may not be swapped onto its own last rank.
- The C&K variant rule allowing a king in the citadel to swap with a prince and
  play on is **not** implemented — entering the citadel ends the game (CVP).
- A sole-royal adventitious king may not *enter* its own citadel (it now ranks
  as the king); Bodlaender's relocation rule covers the case where it becomes
  sole royal while already inside.
