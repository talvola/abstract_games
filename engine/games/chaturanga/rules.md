# Chaturanga

Chaturanga is the ancient Indian ancestor of chess (~6th-7th century A.D.).
Its Sanskrit name means "four arms" (of the army): chariots, cavalry,
elephants and infantry, led by the Raja and his Mantri. It was played on the
uncheckered 8x8 *ashtapada* board. Shatranj — and through it modern chess —
descends directly from it. White (player 0) moves first; players alternate,
one move per turn.

These are the rules **as implemented**. Chaturanga's exact rules are a
scholarly reconstruction; this package follows the **Murray/Golombek account**
(the one chessvariants.com identifies as most authoritative), with the crossed
setup used by the chessvariants.com play preset and Wikipedia. Every point
where historians disagree is documented below.

## The pieces

| Piece | Name | How it moves |
|-------|------|--------------|
| Raja | King (`K`) | One square in any direction, exactly like a chess king. **No castling.** |
| Mantri | Minister / counsellor, ancestor of the queen (`F`) | Exactly **one square diagonally** (the ferz). Nothing more. |
| Gaja | Elephant, ancestor of the bishop (`A`) | **Leaps exactly two squares diagonally**, jumping over any piece on the square in between (the alfil). |
| Ratha | Chariot (`R`) | Any distance orthogonally, exactly like a chess rook. |
| Ashva | Horse (`N`) | The chess knight's leap. |
| Padati | Foot-soldier (`P`) | One square straight forward (**never two**); captures one square diagonally forward. |

The Gaja is a *leaper*: pieces between it and its destination do not block
it, and it can only ever reach 8 of the 64 squares. The Mantri is likewise
colour-bound.

## Setup

```
R N A K F A N R     (Black, rank 8)
P P P P P P P P
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
P P P P P P P P
R N A F K A N R     (White, rank 1)
```

**The Rajas do not face each other:** the White Raja starts on e1 (Mantri on
d1) and the Black Raja on d8 (Mantri on e8). A consequence is that the two
Mantris travel on same-coloured diagonals and can capture one another.

## Pawns

* A Padati moves **one square straight forward** only. There is **no
  two-square first move**, and consequently **no en passant**.
* It captures one square diagonally forward, like a chess pawn.
* On reaching the far rank it **promotes, and only to a Mantri** (`=F`).

## Check and the royal Raja

The Raja may not move into check, you must escape check, and you may not
leave your own Raja in check — as in chess.

## Winning

1. **Checkmate.** The side to move is in check and has no legal move. That
   side loses.
2. **Stalemate — a WIN for the STALEMATED player.** If the side to move is
   *not* in check but has no legal move, that (stalemated) side **wins**.
   This is the opposite of both chess (draw) and Shatranj (loss); Murray
   (p. 6) and Golombek (p. 19) both report it of the Indian game.
3. **Baring the king — an OUTRIGHT win.** The player who *first* reduces the
   opponent to a lone Raja (no other pieces) wins immediately. There is **no**
   Shatranj-style exception for baring the opponent back on the next move.
   (Two simultaneously bare kings cannot arise in play, since the game ends
   the moment one side is bared; a hand-built double-bare position counts as
   a draw.)

## Ruleset choices / documented alternatives

The historians' accounts compared on chessvariants.com's Chaturanga page
disagree on several points. Choices made here, with the alternatives:

* **Setup (implemented: crossed, Rajas e1/d8).** Wikipedia and the
  chessvariants.com play preset use this array (as does Gollon).
  Murray/Golombek instead place both Rajas on the same file (as in Shatranj);
  Murray notes the uncheckered board carried no fixed convention, and that
  nothing essential changes either way (with mirrored kings the Mantris are
  on opposite colours and can never meet).
* **Stalemate (implemented: win for the stalemated player).** Reported by
  Murray, Golombek and Gollon, from a Muslim master's account of the Indian
  rule. Some sources say stalemate simply did not occur (Davidson has no
  check rules at all); Shatranj instead makes it a win for the *stalemating*
  side.
* **Baring (implemented: outright win, no bare-back exception).** Murray,
  Golombek and Davidson report the bare-king win; the "opponent bares you
  back next move = draw" refinement is Shatranj's (al-Adli: the player
  *first* to bare the opponent wins). Gollon denies the bare-king rule
  altogether.
* **Raja's one-time knight leap (NOT implemented).** Gollon's reconstruction
  gives the Raja a single knight move, lost after it has been checked.
  Murray/Golombek have no such privilege, and the chessvariants.com page
  favours their account.
* **Gaja = alfil (implemented).** Davidson instead gives the elephant the
  silver-general move (one diagonal or one straight forward, as in makruk /
  sittuyin), and other ancient texts describe a (2,0) dabbabah leap;
  Murray/Golombek, Gollon and the play preset all use the two-square
  diagonal leap.
* **Promotion (implemented: to Mantri only, always).** Gollon instead
  promotes a pawn to the piece that started on the promotion square, only if
  such a piece has been captured, forbidding the advance otherwise.
  Murray/Golombek promote every pawn to a Mantri.
* **No medieval draw rules.** No fifty-move, threefold-repetition or
  insufficient-material draws; "insufficient" material is decided by the
  bare-king rule instead. The **only** automatic draw is a ply cap (600
  plies), kept purely so the engine's termination requirement is met.

## Notation

Moves are the platform's clickable cell-path strings, e.g. `4,1>4,2`
(from-to). Pawn promotion appends `=F`, e.g. `0,6>0,7=F`. Piece letters in
the move log are `K` (Raja), `F` (Mantri), `A` (Gaja), `R` (Ratha),
`N` (Ashva), `P` (Padati).

## Sources

* [chessvariants.com: Chaturanga](https://www.chessvariants.com/historic.dir/chaturanga.html)
  (comparison of the Murray/Golombek, Davidson and Gollon accounts) and its
  [play preset](https://www.chessvariants.com/play/chaturanga.html).
* [Wikipedia: Chaturanga](https://en.wikipedia.org/wiki/Chaturanga).
* H. J. R. Murray, *A Short History of Chess*; H. Golombek, *Chess: A
  History* (as summarised by chessvariants.com).
