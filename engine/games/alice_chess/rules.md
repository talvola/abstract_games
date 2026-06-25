# Alice Chess

*V. R. Parton, 1953 — "through the looking-glass" chess.*

Alice Chess is played on **two** standard 8×8 boards, **A** (left) and **B**
(right). All pieces begin in the normal chess array on board **A**; board **B**
starts **empty**. White moves first.

## The looking-glass rules

A piece always moves by its **normal chess move on the board it currently
occupies**. Then it "goes through the looking-glass":

1. The move must be a legal chess move on whichever board the piece stands on.
2. The square it would **transfer to on the OTHER board must be vacant**.
3. After the move (capturing or not), the piece is **transferred to the
   corresponding square on the other board**. A piece on A moves on A, then goes
   to B; a piece on B moves on B, then goes to A.

**Sliding pieces** (rook, bishop, queen) need their transit squares empty on the
board they are moving on, exactly as in normal chess.

**Captures** happen only on the board the moving piece currently stands on (the
captured piece is removed from that board). The capture is still legal only if
the mover's mirror square on the other board is vacant; the mover then transfers
there.

## Check and checkmate

A king is **in check** if it is attacked, on the board it currently stands on,
by an enemy piece on that same board. Attacks never cross between boards.

A move is legal only if, for the side moving:

- it is **not in check on the moving board after the move but before the
  transfer** (so you cannot escape check merely by transferring the king away —
  the move itself must answer the check on the board it is played on); **and**
- it is **not in check on either board after the transfer**.

A consequence: you may stand in check on the *other* board before moving, as
long as the resulting position (after the transfer) leaves you out of check on
both boards (e.g. the transferred piece interposes).

**Checkmate** (the side to move is in check and has no legal move) **wins** the
game.

## Special moves — choices made by this implementation

- **Castling: allowed.** King and rook must both be on board **A**, on their home
  squares; the king's path on board A must be clear, and the king's and rook's
  landing squares must be vacant on board **B**. Both the king and the rook then
  transfer to board B. The usual "not into / through check" tests apply. (For
  simplicity this implementation always permits castling when the home squares are
  occupied by an unmoved-looking king and rook; it does not track prior king/rook
  movement history — a minor, rarely-relevant simplification.)
- **En passant: omitted.** Wikipedia notes e.p. is normally excluded from Alice
  chess and that opinions differ on the target square, so this implementation
  leaves it out.
- **Promotion:** a pawn promotes on reaching the far rank **of the board it is
  moving on** (rank 8 for White, rank 1 for Black). Choose Q/R/B/N (move suffix
  `=Q` etc.); the promoted piece then transfers to the other board.

## Move notation

A move is `b,c,r>b,c2,r2`, where **both endpoints are squares on the moving
board** (so the board id is the same on each side). The implicit transfer to the
other board is applied automatically. Promotion appends `=Q`/`=R`/`=B`/`=N`.
Click the piece, then its destination on the same board.

## Ending

- **Checkmate** → win.
- **Stalemate**, **insufficient material** (lone kings, or king + a single
  bishop/knight), **threefold repetition**, or a hard **ply cap** → **draw**.
