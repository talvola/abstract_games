# Tenjiku Shogi (天竺将棋)

**Tenjiku Shogi** ("Indian chess") is the classic **16×16** large-shogi variant,
dating to the 15th–16th century and built on chu shogi. Each side has **78
pieces of 36 types**. It is famous for the *range-jumping Generals* and the
*Fire Demon*, and — unusually — is often a **fast** game because of its very
powerful pieces. **There are no drops.**

- Board: 16×16 (256 squares). Player 0 = **Sente (Black)**, at the bottom,
  advancing toward higher rows; White is the 180° rotation.
- **Objective:** capture (or *burn*) the opponent's **last royal** — the King,
  plus a **Prince** if the opponent's Drunk Elephant has promoted (dual royalty,
  as in chu / sho shogi). There is no check/checkmate enforcement: you may move
  into or ignore "check"; the game simply ends when a side loses its last royal.
  A player with no legal move loses (stalemate = loss).

Rules as implemented; official reconstruction: the Wikipedia article, following
The Chess Variant Pages. Sources: <https://en.wikipedia.org/wiki/Tenjiku_shogi>
and the CVP Tenjiku pages.

## Movement categories

- **Step / limited-range movers** move one square (or one/two along a line).
- **Ranging pieces** slide any distance along a line until blocked; a friendly
  piece blocks, an enemy is captured (must stop there).
- **Jumping pieces** leap to the second square in a direction, ignoring the
  intervening piece (kirin, phoenix, knight, and the lion family's leaps).
- **Area movers** (Lion, Lion Hawk, Vice General, Fire Demon) take 2–3 king
  steps in one turn, not necessarily in a line, stopping when they capture.
- **Range-jumping pieces** (the four Generals) may, *only when capturing*, leap
  over any number of pieces of strictly lower rank (see below).

## Pieces and moves

Notation: F/B = forward/back, sideways = left/right, "diag" = the four
diagonals. Colour-relative (forward flips for White). Each piece's promoted form
is fixed; a piece promotes **at most once**.

### Royals and steppers
- **King (K)** — one step any direction. Royal. Does not promote.
- **Drunk Elephant (DE)** — one step any direction except straight back →
  **Prince (a second royal, moves as a King)**.
- **Prince** — one step any direction. Royal.
- **Gold (G)** → Rook; **Silver (S)** → Vertical Mover; **Copper (C)** → Side
  Mover; **Iron (I)** → Vertical Soldier; **Ferocious Leopard (FL)** → Bishop;
  **Blind Tiger (BT)** → Flying Stag; **Dog (D)** → Multi General; **Pawn (P)**
  (one step forward) → Gold; **Knight (N)** (jumps two forward diagonals) → Side
  Soldier. (Gold = orthogonal + forward diagonals; Silver = forward + 4
  diagonals; Copper = forward king + back step; Iron = 3 forward; Leopard = 6,
  no sideways; Blind Tiger = all but forward; Dog = forward + back diagonals.)

### Ranging and limited-range pieces
- **Lance (L)** (forward slide) → White Horse; **Reverse Chariot (RC)** (F/B
  slide) → Whale; **Side Mover (SM)** (sideways slide + F/B step) → Free Boar;
  **Vertical Mover (VM)** (F/B slide + sideways step) → Flying Ox.
- **Vertical Soldier (VS)** (forward slide, 1–2 sideways, back step) → Chariot
  Soldier; **Side Soldier (SS)** (sideways slide, 1–2 forward, back step) →
  Water Buffalo.
- **Bishop (B)** → Dragon Horse; **Rook (R)** → Dragon King.
- **Dragon Horse (DH)** (bishop + king step) → **Horned Falcon**; **Dragon King
  (DK)** (rook + king step) → **Soaring Eagle**.
- **Kirin (Kr)** (diagonal step + orthogonal 2-jump) → **Lion**; **Phoenix
  (Ph)** (orthogonal step + diagonal 2-jump) → **Queen**.
- **Queen (Q)** (slides all 8 directions) → **Free Eagle**.
- **Water Buffalo (WB)** (diagonal + sideways slide, 1–2 F/B) → **Fire Demon**;
  **Chariot Soldier (CS)** (diagonal + F/B slide, 1–2 sideways) → **Heavenly
  Tetrarch**.

### The Lion family (multiple capture)
- **Lion (Ln)** — the chu-shogi lion: up to two king steps in a turn (may change
  direction, capturing on both), or a single jump anywhere within two squares;
  plus *igui* (capture an adjacent piece without moving) and *pass* (out and
  back). **Promotes to Lion Hawk.** (Chu's lion-trading restrictions do **not**
  apply in Tenjiku.)
- **Lion Hawk (LH)** — Lion + Bishop (long diagonal slides). Does not promote.
- **Free Eagle (FE)** — Queen + a *diagonal* Lion power (two diagonal steps with
  jump/igui/double-capture, reaching every square within two diagonal steps).
  Does not promote.
- **Horned Falcon (HF)** — slides in every direction **except** straight forward;
  straight forward it has a Lion "sting" (step twice / jump two / igui / pass).
  **Promotes to Bishop General.**
- **Soaring Eagle (SE)** — slides in every direction **except** the forward
  diagonals; on the two forward diagonals it has the Lion sting. **Promotes to
  Rook General.**

### The Fire Demon (火鬼)
- **Fire Demon (FD)** may make **either** a ranging move — Bishop + sideways
  slide — **or** an area move (up to 3 king steps, stopping on capture). It does
  not promote.
- **Burn:** wherever the Fire Demon stops, every adjacent enemy piece **except
  an enemy Fire Demon** is removed (up to the one it captures by displacement +
  seven burned neighbours).
- **Passive burn (priority):** any enemy piece that *moves* onto a square next
  to a Fire Demon is destroyed after making its capture — a "suicide move". The
  stationary Demon and every other adjacent piece survive, and the passive burn
  **does not cost the Demon's owner a turn**.
- **Fire Demon vs Fire Demon:** if a Fire Demon moves next to an enemy Fire
  Demon, only the *moving* Demon is immolated; the stationary Demon and all other
  adjacent pieces survive.
- A **Water Buffalo that promotes to Fire Demon burns immediately** upon
  promotion. Burning the enemy's last royal wins.

### The range-jumping Generals
The **Great (GG)**, **Vice (VG)**, **Rook (RG)** and **Bishop (BG)** Generals
range like sliders, but **when making a capture** may leap over any number of
pieces (friend or foe) of **strictly lower rank**. They may **capture** any
piece (even equal/higher rank) but cannot **pass** one of equal/higher rank.
The rank order is:

1. **King, Prince** (rank 4 — never jumped)
2. **Great General** (rank 3) — jumps along all 8 lines; does **not** promote
3. **Vice General** (rank 2) — jumps along diagonals **+ a 3-step area move**;
   does **not** promote
4. **Rook General / Bishop General** (rank 1) — jump along orthogonals /
   diagonals respectively

No General may leap over a King or Prince (of either side), but any can capture
one. Promotions: **Horned Falcon → Bishop General → Vice General**; **Soaring
Eagle → Rook General → Great General**.

### The Heavenly Tetrarch
- **Heavenly Tetrarch (HT, promoted Chariot Soldier)** — cannot move to an
  adjacent square and is not blocked by adjacent pieces: it **skips the first
  square** and ranges beyond it along the diagonals and the vertical, or moves
  two or three squares sideways. It can also *igui* (capture an adjacent enemy
  without moving). It is not a range-jumper elsewhere on its path.

## Setup

Five ranks per camp. From Black's back rank forward:

- **Rank 1 (back):** L N FL I C S G **K DE** G S C I FL N L
- **Rank 2:** RC · CS CS · BT **Kr Ln Q Ph** BT · CS CS · RC
- **Rank 3:** SS VS B DH DK WB **FD LH FE FD** WB DK DH B VS SS
- **Rank 4:** SM VM R HF SE BG **RG GG VG RG** BG SE HF R VM SM
- **Rank 5:** 16 Pawns
- **Rank 6:** two Dogs (in front of the 5th and 12th files)

White is the 180° rotation (so the Kings face diagonally, Black's King on the
right of its Drunk Elephant, White's on the left).

## Promotion

The promotion zone is the **far five ranks** (the opponent's original pawn line
and beyond). A promotable piece may promote when a move **enters** the zone
(starts outside, ends inside) **or** is a **capture that starts inside** the
zone (CVP's rule for multi-step pieces). Promotion is optional and permanent.
The **King, Great General, Vice General, Free Eagle, Lion Hawk and Fire Demon do
not promote**, nor do already-promoted pieces.

## Ending, repetition, draws

- **Win:** capture or burn the opponent's **last royal**. Stalemate loses.
- **Repetition / no progress:** a fourfold repetition of the same position with
  the same player to move, or a hard ply cap, is scored as an **honest draw**.

## Interpretations (contested historical rules resolved here)

The historical sources for Tenjiku are terse and often disagree. This
implementation follows the **mainstream modern reading** (Wikipedia / The Chess
Variant Pages / HaChu):

- **Range-jumping generals — capture allowed.** Generals may capture pieces of
  equal or higher rank (they simply cannot *jump over* them), and no general may
  jump over a King or Prince of either side. The stricter TSA reading (no
  capture of equal/higher rank, which lets Black force a win) is **not** used.
- **Fire Demon — TSA conflict rule.** In a Demon-vs-Demon clash only the moving
  Demon burns; the passive burn has priority over the active burn. The alternate
  "everything adjacent also burns" reading is not used.
- **Fire Demon slide along the rank (sideways),** per the Edo-era sources and
  the Wikipedia diagram (consistent with promotion from the Water Buffalo), not
  the Western "along the file" variant.
- **Water Buffalo promoting to Fire Demon burns immediately** (follows from the
  passive-burn rule).
- **Lion Hawk has full Lion powers** (jump + double capture), not the reduced
  TSA two-step area move.
- **Free Eagle = Queen + diagonal Lion** (the QAD[aF] "queen plus the diagonal
  moves of a lion" reading, symmetric to the Lion Hawk). The Japanese-source
  orthogonal range-jump (QpR) reading is not used.
- **Heavenly Tetrarch has igui and the vertical ranging move** (Sho Shōgi
  Zushiki reading), consistent with it being a promoted Chariot Soldier.
- **Trapped pieces / mandatory promotion:** promotion is always optional here;
  a Pawn/Knight/Iron/Lance that reaches a rank from which it has no move simply
  becomes a "dead piece" (this practically never matters for pawns/lances, which
  are move-compatible with their promotions). The disputed "second chance to
  promote at the far rank" for knights and iron generals is not implemented.
- **Area-move / general pass ("skip a turn"):** the Lion family, Horned Falcon,
  Soaring Eagle and Free Eagle can pass via their out-and-back power; the Vice
  General's and Fire Demon's area-move "return to start" pass is **not**
  generated (a documented simplification — the same choice made in Nutty Shogi).
- **Repetition** uses a simple fourfold-repetition draw rather than the JCSA's
  intent-based perpetual-check / perpetual-chase deviation rules.
