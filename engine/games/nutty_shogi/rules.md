# Nutty Shogi

**Nutty Shogi** is H. G. Muller's "demagnified Tenjiku Shogi" — an attempt to
shrink the wild 16×16 Tenjiku Shogi (78 pieces, 36 types) to a more manageable
**13×13 board with 50 pieces a side of 25 types**, without losing its violent,
highly tactical flavour. There are **no drops**.

Rules *as implemented* (the local source of truth). Official source:
[chessvariants.com/rules/nutty-shogi](https://www.chessvariants.com/rules/nutty-shogi)
(H. G. Muller, last revised by A. M. DeWitt).

## Board and goal

- 13×13 board. Files **a–m** (columns 0–12), ranks **1–13** (rows 0–12).
  Sente (Black) sits at the bottom and advances up the board; Gote (White) is
  the 180° rotation.
- **The game is won by capturing the opponent's King, or by BURNING it with a
  Fire Demon** — in either player's turn. The King is the only royal and never
  promotes.
- There is **no check rule**: a side may leave (or move) its King under attack.
  The game simply ends the instant a King leaves the board.
- A player with **no legal move loses** (stalemate is a loss for the stalemated
  side).

## Movement notation

Moves are `>`-separated cell paths (`"col,row"`):

- `f>t` — a normal step, slide, leap, jumping capture, or Fire-Demon/Regent area
  move.
- `f>m>t` — a two-leg move (Lion/Griffon/Harpy double move, Eagle/Unicorn sting,
  or Tetrarchs igui). `f>m>f` means "capture on m, return to f" (igui) or, if m
  is empty, an out-and-back pass.
- A trailing `=+` promotes.

## The 25 piece types

Betza move strings in Black's forward frame (W = 1 step orthogonally,
F = 1 step diagonally, R/B/Q = rook/bishop/queen slides; `f`,`b`,`s`,`v` =
forward/back/sideways/vertical). Each promotable type has **one** predefined
promoted form.

| Piece | Move | Promotes to |
|---|---|---|
| **Pawn** (P) | one step forward (fW) | Gold |
| **Dog** (D) | forward step + both back-diagonals (bFfW) | Greyhound (forward Rook + back Bishop) |
| **Silver** (S) | shogi silver (FfW) | Vertical Mover |
| **Ferocious Leopard** (FL) | 4 diagonals + fwd/back (FvW) | Bishop |
| **Gold** (G) | shogi gold (WfF) | Rook |
| **Tiger** (BT) | all but straight-forward step (FsbW) | Stag (vRook + fwd-diag + sideways) |
| **Knight** (N) | shogi knight, jumps to (±1,+2) (ffN) | Soldier |
| **Kirin** (KY) | 4 diagonals + 2-step orthogonal leaps (FD) | **Lion** |
| **Phoenix** (PH) | 4 orthogonals + 2-step diagonal leaps (WA) | **Queen** |
| **Lance** (L) | slides forward (fR) | White Horse (fwd-Bishop + vRook) |
| **Vertical Mover** (VM) | slides vertically, steps sideways (sWvR) | Narrow Queen (Bishop + vRook) |
| **Soldier** (SS) | back step, slides sideways, up to 2 forward (bWsRfW2) | Buffalo |
| **Bishop** (B) | B | Crowned Bishop (BW) |
| **Rook** (R) | R | Castle (RF) |
| **Crowned Bishop** (DH) | Bishop + orthogonal step (BW) | **Unicorn** |
| **Castle** (DK) | Rook + diagonal step (RF) | **Eagle** |
| **Lion** (LN) | double king-move (see below) | **Griffon** (Lion + Bishop) |
| **Queen** (Q) | Q | **Harpy** (Queen + diagonal Lion) |
| **Jumping Bishop** (BG) | Bishop, jumps when capturing | **Regent** |
| **Jumping Rook** (RG) | Rook, jumps when capturing | **Jumping Queen** |
| **Chariot** (CS) | Bishop + vRook + up to 2 sideways (BvRsW2) | **Tetrarchs** |
| **Buffalo** (WB) | Bishop + sideways-Rook + up to 2 vertical (BsRvW2) | **Fire Demon** |
| **Regent** (VG) | Jumping Bishop + area move — **does not promote** | — |
| **King** (K) | K — **does not promote** | — |
| **Fire Demon** (FD) | Bishop + sideways-Rook + area move + burning — **does not promote** | — |

## Special pieces

### Fire Demon (FD, and a Buffalo promoted to one)

Slides like a **Bishop and a sideways Rook**. As an alternative it can make an
**area move**: up to **3 king-steps** through empty squares in freely chosen
directions, stopping at the first capture.

It **burns** every *enemy* piece standing on any of its 8 neighbouring squares:

- **actively**, immediately after it moves (also right after a Buffalo promotes
  into one);
- **passively**, when an enemy piece *moves next to it* — **and passive burning
  has priority**: any piece that lands next to a Fire Demon is destroyed *before
  it can do anything* (and whatever it captured on the way stays captured).
  Approaching a Fire Demon is therefore always suicide — even for another Fire
  Demon (the mover burns, the stationary one survives).

A Fire Demon can be **captured safely** by a piece that lands *exactly on it*.
Burning the enemy King wins.

### Jumping sliders (Jumping Rook/Bishop → Jumping Queen/Regent)

They move as their base slider (Rook/Bishop/Queen) for quiet moves, but **when
capturing may jump over any number of pieces** — friend or foe — provided every
piece jumped *over* is of strictly lower jumping-rank:

> **King (4) > Jumping Queen (3) > Regent (2) > Jumping Rook / Jumping Bishop (1)
> > all other pieces (0).**

They may **capture** any piece regardless of rank (only the pieces passed
*over* must be lower). The **Regent** additionally has a Fire-Demon-style **area
move** (up to 3 non-jumping king-steps) and **does not promote**.

### Lion, Griffon, Harpy

The **Lion** is a double mover: up to **2 king-steps per turn**, changing
direction between them, the first step optionally a jump. So it can leap to any
square in the surrounding 5×5 area, capture an adjacent enemy without moving
(**igui**), capture one and move on (**hit-and-run** / **double capture**), or
step out and back to pass. The **Griffon** is a Lion that also moves as a full
**Bishop**. The **Harpy** is a **Queen** with the double-move power along the
four **diagonals** only.

### Tetrarchs (Chariot promoted)

A slider that **skips (and does not affect) the first square** in every
direction: it slides unlimited in the 6 long directions (forward/back and the 4
diagonals) but reaches only squares **2–3 away sideways**. It cannot stop on the
adjacent square; instead it may **igui** — capture an adjacent enemy without
moving.

### Eagle, Unicorn (Castle / Crowned Bishop promoted)

Move as a Queen **except** in certain directions, where they "sting" instead of
sliding: step to the first square **or jump to the second**, optionally
capturing on the first (with igui / out-and-back pass). The **Unicorn** stings
straight **forward**; the **Eagle** stings in the two **forward diagonals**.

## Promotion

The **far four ranks** are the promotion zone (rows 9–12 for Black, 0–3 for
White). A promotable piece may **optionally** promote:

- when it **enters** the zone (starts its move outside, ends inside); or
- when it **starts** its move **inside** the zone **and captures** something.

Promotion is permanent and each type promotes to exactly one form. **King, Fire
Demon and Regent never promote.** A piece that promotes to a form already
present at setup becomes an *unpromotable* copy of it.

## Repetition and draws

A genuine tie is an honest **draw**. This implementation draws on **fourfold
repetition** of the same position with the same player to move, or on a hard
ply cap (600 plies).

## Interpretations / notes for this implementation

- **Setup — chariot d2 vs buffalo k2.** The CVP page's *prose* second-rank list
  places the Buffalo on d2 and the Chariot on k2, but its machine-readable
  interactive-diagram (Game Courier) config — the executable ground truth —
  places the **Chariot on d2 and the Buffalo on k2**, and the build brief agreed.
  This implementation follows the diagram config. (Only these two squares differ;
  every other square matches both sources.)
- **Knight = shogi knight** (`ffN`, jumps only to the two forwardmost squares),
  per the rank-by-rank prose "(Shogi) Knight" — consistent with Muller's diagram
  `fN` (his single-letter dialect gives the two forwardmost knight leaps).
- **Fire Demon slide** is Bishop + sideways Rook (no straight vertical slide),
  matching the setup prose `BsR` and the canonical Tenjiku Fire Demon; vertical
  reach of 1–3 comes from the area move.
- **Area moves** (Fire Demon, Regent) are encoded by their destination square
  only; the intervening king-path is validated (must be empty, stop at the first
  capture) during move generation. A Fire Demon cannot make a null area move that
  returns to its start.
- **Repetition** uses the simple fourfold-repetition-draw rule. The official
  page's intent-based rules (perpetual *checking* loses for the checker;
  perpetual *chasing* loses for the chaser; otherwise a draw) are **not**
  implemented; the outcome here is always an honest draw, never a fabricated win.
- There is **no check / checkmate**: this is a king-capture ("win as event")
  game with pseudo-legal move generation, exactly like Chu and Dai Shogi in this
  library.
