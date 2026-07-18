# Chess with Different Armies

**Designer:** Ralph Betza (~1996). A *Recognized Chess Variant*.
**Source:** [chessvariants.com — Chess with Different Armies](https://www.chessvariants.com/unequal.dir/cwda.html)
(the exact Betza movement notation is quoted below from Betza's own interactive-diagram setup on that page).

This is ordinary 8×8 chess in **every** rule except one: the two players may field
**different armies**. The Kings and Pawns are always the orthodox FIDE King and
Pawn; each side's other six pieces (the two "rooks", two "knights", two "bishops"
and the "queen") come from one of four balanced, equal-strength armies. Choose the
White and Black armies from the option dropdowns (default: **Fabulous FIDEs vs
Colorbound Clobberers**, so the default game shows off the variant). Both sides may
even have the same army.

Standard FIDE chess rules apply throughout: pawn double-step, en passant,
check / checkmate / stalemate, and the fifty-move, threefold-repetition and
insufficient-material draws.

## The armies

Each army's back rank is, files **a b c d e f g h**: *corner · minor · bishop-type
· queen-type · **King** · bishop-type · minor · corner*.

### The Fabulous FIDEs (orthodox)
The regular chess army: **Rook (R)**, **Knight (N)**, **Bishop (B)**, **Queen (Q)**.

### The Colorbound Clobberers
A Bishop-themed army of colourbound pieces; its Queen is weaker than the FIDE Queen
and its "bishop" (the FAD) is stronger.

- **Bede (D)** — corner (a1/h1). *"Moves like a Bishop or a Dabbabah."* Betza **BD** = Bishop slide + a (2,0) leap. **Colourbound.**
- **Waffle (W)** — minor (b1/g1). *"Moves like a Wazir or an Alfil."* Betza **WA** = one orthogonal step + a (2,2) diagonal leap.
- **FAD (F)** — bishop square (c1/f1). *"Moves like a Ferz, an Alfil, or a Dabbabah."* Betza **FAD** = one diagonal step + (2,2) and (2,0) leaps. **Colourbound.**
- **Cardinal (A)** — queen square (d1). *"Moves like a Bishop or a Knight."* Betza **NB** = the Archbishop.

### The Remarkable Rookies
An orthogonal, Rook-themed army.

- **Short Rook (S)** — corner (a1/h1). *"Moves like a Rook, but only up to 4 spaces."* Betza **R4**.
- **Woody Rook (O)** — minor (b1/g1). *"Moves like a Dabbabah, or a Wazir."* Betza **WD**.
- **Half-Duck (H)** — bishop square (c1/f1). *"Moves like a Dabbabah, or like a Ferz, or can move three squares Rookwise (jumping over obstacles)."* Betza **HFD** = one diagonal step + (2,0) and (3,0) orthogonal leaps.
- **Chancellor (M)** — queen square (d1). *"Moves like a Rook, or a Knight."* Betza **RN**.

### The Nutty Knights
A Knight-themed army. Like the Pawn, **these pieces move differently forwards than
backwards** — their geometry is mirrored for Black.

- **Charging Rook (G)** — corner (a1/h1). *"Moves like a Rook forward and sideways, or moves like a King backwards."* Betza **fsRbWbF**.
- **Fibnif (I)** — minor (b1/g1). *"Moves like a Knight for its two longest forward and backward moves, or a Ferz."* Betza **fbNF** — the four (±1,±2) knight moves plus the four diagonal steps (this one is actually symmetric).
- **Charging Knight (J)** — bishop square (c1/f1). *"Moves like a Knight for its four forward moves, or moves like a king sideways and backwards."* Betza **fhNbsWbF**.
- **Colonel (C)** — queen square (d1). *"Moves like a Rook forwards or sideways, or a Knight in a knight's four forward moves, or a king."* Betza **fsRfhNbWF**.

## Special rules

### Pawn promotion
When a Pawn reaches the far rank it **may become any kind of piece that was in
either army at the start of the game** — i.e. the union of the two chosen rosters
(never a King or Pawn). So in a FIDEs-vs-Clobberers game either player may promote
to Q, R, B, N, Cardinal, Bede, FAD or Waffle.

### Castling
Castling still follows the normal king patterns even though the corner piece may
not be a Rook (the corner piece plays the Rook's role, and castling rights are lost
if the King or that corner piece moves).

- **Ordinary castling** (FIDEs, Rookies, Nutty Knights, and the *kingside* of the
  Clobberers): King moves two squares toward the corner and the corner piece hops
  to the far side of the King (O-O: e1→g1, corner h1→f1; O-O-O: e1→c1, corner a1→d1).
- **Colourbound flip** (forced, only when the **a-file corner piece is
  colourbound** — the Clobberers' Bede): queenside castling instead moves the King
  **three** squares to **b1/b8** and hops the corner piece over it to **c1/c8**.
  This keeps the colourbound piece on its own colour, and is **not optional**.

## Winning
Checkmate the opponent's King. Stalemate, the fifty-move rule, threefold
repetition and insufficient material are draws (as in FIDE chess). A hard ply cap
guarantees termination.

## Piece letters on the board
Standard pieces show their usual chess glyph. **Cardinal (A)** renders as the
Archbishop and **Chancellor (M)** as the Chancellor image. The remaining fairy
pieces have no dedicated glyph and are drawn as their letter:
**D** Bede · **W** Waffle · **F** FAD · **S** Short Rook · **O** Woody Rook ·
**H** Half-Duck · **G** Charging Rook · **I** Fibnif · **J** Charging Knight ·
**C** Colonel.
