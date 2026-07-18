# Hostage Chess

Invented by **John Leslie** (1997). David Pritchard called it "the variant of
the decade" (*Variant Chess* 32, 1999). Rules as implemented, from Leslie's own
page at [chessvariants.com](https://www.chessvariants.com/difftaking.dir/hostage.html)
and Wikipedia's "Hostage chess" article.

All rules of orthodox chess apply (movement, check, checkmate, stalemate,
castling, en passant) except how captured men are treated.

## Prisons and airfields

- Each player has a **prison** and an **airfield** beside the board. A captured
  man is never removed from the game: it goes into the **captor's prison**,
  keeping its colour.
- The board caption shows both inventories; the trays above/below the board
  show each player's **airfield** (their own men, ready to drop).

## Hostage exchange

Instead of a normal move you may rescue one of your men from the opponent's
prison:

1. Press an **exchange (H-L)** button: you release hostage **H** from your own
   prison (it goes to the **opponent's airfield** — they may drop it later) to
   rescue your man **L**. H must be of **equal or greater value** than L, on the
   scale **Q > R > B = N > P** (so any man buys back a pawn; only a queen buys
   back a queen; knight and bishop are interchangeable).
2. The rescued man must be **parachuted at once**: click it in your tray and
   drop it on any empty square. This completes the turn (the exchange and the
   drop are recorded as two entries in the move log, e.g. `(N-B)` then `B*f7`).

The opponent cannot refuse an exchange. An exchange is only offered when a
legal completing drop exists (in check, the parachuted man must resolve the
check — which it may, since drops can block, and releasing a hostage can even
disable a promotion-pawn check, see below).

## Drops

On any turn you may instead drop one man from your **airfield** on any empty
square. Restrictions and clarifications:

- A **pawn** may not be dropped on the 1st or 8th rank. A pawn dropped on its
  2nd rank regains the **double step**; a freshly dropped pawn cannot be
  captured en passant (only a later double step can be).
- A **rook dropped on a rook starting square can castle**, provided the king
  has never moved (implemented as regenerating that side's castling right).
- Two same-coloured bishops on same-coloured squares are fine.
- A drop may give **check or checkmate**.

## Pawn promotion

A pawn may move to the last rank **only if the opponent's prison holds one of
your Q/R/B/N**: the pawn goes into the opponent's prison and the piece you
choose is released onto the vacated square (`=Q/R/B/N` picker). Consequences,
both implemented:

- With no such piece available, a 7th-rank pawn **cannot advance and gives no
  check** to a king diagonally in front of it.
- Capturing a Q/R/B/N can be **illegal as self-check** if imprisoning it would
  suddenly let such a pawn promote onto your king's square (Wikipedia's
  8...Bxd7! example).

A promoted piece is a real piece from your set: if captured later it keeps its
type (there is no crazyhouse-style reversion to pawn).

## End of the game

Checkmate wins; stalemate is a draw. Material never leaves the game, so there
is no insufficient-material draw. Draws as implemented: **threefold
repetition** (the position includes both prisons, both airfields and any
pending parachute), the **fifty-move rule** (100 half-moves without a capture
or a pawn move; drops and exchanges do not reset the clock), or a hard cap of
800 plies (an exchange turn counts as two plies).

## Notation used in the move log

`N*c7` = knight dropped from the airfield on c7; `*g5` = pawn drop; `(B-N)`
followed by `N*c7` = a bishop released to rescue a knight, which parachutes to
c7 (Leslie writes this `(B-N)N*c7`); promotions as `d7-d8=R`.
