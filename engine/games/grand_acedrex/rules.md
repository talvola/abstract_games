# Grant Acedrex ("Great Chess")

The large medieval chess variant described in **Alfonso X of Castile's
*Libro de los Juegos* (1283)**, on a **12×12** board with exotic animal pieces.
This package implements the modern scholarly reconstruction by **Jean-Louis
Cazaux and Sonja Musser** (as given on Wikipedia and the Chess Variant Pages),
playing the **standard no-dice version**. The rules are written below *as
implemented*; the points where the medieval sources are unclear are listed under
*Ruleset choices*.

## Objective
**Checkmate** the opponent's King. The King is the only royal piece.

## Board & setup (12 files × 12 ranks)
Files run **a–l** (columns 0–11). Each side has a 12-piece back rank plus 12
pawns. **Both colours use the identical back-rank arrangement**, so the two
Kings stand on the **same file (g)**, facing each other — the array is *not* a
left–right mirror (the Aanca on f and King on g are not symmetric about the
centre).

From file a to l, the back rank is:

```
R  L  U  G  C  A  K  C  G  U  L  R
```

- **R** Rook · **L** Lion · **U** Unicorn · **G** Giraffe · **C** Crocodile ·
  **A** Aanca · **K** King.
- White's back rank is **rank 1** (row 0); Black's is **rank 12** (row 11).
- Pawns fill **rank 4** for White (row 3) and **rank 9** for Black (row 8).
  Ranks 2–3 and 10–11 start empty.

White = player 0 and moves up the board (toward higher ranks).

## The pieces
| Piece | Symbol | Move |
|---|---|---|
| **King** | K | One square in any of the 8 directions. **Royal.** *First move only:* may instead leap two squares orthogonally **or** diagonally to an **empty** square, jumping over the intermediate square even if it is occupied; it may **not** capture with this leap. |
| **Rook** | R | Any distance **orthogonally** (the modern chess rook). |
| **Crocodile** | C | Any distance **diagonally** (the modern chess bishop). |
| **Aanca** | A | The griffon / roc. **Steps one square diagonally**, then **slides orthogonally outward** any number of squares in either of the two directions leading away from its origin. The diagonal intermediate square must be empty to continue sliding (it may instead stop there, capturing an enemy on it). It may leap nothing — every square it passes must be empty. *(Betza `t[FR]`.)* |
| **Unicorn** | U | The "rhinoceros". Makes a **knight leap**, then **slides diagonally outward** any number of squares in the direction continuing the knight's hop. The knight-landing square must be empty to continue (it may instead stop there, capturing an enemy on it). *(Betza `t[NB]`.)* |
| **Lion** | L | A leaper: a combined **(3,0)** + **(3,1)** jumper (a *threeleaper* + a *camel*). It leaps directly to those squares, ignoring anything between. |
| **Giraffe** | G | A **(3,2)** oblique leaper (a *zebra*) — jumps to a square three in one direction and two in the perpendicular, ignoring anything between. |
| **Pawn** | P | One square straight forward; captures one square diagonally forward. **No double step, no en passant.** Promotes on the far rank (see below). |

### Aanca and Unicorn reach (worked example)
An Aanca on **e5** can stop on its four diagonal steps (d6, f6, d4, f4) and, from
each, run the full rank/file away from e5 — forming a broad "griffon" cross. A
Unicorn on e5 hops a knight's move and then continues out along that diagonal
(e.g. **e5 → g6 → h7 → i8 …**).

## Pawn promotion (Alfonso's rule)
A pawn that reaches the far rank promotes to **the piece that started on the
file it lands on** — so a Rook-file pawn becomes a Rook, a Lion-file pawn a Lion,
and so on. The **King's-file (g) pawn promotes to an Aanca** (you can never gain
a second King). Promotion is mandatory and offers no choice (the file fixes it).

## Other rules
- **No castling.**
- **Checkmate wins. Stalemate is a draw.**

## Ruleset choices (where the sources are unclear)
The Alfonso reconstruction has several genuine uncertainties; the choices made
here are:

- **Dice omitted.** Historically Grant Acedrex was played with an octahedral die
  that dictated which piece type you had to move each turn (8 = King … 1 = Pawn).
  This package implements the common **no-dice** version (free choice of move),
  which is how the game is normally studied and played today.
- **Pawn double step: OFF.** This follows the **Wikipedia / Cazaux–Musser**
  reconstruction ("moves like the modern pawn, but cannot make an initial double
  step or capture *en passant*"). The Chess Variant Pages *Game Courier* preset
  instead *allows* a non-capturing double step (with no en passant); that reading
  is **not** used here. Consequently there is no en passant at all.
- **King's first-move leap: ON.** Modelled as a one-time two-square leap
  (orthogonal or diagonal) to an empty square, leaping over the intermediate
  square, with no capture. The leap is forbidden if it would leave the King in
  check (and, like any king move, cannot be used to castle — there is no
  castling).
- **Lion / Giraffe geometry** follows the Cazaux–Musser reconstruction
  (Lion = (3,0)+(3,1) leaper, Giraffe = (3,2) zebra). Some older readings give
  these animals slightly different leaps; this package uses the now-standard
  reconstruction.
- **Aanca = "one diagonal step then slide orthogonally outward"** and
  **Unicorn = "knight leap then slide diagonally outward"** follow the same
  reconstruction; both are *lame* compound movers (the intermediate square must
  be empty to continue past it).
- **Draw rules for termination.** The medieval game had no fifty-move or
  repetition draw; to guarantee the game terminates this package adds a 100-ply
  no-progress draw, threefold-repetition draw, and a hard ply cap, plus a
  bare-king-vs-bare-king insufficient-material draw. None of the animal pieces is
  a chess bishop/knight "minor", so every non-trivial endgame is played out.

## Notes / source
Primary references:
<https://en.wikipedia.org/wiki/Grant_Acedrex> and the Chess Variant Pages
reconstruction (Cazaux & Musser) at <https://www.chessvariants.com/rules/grantacedrex>.
