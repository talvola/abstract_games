# Anti-King Chess

**Anti-King Chess II**, by Peter Aronson (2002). Standard chess with one twist: each
side has a **second royal piece — the Anti-King (A)** — that obeys an *inverted*
check rule. (Rules as implemented; see the official source link for the original.)

## The board and setup

The ordinary chess army, in the standard starting position, **plus** one Anti-King
per side:

- White Anti-King on **d6**
- Black Anti-King on **d3**

In the starting position each Anti-King is already attacked by two enemy pawns
(White's d6 by the Black c7 and e7 pawns; Black's d3 by the White c2 and e2 pawns),
so the opening position is legal and stable.

## The Anti-King

- It **moves exactly like a King**: one square in any of the eight directions.
- It may capture **only friendly pieces** — never an enemy piece. (Moving onto a
  friendly square removes your own piece.)
- It **can never be captured**, only anti-mated.
- It is **not a checking piece**: it gives no check to the enemy King and does not
  count as an attacker of the enemy Anti-King.
- **Kings do not attack Anti-Kings.** An Anti-King standing next to the enemy King,
  with nothing else attacking it, counts as *un*-attacked.

## Inverted check (the signature rule)

- A normal King is "in check" when it **is** attacked, and you may never leave it
  attacked.
- An **Anti-King is "in check" (safe) only when it IS attacked** by an enemy piece.
  When it is **not** attacked it is in **anti-check** — in danger.
- **You may never end your turn with your own Anti-King un-attacked.** A move that
  leaves your Anti-King unattacked is illegal, exactly as moving your King into
  check is illegal.

## How a move is legal

After your move, **both** must hold for the side that moved:

1. your **King is not attacked** (orthodox), **and**
2. your **Anti-King is attacked** by at least one enemy piece (other than the enemy
   King).

If you have no move satisfying both, your turn cannot be completed legally — you are
mated.

## Winning

You win by **either**:

- **Checkmate** — the enemy King is attacked and the opponent has no legal move to
  un-attack it; **or**
- **Anti-checkmate** — the enemy Anti-King is un-attacked and the opponent has no
  legal move to put it back under attack.

Mechanically these are the same condition: the player to move has **no legal move**
while **in danger** (King attacked *or* Anti-King un-attacked) → that player loses.
No legal move while *not* in danger is **stalemate** → a draw.

## Everything else is standard chess (version II)

- **Pawns** move and capture normally, with the two-square first step and **en
  passant**.
- **Promotion** on the last rank to Queen, Rook, Bishop or Knight (you may **not**
  promote to an Anti-King).
- **Castling** king-side and queen-side under the usual rules (the King may not
  castle out of, through, or into check; a castle that would leave your Anti-King
  un-attacked is also illegal).

## Draws

Stalemate, the fifty-move rule, threefold repetition, and a hard ply cap (for
termination). Orthodox insufficient-material is **not** used here — with a second
royal you can anti-mate with very little material.

## Notes / interpretation

This implements **version II** (standard pawns and standard castling). Version I
(Berolina pawns, a one-time king's-knight-leap instead of castling, an asymmetric
array) is a distinct game and is not included. The win conditions, the "kings don't
attack anti-kings", "anti-kings capture only friendly pieces / are uncapturable",
and the inverted-check rule all follow the chessvariants.com description.
