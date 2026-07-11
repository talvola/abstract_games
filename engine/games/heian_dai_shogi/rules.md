# Heian Dai Shogi (平安大将棋)

The earliest known large Shogi variant, described in the *Nichūreki* (a
Kamakura-era encyclopedia drawing on 12th-century sources), where it is
called simply "dai shogi". It is retrospectively named *Heian* dai shogi to
distinguish it from the later 15×15 dai shogi. **The historical record is
partial: some moves and details are a modern reconstruction** — see
"Reconstruction notes" below for what this implementation chose.

## Board and pieces

- 13×13 board, no drops: **captured pieces leave play permanently**.
- Each side has 34 pieces of 13 types. Sente (Black, player 1) moves first.

Setup, from each player's nearest rank:

- **Rank 1:** Lance, Knight, Iron, Copper, Silver, Gold, **King**, Gold,
  Silver, Copper, Iron, Knight, Lance.
- **Rank 2:** Free Chariot and Flying Dragon in front of the Lance and
  Knight, Fierce Tigers in front of the Silvers, Side Mover in front of the
  King.
- **Rank 3:** thirteen Pawns.
- **Rank 4:** the Go-Between, on the King's file.

## Moves (as implemented)

"Step" = one square; "ranges" = any number of empty squares (blocked by the
first piece; an enemy piece there may be captured).

| Piece (label) | Move |
|---|---|
| King (K) | steps 1 in any of the 8 directions |
| Gold General (G) | steps orthogonally or diagonally forward (6 ways) |
| Silver General (S) | steps diagonally or straight forward (5 ways) |
| Copper General (C) | steps orthogonally only (4 ways — "not to the four corners") |
| Iron General (I) | steps forward (3 ways) or sideways (2 ways) — "not to the three rear directions" |
| Fierce Tiger (FT) | steps 1 diagonally (4 ways) |
| Go-Between (GB) | steps 1 straight forward or backward |
| Pawn (P) | steps 1 straight forward |
| Knight (N) | the two forward shogi-knight jumps (leaps over anything) |
| Lance (L) | ranges straight forward |
| Side Mover (SM) | ranges sideways; steps 1 straight forward (no backward step) |
| Flying Dragon (FD) | ranges on all four diagonals (a bishop) |
| Free Chariot (FC) | ranges straight forward and backward |

Note for chu/dai shogi players: the Copper, Iron, Side Mover and Flying
Dragon all move **differently** here from the later games.

## Promotion

- The promotion zone is the far **three ranks**. Promotion is **optional**
  whenever a move starts or ends in the zone (entering, moving within, or
  leaving it), and is permanent.
- **Every promotable piece promotes to a Gold General** (shown as `+X`),
  except the **Flying Dragon**, which gains a one-square orthogonal step —
  i.e. it becomes a **Dragon Horse** (shown as `DH`).
- The King and Gold General do not promote.
- Promotion is **forced** when the piece could otherwise never move again:
  a Pawn or Lance reaching the last rank, and a Knight reaching either of
  the last two ranks. (In practice a Knight can only ever land on the last
  rank: each jump advances exactly two ranks and, with no drops, it always
  starts from rank 1, so it visits only odd ranks — never rank 12 of 13.)

## Winning and draws

- **Checkmate:** you may not leave your own King in check; a player with no
  legal move (checkmated or stalemated) loses — equivalent to the historical
  "capture the King".
- **Bare King:** reducing the opponent to a lone King **wins immediately** —
  *unless* the bared King could immediately capture your last remaining
  non-King piece on its very next move (or you are also bare), in which case
  the game is an immediate **draw**.
- **Repetition:** the same position occurring four times with the same
  player to move is a draw (*sennichite*, historically "no contest").
- A hard 600-ply cap ends an unresolved game as a draw.

## Reconstruction notes (conjectural points and choices)

The *Nichūreki* text gives the setup and most moves but not a complete
ruleset; both sources used here present a modern reconstruction and this
implementation follows them, choosing as follows where they differ:

1. **Piece moves** follow the Nichūreki descriptions as read by both
   Wikipedia and chessvariants.com (they agree on all 13 types). The
   generals' moves (wazir Copper, no-rear Iron) are stated in the text; the
   King/Gold/Silver/Knight/Lance/Pawn moves are inferred from Heian shogi.
2. **Promotion** to Gold in the far three ranks mirrors Heian shogi and is
   part of the standard reconstruction. The **Flying Dragon's promotion to
   Dragon Horse** follows chessvariants.com ("on promotion the Flying Dragon
   gains the power to move one square orthogonally"), which Wikipedia's
   piece notes confirm, although Wikipedia's summary line says everything
   promotes to Gold.
3. chessvariants.com claims the **Iron General must promote on the last
   rank**; that contradicts its own (and Wikipedia's) 5-direction Iron move,
   which can still step sideways there — this implementation does **not**
   force it (the general "must promote only if otherwise stuck" principle,
   stated by both sources, is applied literally).
4. The **bare-king rule** and its mutual-baring draw proviso are implemented
   exactly as both sources state; the game ends the moment a side is bared.
   The historical priority between baring and checkmate is unrecorded; here
   a baring move that also checkmates still falls under the bare-king rule
   (same winner; the draw proviso cannot apply, since a checkmated King has
   no legal capture).
5. The historical **prohibition of perpetual check** is not separately
   enforced; repetition is adjudicated as a draw instead.
6. "A player who makes an illegal move loses" is moot here (only legal moves
   can be played), and the 600-ply cap is a practical addition.
