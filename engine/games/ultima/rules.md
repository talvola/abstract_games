# Ultima (Baroque Chess)

Ultima, invented by **Robert Abbott** in 1962 (renamed *Baroque Chess* by some
publishers). Played on a standard 8×8 board. White = player 0 moves first.

The signature idea: **almost every piece MOVES like a chess Queen, but each type
CAPTURES by a completely different method**. Captures are a *side effect of where
you move* — you almost never capture by landing on the enemy. A single move can
remove **zero, one, or several** enemy pieces at once.

## Piece legend

| Letter | Piece | Moves like | How it captures |
|---|---|---|---|
| `K` | King | one square (any direction) | by displacement (land on the enemy), like chess |
| `P` | Pincer Pawn | a **Rook** (orthogonal slide) | custodial / pincer (orthogonal only) |
| `W` | Withdrawer | a Queen | by moving directly **away** from an adjacent enemy |
| `C` | Coordinator | a Queen | by **triangulating** a rook-cross with its own King |
| `L` | Long Leaper | a Queen | by **leaping** over enemies in its line of travel |
| `I` | Immobilizer | a Queen | **never captures**; freezes adjacent enemies |
| `M` | Chameleon | a Queen | by **mimicking the victim's own** capture method |

All sliding pieces move any number of empty squares and **cannot jump** (the Long
Leaper jumps only as part of a capture; see below).

## Starting position

The standard-chess back rank is replaced by Ultima pieces; the second rank is all
Pincer Pawns. From the a-file to the h-file:

```
8  I L M K W M L C   (Black)
7  P P P P P P P P
6  . . . . . . . .
5  . . . . . . . .
4  . . . . . . . .
3  . . . . . . . .
2  P P P P P P P P
1  I L M K W M L C   (White)
   a b c d e f g h
```

So: **Immobilizer** a-file, **Long Leaper** b- & g-files, **Chameleon** c- &
f-files, **King** d-file, **Withdrawer** e-file, **Coordinator** h-file. (Note the
King sits on d and the Withdrawer on e — swapped versus standard chess Q/K. Some
sources let players pre-game swap king/withdrawer and choose which rook is the
immobilizer; this package uses the **fixed canonical setup** above and offers no
swap, for simplicity and determinism.)

## How each piece captures

- **King (`K`)** — moves one square in any direction and captures by landing on an
  enemy (ordinary chess capture). It is the only piece captured by being landed on.
- **Pincer Pawn (`P`)** — moves like a Rook (orthogonal, any distance). When it
  moves to a square such that an enemy is **orthogonally adjacent** and a **friendly
  piece is directly beyond** that enemy (no gap: pawn–enemy–friend in a line), the
  enemy is captured. A single move can pincer up to four enemies (one per
  direction). **Diagonal pincers do not count.** A piece that moves *itself* into a
  pincer formation is **not** captured (custodial capture only triggers for the
  side that just moved into the flanking square).
- **Withdrawer (`W`)** — moves like a Queen. If it **starts** adjacent to an enemy
  and moves **directly away** from that enemy (the enemy is on the square just
  behind its starting square, along the line of motion), that enemy is captured.
  Moving any other direction captures nothing.
- **Coordinator (`C`)** — moves like a Queen. **After it moves**, draw the rook-file
  and rook-rank through the Coordinator and through its own King. Any **enemy** on
  either of the two intersection squares — (Coordinator's column, King's row) and
  (King's column, Coordinator's row) — is captured (up to two pieces).
- **Long Leaper (`L`)** — moves like a Queen over empty squares, **or** captures by
  **jumping** over enemy pieces in a single straight line, landing on an empty
  square beyond. It may chain **multiple** leaps in the **same line** in one move,
  provided each jumped enemy is **alone** (an empty square immediately follows it —
  two enemies back-to-back cannot be leaped). It cannot leap a friendly piece.
- **Immobilizer (`I`)** — moves like a Queen but **captures nothing**. Instead, every
  **enemy** piece **orthogonally or diagonally adjacent** to it is **frozen**: that
  enemy may not move at all while the adjacency persists. (See the deadlock
  exception below.)
- **Chameleon (`M`)** — moves like a Queen, and captures an enemy **by that enemy's
  own capture method**, behaving as if it were a piece of the victim's type:
  - vs an enemy **Withdrawer** — by withdrawing away from it.
  - vs an enemy **Coordinator** — by coordinating (rook-cross with its own King).
  - vs an enemy **Long Leaper** — by leaping over it (and it may make the leaping
    *move* only over enemy Long Leapers).
  - vs an enemy **Pincer Pawn** — by custodial pincer.
  - vs the enemy **King** — by stepping one square onto it (the King's own method);
    this requires beginning the turn adjacent to the King.
  - A Chameleon **cannot capture another Chameleon**, and it does not capture
    Immobilizers (it freezes them instead — see below). Only enemies whose **type
    matches the method used** are removed (e.g. leaping over a pawn captures
    nothing — and a Chameleon may not even leap a non-leaper).

## Immobilizer / Chameleon edge cases (the crux)

Following the canonical "pure rules" (MacKay) used by Wikipedia, a friendly piece
**X is immobilized** (cannot move) if **either**:

- **(a)** X is an **Immobilizer** and is adjacent to an **enemy Chameleon**; or
- **(b)** X is adjacent to an **enemy Immobilizer** next to which there is **no
  friendly Chameleon or Immobilizer other than X itself**.

Consequences:

- An Immobilizer freezes all adjacent enemy pieces — **including** enemy Kings,
  Withdrawers, etc. (This package follows the "pure rules": there is **no**
  immunity for any piece type; the *only* exception is the Chameleon/Immobilizer
  interaction below. A minority ruleset exempts King/Withdrawer/Chameleon — this
  package does **not** use that variant.)
- A **Chameleon freezes an adjacent enemy Immobilizer** (rule a). When this
  happens the two pieces lock each other: the Chameleon is also frozen by the
  Immobilizer (rule b), so **neither can move** until one is captured.
- Two **enemy Immobilizers** in contact also freeze each other (rule b: each is
  adjacent to the enemy Immobilizer and is itself an Immobilizer, but the rule's
  neutralizer must be a *different* friendly piece — so a lone immobilizer beside
  an enemy immobilizer **is** frozen; both sit dead).
- A friendly **Chameleon or Immobilizer adjacent to the enemy Immobilizer
  neutralizes** it for the *other* friendly pieces next to that immobilizer — they
  become free to move again (only the neutralizer itself may stay frozen).

## Winning

**Capture the enemy King.** When a King is removed, the game ends immediately and
the capturer wins.

**Interpretation note (check / checkmate):** classical Ultima descriptions say the
goal is to "checkmate" the King, but with seven exotic capture methods the notion
of "check" is impractical to compute and the literature is inconsistent about it.
This package therefore uses the cleaner, equivalent-in-practice rule: **the King
moves and is captured like any piece, and the win is the actual capture of the
enemy King.** There is **no check enforcement** — you may move into "check" and
your opponent then wins by taking the King. Players who want classical play should
simply avoid leaving their King capturable.

## Termination (draws)

Ultima can shuffle Queen-moves indefinitely, so to guarantee the game ends this
package adds two draw caps:

- **No-progress draw:** if **100 plies** pass with **no capture**, the game is a
  draw.
- **Hard ply cap:** the game is a draw after **600 total plies**.

Both are pragmatic implementation limits, not part of historical Ultima.

## Move notation

A move is `from>to` (e.g. `2,1>2,4`), cells written `col,row` (0-indexed, a1 =
`0,0`). Click the piece, then the destination. If no legal move exists (everything
frozen), the only move is `pass` (rendered as a button) — in practice the rules
make a full freeze of one side rare.

## Source

Rules verified against Wikipedia "Baroque chess" and the MacKay *"Pure" Rules of
Ultima* (the immobilizer/chameleon deadlock formulation above is taken verbatim in
substance from MacKay). Where sources disagree (immobilizer immunities; check vs.
king-capture), this package follows the choices documented above.
