# Knight Relay Chess

*By Mannis Charosh (c. 1972). Rules as implemented in this package — the local source of truth.*

Knight Relay Chess is standard chess on the usual 8×8 board, with the orthodox
starting array and ordinary piece movement, plus **one extra power** and **one
big restriction**, both built around the knight.

## The relay power

> Any piece **other than a king or a knight**, when it is **defended by a
> friendly knight**, gains the power to *also* move and capture like a knight.

- A piece is "defended by a friendly knight" if a friendly knight stands a
  knight's-leap away from it (i.e. the knight guards that square). The guarding
  knight does not move — it simply lends its leaping power.
- A queen, rook, bishop, or **pawn** so guarded may make a knight-leap **in
  addition** to its normal moves, and may capture with that leap.
- The **king never relays** (this is a deliberate rule, to stop kings escaping
  mate too easily), and **knights do not relay to one another**.

## Non-capturing, un-capturable knights

> A knight **cannot capture** anything, and **cannot itself be captured**.

- A knight only ever moves to an **empty** square. It can never make a capture.
- No move of any kind — ordinary or relayed — may land on (capture) an enemy
  knight. Knights are therefore excellent **immovable blockers**.
- Because a knight cannot capture, **a knight cannot give check by itself**.
  However, a knight can **relay** a check: a friendly non-knight piece that the
  knight guards may deliver a knight-leap check. (For example, a bishop guarded
  by a knight can give a "knight-leap" check — the check is relayed through the
  bishop.)

## Pawns

- A guarded pawn gains knight-leaps like any other piece, **except** it may
  **not** use a relayed knight-move to move to or capture on its own **first or
  last rank**. In particular there is **no promotion via a relayed move** — a
  pawn promotes only by an ordinary pawn move to the last rank (to Q, R, B, or N).
- If a guarded pawn relays back onto its initial rank, it regains the option of a
  double step (a natural consequence — the double-step is judged from the pawn's
  current rank).

## Check, checkmate, and other rules

- The king is **in check** when an enemy piece attacks its square either by an
  ordinary (non-knight) move, or by a **relayed knight-leap** from an enemy
  non-knight piece that is guarded by an enemy knight. A lone enemy knight never
  gives check.
- **Checkmate** and **stalemate** are the usual no-legal-move tests. You may not
  make a move that leaves your own king in check.
- **No en passant.**
- **Castling** is the standard king-and-rook castle (the published rules do not
  mention castling; orthodox chess otherwise, and the king cannot relay, so the
  relay mechanic does not affect it). *(Implementer's interpretation.)*
- Draws by the fifty-move rule, threefold repetition, and a hard ply cap
  guarantee termination. (Material-insufficiency draws are inherited from
  standard chess.)

White (player 0) moves first.

## Notes on this implementation

The published sources (chessvariants.com, Wikipedia, mayhematics) are unanimous
on the core rules above; this package follows them exactly. The only
under-specified point — castling — is resolved by keeping standard castling, as
documented above.
