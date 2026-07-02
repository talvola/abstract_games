# Elven Chess

H. G. Muller (2014). A 10×10 hybrid of orthodox Chess and Chu Shogi, designed to
give a western chess player "a whiff" of Chu Shogi. Checkmate wins. Rules below
are **as implemented**, following Muller's published rules page on
chessvariants.com (the "official source" link).

## Setup

Files `a`–`j`, ranks 1–10. White:

- **Rank 1:** Rooks a1, j1; **King f1** (the rest of the rank is empty).
- **Rank 2:** Dwarf a2, Knight b2, Bishop c2, **Elf d2, Warlock e2, Queen f2,
  Goblin g2**, Bishop h2, Knight i2, Dwarf j2.
- **Rank 3:** Pawns a3–j3.

Black mirrors by **180° rotation** (King e10, Queen e9, Warlock f9, Elf g9,
Goblin d9, pawns a8–j8).

## Pieces

- **King, Queen, Rook, Bishop, Knight, Pawn** — exactly as in orthodox chess.
- **Goblin (G)** — Rook **or** one King step (the Shogi *Dragon King*).
- **Elf (E)** — Bishop **or** one King step (the Shogi *Dragon Horse*).
- **Dwarf (D)** — one King step in any direction; non-royal (a *Commoner*). It
  gains nothing pawn-like: no double step, no e.p., no promotion.
- **Warlock (W)** — the Chu-Shogi **Lion**. It moves as a King but may
  (optionally) do so **twice in one turn**, and may use its first step as a
  *hop* over any occupied square. So it can:
  - leap directly to **any square of the surrounding 5×5 area** (nothing in
    between is disturbed);
  - **capture two pieces** in one turn (capture an adjacent piece, then make a
    second King step that captures again);
  - capture an adjacent piece and move on to an empty square, or **return to
    its starting square** (*igui* — capture without net movement);
  - **pass the turn** by stepping to an adjacent empty square and back.

### Warlock click-encoding (this app)

- Distance-2 leap: click the Warlock, then the target.
- Move to an **adjacent** square: click the Warlock, then the target **twice**
  (the second click confirms "stop here" — needed because a continuation of a
  double move starts with the same clicks).
- Double move: Warlock → adjacent enemy → second square (which may be the
  Warlock's own starting square for an igui capture).
- Pass: Warlock → adjacent empty square → back onto the Warlock.

## Anti-trading rules (the game's signature)

1. **Royal-for-one-turn.** A Warlock may capture the enemy Warlock **only if
   the square it ends up on would be safe for a King** — not attacked by any
   enemy piece, *pinned pieces included*. (A Lion double move may still grab a
   defended Warlock in passing, as long as its final square is safe.)
2. **Iron-for-one-turn.** When a **non-Warlock** captures a Warlock, the other
   side's Warlock becomes **iron** for one turn: the opponent's immediate reply
   cannot capture it at all (not even as the first leg of a Warlock double
   move). The board caption shows which Warlock is currently iron.

Together these make it impossible for the two Warlocks to be captured on
consecutive moves.

## Pawns, castling, game end

- Pawns have the orthodox initial **double step** (from rank 3 / rank 8) and
  **en passant** capture.
- **Promotion is mandatory on entering the last three ranks** (so in practice a
  pawn promotes on reaching the 8th rank, 3rd for Black), and only to **Q, R,
  B or N** — never to Warlock, Elf, Goblin or Dwarf.
- **Castling:** orthodox conditions (unmoved King and Rook, empty in between,
  King not in / through / into check); the King moves **three squares** toward
  either Rook, the Rook lands beside it.
- **Checkmate wins.** Stalemate is a draw; also drawn: threefold repetition,
  50 moves without a capture or pawn move, insufficient material, and a
  400-move hard cap (anti-stall).

## Interpretations & implementation notes

- Muller's two sources disagree on two details; this port follows the
  **published chessvariants.com rules page**:
  - **Queen/Warlock squares:** CVP puts the Warlock on e2 and Queen on f2
    (Black: f9/e9); his play-test applet swaps them. CVP is used.
  - **Warlock-trade enforcement:** the applet instead ends the game immediately
    when Warlocks are captured on consecutive turns. The CVP royal/iron
    formulation is implemented.
- The Warlock's turn-pass (explicit on the CVP page) is implemented; passing is
  not allowed while in check (it cannot resolve check).
- The royal-for-one-turn rule needs no memory: a Warlock that legally captured
  the other Warlock stands on a square no enemy piece attacks, so it provably
  cannot be recaptured on the very next move.
- Hop-first-then-step moves that land where a direct leap also lands are the
  same move (one canonical encoding); a pass via any adjacent empty square is
  offered.
