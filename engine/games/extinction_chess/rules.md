# Extinction Chess

**Extinction Chess** (also called *Survival of the Species*) was invented by
R. Wayne Schmittberger, editor of *Games* magazine, in 1985. It uses the
standard chessboard, starting position and piece movement, but a completely
different goal: **wipe out an entire *type* of the opponent's pieces.**

These are the rules *as implemented* on this platform.

## How to win

You **win immediately** the moment any one of the opponent's six piece *types*
becomes **extinct** — its count on the board drops to zero:

- their **King**,
- their **Queen**(s),
- both their **Rooks**,
- both their **Bishops**,
- both their **Knights**, or
- all eight of their **Pawns**.

So capturing the opponent's last knight wins. Capturing their last bishop wins.
Capturing all their pawns wins. Capturing their king wins. You do **not** have to
checkmate — you just have to render one species extinct.

If a player owns *more than one* piece of a type (for example, two queens after a
promotion), **all** of them must be captured to make that type extinct.

## The king is just a piece

The king is **not royal** in Extinction Chess:

- There is **no check, no checkmate, no stalemate.**
- You **may** move your king onto an attacked square, or leave it attacked
  ("move into check") — it is a perfectly legal move.
- The king can be **captured** like any other piece; capturing the opponent's
  king empties their King type and wins the game (kings are just the most fragile
  type, since each side has only one).

## Moves

Everything about *how the pieces move* is identical to standard chess: rook,
bishop, queen, knight and king moves; pawn single/double steps and diagonal
captures; **en passant**.

### Castling

Castling is allowed, with the normal requirements — the king and the chosen rook
must not have moved, and the squares between them must be empty — **but** because
there is no check, it is **legal to castle while in check, or through / into an
attacked square.**

### Promotion

A pawn reaching the last rank **must** promote, and may become a **Queen, Rook,
Bishop, Knight, or King** (the king is not special). Promoting your last pawn is
legal even though it empties your own Pawn type — see below.

## Simultaneous extinction (the promotion tiebreak)

Promoting removes a pawn, so promoting your **last** pawn makes your own pawns
extinct. This only matters when it happens on the **same move** as an enemy
extinction. The classic case: White's last pawn on b7 captures Black's last
bishop on c8 and promotes (`bxc8=Q`) — this empties **White's pawns** *and*
**Black's bishops** at once.

In any such mutual extinction, **the player who made the move wins.** A move that
empties *only your own* type (with no enemy extinction) is a **loss**.

## Draws / game end

Orthodox insufficient-material draws are meaningless here (a lone king is already
several extinctions), so they are **disabled**. To guarantee every game
terminates, the game is drawn (0–0) by the **fifty-move rule**, **threefold
repetition**, or a hard ply cap. These are coarse compared to a dedicated
Extinction-Chess engine but never affect a decisive extinction result.

## Notation

Moves are clicked on the board. Castling is the king's two-square move (the rook
follows automatically); a promotion appends `=Q`, `=R`, `=B`, `=N` or `=K`.
