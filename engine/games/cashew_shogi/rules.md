# Cashew Shogi

**Cashew Shogi** is H. G. Muller's "demagnified Dai Dai Shogi" — the huge historic
Japanese variant *Dai Dai Shogi* (17×17, 96 pieces) shrunk by roughly a factor two
onto a **13×13** board with **54 pieces a side of 35 types** (2 more available through
promotion), chosen to keep the feel of the big game. Rules *as implemented* below;
the official source is Muller's own page (linked as the "official source").

## Board & goal

- 13×13 board. Files **a–m** (columns 0–12), ranks **1–13** (rows 0–12). Sente
  (Black) sits at the bottom and advances up the board; Gote (White) is the exact
  **180° rotation** (so the asymmetric flank pieces are left/right-mirrored).
- **Win by capturing the enemy King.** The King is the only royal piece and never
  promotes; the game ends the instant a King is taken. There are no drops.

## Setup

Each side's three back ranks plus a pawn rank and two Guns:

- **Rank 1 (a1–m1):** Lance, Goblin, Crowned Bishop, Butterfly, Queen, Left General,
  King, Right General, Flying Horse, Castle, Dragon, Hook Mover, Lance.
- **Rank 2 (a2–m2):** Broad Guard, Kite, Lion, Golden Bird, Phoenix, Gold, Commoner,
  Gold, Kirin, Unicorn, Wolf, Viper, Deep Guard.
- **Rank 3 (a3–m3):** Left Chariot, Bear, Viking, Leopard, Silver, Tiger, Flag, Tiger,
  Silver, Leopard, Hun, Bear, Right Chariot.
- **Rank 4 (a4–m4):** 13 Pawns. **Guns** on **d5, j5**.

Eight of the pieces are placed as an **already-promoted form** of a promotable piece
(Goblin = promoted Kite, Crowned Bishop = promoted Butterfly, Queen = promoted Flying
Horse, Castle = promoted Dragon, Hook Mover = promoted Viper, Golden Bird = promoted
Phoenix, Unicorn = promoted Kirin, Flag = promoted Commoner). They start already
promoted and cannot promote again.

## Promotion — by capture only

There is **no promotion zone**. A promotable piece **must promote the moment it
captures** something (mandatory; there is no choice of whether or what it promotes to).
A non-capturing move never promotes. **Pawns never promote**, and neither do the many
non-promotable pieces (Silver, Gold, Tiger, Leopard, Bear, Lance, Gun, the Generals,
Guards and Chariots, King).

The **12 promotable types** and their fixed promoted forms:

| Piece | promotes to | | Piece | promotes to |
|---|---|---|---|---|
| Commoner | Flag | | Kite | Goblin |
| Butterfly | Crowned Bishop | | Viper | Hook Mover |
| Dragon | Castle | | Wolf | Elephant |
| Flying Horse | Queen | | Lion | Berserker |
| Phoenix | Golden Bird | | Viking | Wolf |
| Kirin | Unicorn | | Hun | Lion |

## Pieces

Moves are given in Betza-ish shorthand (as verified against the reference engine):
*step* = one square; *slide* = any distance until blocked; a range like "up to 2/3/5"
is a blockable slide of that length; a *jump* ignores intervening pieces.

**Simple pieces**

- **Pawn** — steps 1 forward.
- **Silver** — steps to the 4 diagonals and straight forward.
- **Gold** — steps to the 4 orthogonals and the 2 forward diagonals.
- **Commoner** — steps 1 in any of the 8 directions (a non-royal King).
- **Leopard** — steps to the 4 diagonals, forward and backward.
- **Tiger** — steps to the 2 forward diagonals; slides up to 2 vertically.
- **Bear** — slides up to 2 on the forward diagonals; steps 1 sideways.
- **Lance** — slides forward. **Gun** — slides forward, steps 1 back.
- **Butterfly** — steps to the 4 diagonals (promotes to Crowned Bishop).
- **Dragon** — slides up to 2 on any diagonal (promotes to Castle).
- **Flying Horse** — steps to the 4 orthogonals; slides up to 2 on the forward
  diagonals (promotes to Queen).
- **Phoenix** — steps to the 4 orthogonals; jumps 2 diagonally.
- **Kirin** — steps to the 4 diagonals; jumps 2 orthogonally.
- **Viper** — steps 1 sideways; jumps 2 straight forward; jumps 2 to the back
  diagonals.
- **Kite** — slides up to 2 orthogonally; steps to the 2 forward diagonals.
- **Viking** — steps to the forward diagonals and vertically; slides up to 2 sideways.
- **Hun** — steps to the forward diagonals and sideways; slides up to 2 vertically.

**Asymmetric flank pieces** (mirrored for the two players)

- **Left General** — steps to all 4 diagonals, forward, backward, and **right** (no
  left step). **Right General** is the mirror (no right step).
- **Broad Guard** — slides sideways; slides up to 2 vertically; slides on the
  **forward-right** diagonal; steps to the forward-left diagonal.
- **Deep Guard** — slides vertically; slides up to 2 sideways; slides on the
  **forward-left** diagonal; steps to the forward-right diagonal.
- **Left Chariot** — slides forward; steps 1 back; slides along the **forward-left /
  back-right** diagonal axis. **Right Chariot** uses the other diagonal axis.

**Promoted-only / heavy pieces**

- **Crowned Bishop** — Bishop + one-step King (slides diagonally, steps orthogonally).
- **Castle** — Rook + one-step diagonals. **Queen** — Rook + Bishop.
- **Flag** — slides forward (orthogonal and both diagonals); slides up to 2 backward
  and sideways.
- **Golden Bird** — slides vertically; slides up to 2 sideways; slides up to 3 on any
  diagonal. **Unicorn** — the sideways/vertical mirror of the Golden Bird.
- **Elephant** — slides up to 3 vertically and on the forward diagonals; up to 5
  sideways and on the back diagonals.

**Multi-move pieces**

- **Lion** (promotes to Berserker) — a double mover: up to two King-steps per turn,
  changing direction between them, the first step optionally a jump. It can therefore
  reach any square of the surrounding 5×5 in one turn, capture an adjacent piece and
  stay ("igui"), capture-and-continue ("hit-and-run"), capture two adjacent pieces, or
  pass (step out to an empty neighbour and back). Dai Dai has **no** Lion-trading
  restrictions, so a Lion may always take another Lion.
- **Berserker** — moves as a Lion, **or** slides up to 3 squares in any of the 8
  directions.
- **Wolf** (the Dai Dai "Lion Dog"; promotes to Elephant) — moves **up to three
  King-steps along a single ray**, and may **jump over anything** (friend or foe) in
  the way. It annihilates enemies it passes over as well as the piece it lands on, so
  it can capture up to three pieces in one turn; it may also annihilate an adjacent
  enemy without moving, or pass. (Because any capture forces promotion, a Wolf that
  captures immediately becomes an Elephant.)
- **Goblin** (promoted Kite) — a **bent Bishop**: it slides diagonally and may make one
  90° turn onto the perpendicular diagonal, so on an empty board it reaches every
  square of its colour; it can also step one square orthogonally.
- **Hook Mover** (promoted Viper) — a **bent Rook**: slides orthogonally and may make
  one 90° turn, reaching any square in at most two legs.

## Repetition

Repeating a position (same side to move) four times is an honest **draw**; a hard ply
cap also draws. *(Interpretation — see below.)*

## Interpretations & notes

- **Sources override the brief.** The piece set, exact setup, every piece's move and
  the promotion rule were transcribed from Muller's Chess Variant Pages article and
  **differential-confirmed against HaChu 0.21** (Muller's reference engine, which plays
  `variant cashew-shogi`): HaChu's printed initial FEN matched this setup rank-by-rank,
  and each piece's Betza definition matched these move tables exactly.
- **Promotion is by capture only and mandatory** (Muller's page states this verbatim);
  there is no promotion zone and Pawns do not promote. This is Dai Dai Shogi's famous
  "promotion by capture" rule.
- **Repetition:** Muller's page gives intent-based perpetual-check / perpetual-chase
  loss rules. This implementation simplifies them to a plain **fourfold-repetition
  draw** (plus a ply-cap draw), which keeps the game terminating without adjudicating
  attack-intent.
- **Wolf partial captures:** the article notes the Lion Dog may choose to *spare* an
  enemy it jumps over; here the Wolf's move set lists exactly which passed squares it
  captures (both "capture it" and "jump over it" are offered as distinct moves), so the
  choice is preserved.
- **Stalemate** (no legal move) is a loss for the side to move.

Reference: H. G. Muller, *Cashew Shogi*, The Chess Variant Pages —
<https://www.chessvariants.com/rules/cashew-shogi>.
