# Chaturaji — Chaturanga for four players

**Chaturaji** (also *Choupat* / four-handed Chaturanga) is the medieval Indian
four-player dice-chess, thought to date from around the 10th century and
reconstructed in the 18th–19th centuries by Captain Hiram Cox and Duncan Forbes;
H. J. R. Murray documented it in *A History of Chess*. This package implements the
**dice variant** from the chessvariants.com "Chaturanga for four players" entry,
settled by the piece-value scoring recorded by al-Biruni. A **diceless** option
gives the modern free-move version.

## Board and armies

An uncheckered **8×8** board. Four armies of eight sit in the corners; they move
**clockwise**: **Red → Green → Yellow → Black**. Each army has one **King**, one
**Rook** (the Elephant, moving as a rook), one **Knight** (Horse), one **Boat**
(Ship) and four **Pawns**.

Opening setup (chess coordinates):

- **Red:** King e8, Rook f8, Knight g8, Boat h8; Pawns e7, f7, g7, h7.
- **Green:** King h4, Rook h3, Knight h2, Boat h1; Pawns g1, g2, g3, g4.
- **Yellow:** King d1, Rook c1, Knight b1, Boat a1; Pawns a2, b2, c2, d2.
- **Black:** King a5, Rook a6, Knight a7, Boat a8; Pawns b5, b6, b7, b8.

Each army's pawns advance toward the *opposite* edge (Red downward, Green
leftward, Yellow upward, Black rightward) — every pawn is six steps from its
promotion rank.

## How the pieces move

- **King** — one square any direction (as in chess). There is **no check or
  checkmate** and no castling: a king may move into or be left "in check", and is
  simply captured like any other man.
- **Rook / Elephant** — any distance orthogonally, blocked by the first piece.
- **Knight / Horse** — the chess knight's leap.
- **Boat / Ship** — leaps **exactly two squares diagonally** (an *Alfil*); it jumps
  over whatever lies between.
- **Pawn** — one square straight forward to an empty square (no initial double
  step); captures one square diagonally forward. On reaching its far edge it
  **promotes** to Rook, Knight, or Boat (your choice — the modern rule).

All pieces capture by moving onto an enemy man.

### Triumph of the Boat

When a boat moves so that **four boats stand in a 2×2 square**, the moving boat
**captures the other three** at once (whoever owns them). This is rare.

## The dice

Each turn a player throws **two** long dice, each showing **2, 3, 4, or 5**. The
pip decides which arm may move:

| Pip | Moves |
|-----|-------|
| 2 | Boat |
| 3 | Knight |
| 4 | Rook |
| 5 | King **or** Pawn |

You may make **0, 1, or 2** moves per turn — one per die, in either order. On a
double you may move the same arm twice or two different arms of that type. If a die
gives no legal move it is wasted, and you may always decline part or all of your
roll (choose **Pass** to end the turn). If no move is possible the turn is simply
lost.

The dice for a turn are rolled automatically the instant the previous turn ends, so
you always know your roll before you choose your move.

**Diceless option** (`Dice: off`): no dice — each turn is exactly **one free move**
with any piece (the modern variant).

## Scoring and the end of the game

There is no checkmate. Every man has a value — **King 5, Rook 4, Knight 3,
Boat 2, Pawn 1** (al-Biruni's values) — and you score the value of the men you
capture (the piece's owner loses that value, so scores are zero-sum). A king
captured is worth 5; **the bereaved player keeps playing** with the rest of the
army (there is no king exchange in this implementation).

The game ends when:

- **A player has captured all three enemy kings while their own king survives** —
  they sweep the board, collecting the value of every remaining enemy man, and win.
- **Only one king is left** on the board (three kings have fallen), or
- a long stretch passes with no capture (or a hard move cap is reached).

Final standings are the net point totals; the highest score wins, an exact tie is
an honest draw.

### Notes on this implementation

- Scoring follows al-Biruni's **piece-value** account (each capture redistributes
  the man's value), which gives every seat an individual, zero-sum result suited to
  the platform's four-player payoffs.
- Simplifications from the fuller historical descriptions, documented for honesty:
  the **team/partnership** play (Red+Yellow vs Green+Black), **king exchange** by a
  partner, and the **throne-seizure stakes** are *not* modelled — each player plays
  for their own score. Promotion uses the modern free choice of Rook/Knight/Boat
  rather than the square-dependent promotion of the basic variant.
