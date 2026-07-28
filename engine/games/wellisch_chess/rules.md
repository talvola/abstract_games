# Wellisch's Three-Handed Hexagonal Chess (Dreischach)

**Siegmund Wellisch, Vienna 1912 — the first hexagonal chess ever published.**

These are the rules *as implemented in this package*, which follows Wellisch's own
article throughout. Where the article is silent, the gap is filled by a **named
interpretation** listed at the bottom.

> **Primary source.** Siegmund Wellisch, "Das Dreischach", *Wiener Schach-Zeitung
> (Allgemeine Schach-Rundschau)*, red. u. hrsg. Georg Marco, Wien und Leipzig:
> Wilhelm Braumüller, **XV. Jahrgang 1912, Nr. 21/24 (November–Dezember), S. 322–330**.
> Nine pages with five figures; the starting array is Fig. 5 on p. 327.
> Scanned by the Austrian National Library (ANNO, title acronym `sze`) — the
> "official source" link opens that 1912 volume; the article begins on p. 322.
> There is no BoardGameGeek entry for this game.
>
> Corroborated by D. B. Pritchard, *The Classified Encyclopedia of Chess Variants*,
> 2nd ed. (ed. John Beasley, 2007), §37.2, p. 334.


## The board

A regular hexagon of side 6 — **91 cells in three colours** (30 yellow, 31 black,
30 red). Cells are **pointy-top**: their corners face the players, so the rows run
horizontally and each player's home edge is a straight line of six cells. Wellisch
explicitly *rejected* the flat-top arrangement (his Fig. 4) because it has no
well-defined last row for promotion.

Three players sit at **alternating** edges of the hexagon; the three edges between
them are free and serve as the promotion rows.

| Seat | Wellisch's name | Home edge | Pawns advance toward | Promotion row |
|---|---|---|---|---|
| 1 | Weiss (White) | bottom | the top | the top edge (row `l`) |
| 2 | Rot (Red) | upper right | the lower left | the lower-left edge (file `1`) |
| 3 | Schwarz (Black) | upper left | the lower right | the lower-right edge (`N−L = 6`) |

**Move order is White → Red → Black**, cyclically (Wellisch p. 329).

> The board's three cell colours are drawn as three shades of the board itself.
> The *pieces* are drawn in this platform's seat palette, which is not white/red/black
> — the historical colour names are kept in the captions and the move log.

The move log uses **Wellisch's own coordinates**: letter rows `a`–`l` parallel to
White's edge (11 rows, **with no "j"**) and numbers `1`–`11` parallel to Red's edge.
So White's king starts on `a4`, Black's on `h3`, Red's on `i11`.

## The men — 15 each: 1 King, 1 Queen, 2 Rooks, **3 Knights**, 8 Pawns

**There are no bishops.** A hexagonal board has no diagonals in the chess sense, so
Wellisch dropped the bishop altogether and gave each player a third knight instead.

- **Rook** — slides any distance along one of the six edge-adjacent lines. It may not
  turn within a move and it does not jump. *(Wellisch's example: `a5–d8`, passing
  through `b6` and `c7`.)*
- **King** — one step to any of the six edge-adjacent cells (a *wazir*). The diagonal
  step is a "Sprung" and is reserved to the knight and the queen.
- **Knight** — exactly **one hex-diagonal step** in any of the six diagonal
  directions: to the nearest cell of its **own colour**, forwards, backwards or
  sideways. It captures the same way. A knight is therefore colour-bound, which is
  why three of them are needed to cover the board — one yellow, one black, one red.
  *(Wellisch's examples: `b4 → c3, c6, d5` only; `f11 → e9` only.)*
- **Queen** — Rook **+** Knight, one mode per move. She does *not* slide along the
  diagonals; her diagonal reach is exactly one cell.
- **Pawn** — one step forward, and it **captures in exactly the same way** — there is
  no separate capturing direction. Because each player faces a *vertex* direction,
  there is **no straight-ahead step**: every pawn has **two forward directions, 120°
  apart**, and may move or capture into either. **No initial double step and no en
  passant.** *(Wellisch's examples: Black's pawn `f2 → e2` or `f3`; Red's pawn
  `l10 → l9` or `k9`.)*

### Castling

The king **swaps places with a rook**, "under the usual rules of two-handed chess":
neither man may have moved, the cells between them must be empty, and the king may
not castle out of, through, or into check. Each home row reads **N R Q K R N**, so
one rook stands next to the king (a one-cell swap, available from move 1 — notated
`O-O`) and the other is two cells away behind the queen (`O-O-O`, playable only once
the queen has moved).

## The starting array

King and Queen occupy the two middlemost cells of the home row, the **King on the
yellow cell and the Queen on the red cell**; the two Rooks flank them on **black**
cells; the two corner cells of the home row and the middle cell of the second row
hold the three Knights; the remaining second-row cells plus the two middlemost cells
of the third row hold the eight pawns — i.e. Pritchard's `NRQKRN / PPPNPPP / PP`.

```
     N P . . P N          Black's corner l6 … Red's corner f11
    R P . . . P R
   Q P . . . . P K        Black's Queen i4 … Red's King i11
  K N P . . . P N Q       Black's King h3 … Red's Queen h11
 R P P . . . . P P R
N P . . . . . . . P N
 P . . . . . . . . P
  . . . . . . . . .
   . . . P P . . .        White's c4 c5
    P P P N P P P         White's b1 … b7
     N R Q K R N          White's a1 a2 a3 a4 a5 a6
```

### A warning about published diagrams

**The diagram in *The Oxford Companion to Chess* (Hooper & Whyld, p. 172) is wrong,
and German Wikipedia's diagram is a redraw of it** (its own source field says so). It
mirrors the Red and Black armies, putting their Queens on their Kings' *right*. Anyone
checking this implementation against German Wikipedia will therefore appear to find a
bug. We follow the **1912 original**, which agrees exactly with Pritchard's *ECV*
diagram, with *CECV* p. 334 ("Qs always to left of Ks") and with the Ludii
implementation — all four agree on all 45 men. Wellisch's own **colour rule** (King on
yellow, Queen on red) settles the handedness without reference to any diagram, and it
is checked in this package's `selftest.py`.

## Promotion

A pawn reaching the free edge opposite its own home edge promotes — but **only to a
piece its own army has already lost**. It is not a free choice: the promoted man is
literally a captured Queen, Rook or Knight taken back off the side of the board.
Pawns and kings are never promotion targets. A man taken over from an eliminated
player keeps its **original army** in every respect: its direction of travel, its
promotion row, and the pool it promotes from.

## Check, checkmate, king capture and army takeover

- You may never leave your own king attacked — by *either* opponent.
- **Checkmate is not the end of the game.** A checkmated player's king may be
  captured, but the third player may just as well **free him from the mate** first.
- A king may be captured **only while checkmate stands against it**. A king merely in
  check is untouchable. (Wellisch writes that no king may be taken "ohne daß ihm im
  Zuge vorher Schachmatt angekündigt wird"; we read the mate as a property of the
  *position*, so a mate that has stood for several plies is still a mate.)
- If two players are in check and each one's *only* escape is capturing the other's
  (equally mated) king, neither mate stands and neither king may be taken — a mate
  may not depend on a king capture that depends on itself.
- When a king falls, its owner is out, and **all of his remaining men pass to the
  player who actually captured the king** — who may or may not be the player who
  delivered the mate.
- Once one player is out, the remaining two simply play on, alternating moves.
- The object is to defeat **both** opponents.

## Scoring

Wellisch's own table (p. 329): three points per game, one for a win and a half for a
draw against each opponent.

| Outcome | 1st eliminated | 2nd | survivor |
|---|---:|---:|---:|
| No draw | 0 | 1 | 2 |
| The two finalists draw | 0 | 1½ | 1½ |
| All three draw | 1 | 1 | 1 |

This package returns exactly these numbers as the per-seat payoffs.

## Draws (this implementation)

Wellisch says only that "Patt stellen" and "Remis machen" follow two-handed chess
*mutatis mutandis*; he gives no numbers, and 1912 chess had no fifty-move rule in the
modern form. This package uses:

- **150 plies with no capture, no pawn move and no promotion** → draw (50 turns each,
  the three-player analogue of the fifty-move rule);
- **threefold repetition** of position + player to move + castling rights → draw;
- a hard **47,000-ply backstop** derived from the game's own bound (pawn advances are
  monotone, so there are at most ~310 progress events, each followed by at most 150
  quiet plies). It is not expected ever to fire; the manifest's `max_random_plies`
  sits far below it on purpose, so a termination regression fails loudly as "did not
  terminate" rather than being absorbed into a silent cap draw.

**A decisive result always outranks these counters:** a king capture that leaves one
player standing ends the game as a conquest even on the 150th quiet ply, in a
thrice-repeated position, or at the ply cap.


## Interpretations (where the 1912 article is silent)

1. **Delayed promotion.** *What if a pawn reaches the promotion row before its army
   has lost anything?* This is the one genuine gap; no source records it. We use
   **delayed promotion**: the pawn stays on the promotion row and promotes on a later
   turn, once a piece becomes available. This matches the Ludii implementation and the
   period precedent of Ayres's *Mars* (1910), which *CECV* names as Wellisch's
   immediate predecessor ("providing one has previously been captured. If not, it must
   wait until one is available"). **Note the stalemate interaction:** such a pawn has
   *no legal move at all* — both of its forward steps run off the board — so it simply
   sits until a piece is lost or it is captured. Promotion is compulsory on arrival if
   the pool is non-empty; a *delayed* promotion is optional (an available move, never
   a forced one), because with two waiting pawns and one available piece a compulsory
   rule would be ambiguous.
2. **A player who cannot move passes — while three are playing.** *What does a
   checkmated player do when his own turn arrives before he is freed or his king is
   taken?* He passes — nothing else is possible. We apply the same rule to a
   **stalemated** player: in a three-handed game one player having no move cannot end
   everybody's game, so play simply skips him and he may be freed later. Play ends in a
   draw only if *no* remaining player has a legal move.
   **Once only two players remain this reverts to the two-handed rule and a stalemate
   is a DRAW.** This is not an interpretation but the article itself: after an
   elimination "the two other participants play **as a pair** to the end of the game"
   (p. 329), and *"Patt stellen"* is named among the terms governed by "the same rules
   applied mutatis mutandis **as in two-handed chess**". A stalemate then scores the
   *two finalists draw* row of Wellisch's own table (0 / 1½ / 1½). A **checkmate** is
   still not terminal even here — the king must actually be captured — so only a player
   who is *not* in check ends the game this way.
3. **You may never move into check from any player.** Wellisch's "mutatis mutandis"
   clause imports the ordinary prohibition; with three players we read it as *your
   king may not be left attacked by anyone*. (Consequence: a mate may be delivered
   jointly by two opponents.)
4. **Termination constants.** The 150-ply no-progress rule, threefold repetition and
   the 47,000-ply backstop above are ours; Wellisch specifies none. The game genuinely
   can loop — there is no double pawn step, promotion is gated on prior losses, and
   the army takeover recycles material — so some such rule is required.

A fifth, smaller reading, for completeness: **a promoting pawn draws on its own
army's pool**, not its current commander's. A captured man goes to the side of the
board as a man of *its* colour, and a taken-over pawn is explicitly stated to keep its
original owner's direction of travel, so it is treated as a man of that army in every
other respect too.

> **In fairness, the article's literal wording points the other way.** Wellisch writes
> (p. 328) that a promoting pawn may become "any piece which **the player** has lost so
> far, at **the player's** free discretion" — and *der Spieler* is naturally the player
> to move, i.e. the *current commander*. Wellisch never contemplates an inherited pawn
> promoting, so neither reading is his; we prefer the physical-man argument above, but
> the choice is genuinely open and a reader following the German literally would
> implement the opposite.
