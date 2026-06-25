# Cannon Shogi (Taihou Shogi)

Cannon Shogi was invented by **Peter Michaelsen** in February 1998: standard 9×9
Shogi **plus four "cannon" pieces** borrowed from Xiangqi (Chinese chess) and
Janggi (Korean chess), with the nine pawns replaced by five **Janggi soldiers**.
All the familiar Shogi machinery — captured pieces switch sides and re-enter from
hand (**drops**), and pieces **promote** in the far three ranks — is unchanged.
These are the rules **as implemented** here. Sente (Black, player 1) sits at the
bottom and moves first; Gote (White, player 2) is at the top. "Forward" is toward
the opponent.

## The board at the start

Each side has, on its back rank: **Lance N Silver Gold King Gold Silver Knight
Lance** (`L N S G K G S N L`, files 0–8).

On the **second rank** sit the **Bishop** (file 1), the **Rook** (file 7), and the
four cannons:

- **Silver cannon** on the left silver-general file (file 2)
- **Gold cannon** on the left gold-general file (file 3)
- **Iron cannon** on the right gold-general file (file 5)
- **Copper cannon** on the right silver-general file (file 6)

So the orthogonal cannons (silver/gold) flank the Bishop and the diagonal cannons
(copper/iron) flank the Rook. White's array is the 180° rotation of Black's.

On the **third rank**, five **soldiers** (the pawns) stand on files 0, 2, 4, 6, 8
(the lance, silver and king files). 20 pieces a side.

## How the pieces move

The standard Shogi pieces are exactly as in Shogi:

- **King (K)** — one square any direction. **Rook (R)** — any distance
  orthogonally. **Bishop (B)** — any distance diagonally.
- **Gold (G)** — one square orthogonally or one square forward-diagonally (six
  squares). **Silver (S)** — one square diagonally or one square straight forward
  (five squares).
- **Knight (N)** — jumps to the two squares two-forward-and-one-to-the-side (only
  forward; it jumps over pieces). **Lance (L)** — any distance straight forward.
- **Pawn / Soldier (P)** — **here it is the Janggi soldier: one square forward OR
  sideways** (never backward). It captures the same way it moves.

The four **cannons** range over empty squares and/or jump a single "screen". A
screen is *any* piece of *either* colour. (Unlike in Janggi, a cannon here **may**
use another cannon as a screen and **may** capture another cannon.)

- **Gold cannon (C)** — *orthogonal Xiangqi cannon*: slides like a **Rook** over
  empty squares, but **captures only by jumping exactly one screen** to land on
  the first enemy beyond it.
- **Copper cannon (D)** — *diagonal Xiangqi cannon*: the gold cannon's move on the
  four **diagonals** (slides like a Bishop, captures over one screen).
- **Silver cannon (E)** — *orthogonal Janggi cannon*: it must **jump one screen to
  both move and capture**. It lands on the **first square past a single screen** —
  if empty that is a move, if it holds an enemy that is a capture. It cannot step
  to an adjacent square and does not range past the landing square.
- **Iron cannon (F)** — *diagonal Janggi cannon*: the silver cannon's move on the
  four **diagonals**.

## Promotion

The **promotion zone** is the farthest three ranks. A piece that **moves into, out
of, or within** the zone *may* promote at the end of that move.

- **Soldier/Pawn (+P), Lance (+L), Knight (+N), Silver (+S)** all become a **Gold**
  (the soldier's promotion is the *tokin*). Knight and Lance promotion is
  *mandatory* on the squares where they would otherwise be frozen (a Knight on the
  last two ranks, a Lance on the last rank); the soldier's promotion is **always
  optional** here, because a soldier on the last rank can still move sideways.
- **Rook (+R, Dragon King)** — Rook + one-square diagonal steps. **Bishop (+B,
  Dragon Horse)** — Bishop + one-square orthogonal steps.
- **Cannons** promote to **"flying" cannons** (+C/+D/+E/+F), **always optionally**.
  A flying cannon keeps its cannon move **and** gains a one-step move in the
  *perpendicular* family — diagonal steps for the orthogonal cannons (C, E),
  orthogonal steps for the diagonal cannons (D, F). Along that short step it is
  itself a tiny cannon: if a piece sits **adjacent** in that direction it **leaps
  that screen** to the second square (capturing an enemy there).

King and Gold never promote.

## Drops

When you capture a piece it **flips to your colour and goes to your hand** (a
promoted piece reverts to its unpromoted type, including the cannons). On your
turn you may **drop** a piece from your hand onto any empty square, where it
arrives **unpromoted**. Restrictions (as in Shogi):

- **No soldier on a file already holding one of your unpromoted soldiers** (*nifu*),
  no soldier or Lance on the last rank, no Knight on the last two ranks.
- **A soldier may not be dropped to give immediate checkmate** (*uchifuzume*).
- A drop may not leave your own king in check.
- **Cannons may be dropped on any empty square** (no file or rank restriction); a
  freshly dropped cannon may capture immediately on a later turn like any cannon.

## Winning, check, and draws

A player whose King is attacked is **in check** and must escape; a player with no
legal move is **checkmated and loses** (cannon checks count — a cannon attacks the
King only across a screen). To guarantee the game ends, a position repeated four
times and a hard ply cap (500) are scored as a **draw**.

## Letter legend (board glyphs)

`K R B G S N L P` are the standard pieces (P = soldier). The cannons render as
**gC** (gold cannon, C), **cC** (copper cannon, D), **sC** (silver cannon, E),
**iC** (iron cannon, F); a promoted piece is shown with a leading `+`.

## Interpretations & simplifications

- **All four cannon types are implemented in full** (the orthogonal/diagonal ×
  Xiangqi/Janggi matrix), including the flying-cannon perpendicular step/leap.
  Nothing was omitted.
- Sources differ on one point: some describe the gold/copper cannons as also
  *needing a screen to move*. This implementation follows the playable **pychess**
  ruleset (and chessvariants): the gold/copper cannons are **Xiangqi cannons**
  (free slide on empties, screen needed only to capture), while the silver/iron
  cannons are **Janggi cannons** (screen needed to move *and* capture).
- The **soldier** keeps the Shogi pawn's *drop* restrictions (nifu, no last-rank
  drop, uchifuzume) since it is still "the Pawn" and the source says other rules
  match Shogi — even though its sideways move makes those restrictions less
  necessary. Its *promotion*, however, is treated as optional everywhere (it is
  never frozen).
- The Janggi cannon-screen restriction (a cannon may not jump or capture another
  cannon) is **not** applied, per the chessvariants/pychess note that cannons here
  may jump and capture one another.
- Tournament perpetual-check rules are simplified to the repetition draw.
