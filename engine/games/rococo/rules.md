# Rococo

By **Peter Aronson & David Howe** (c. 2000; published on chessvariants.com in 2002,
a *Recognized Chess Variant*). A member of the Ultima family: almost every piece
**moves like a chess queen** but has its own **method of capture**. Rococo was
designed to fix Ultima's defensive bias — here attack is stronger than defense.

## Board and objective

- **10×10 board.** The 36 outer squares are **edge squares** (tinted): a move may
  only **end on an edge square when that is necessary for a capture**, crossing as
  few edge squares as possible. Passive (non-capturing) moves must end on the inner
  8×8. A piece on an edge square may always move back into the interior.
- Setup (files a–h on the inner columns, White's back rank, mirrored for Black):
  **Immobilizer a1, Withdrawer b1, Long Leaper c1, King d1, Chameleon e1, Long
  Leaper f1, Advancer g1, Swapper h1**, with 8 **Cannon Pawns** on a2–h2.
  (The official page's prose says "King e1", contradicting its own diagram; the
  diagram and the authors' Zillions implementation both put the King on d1 — we
  follow those.)
- **Win by capturing the enemy King** — there is no check or checkmate; you may
  freely leave your King attacked or move it next to the enemy King.
- A player **unable to move loses**. A player whose move **repeats the same
  position for the third time loses** (position = piece placement + side to move
  + any live swap-back ban).

## The pieces

- **King (K)** — moves and captures one square in any direction, like a chess
  king. May enter an edge square only to capture a piece standing on it.
- **Advancer (A)** — moves as a queen to an empty square; then, if the *next*
  square in its direction of travel holds an enemy piece, that piece is captured
  (**capture by approach** — automatic, not optional). It never enters an edge
  square by its own move (only by being swapped there), but once on the ring it
  may make capturing moves along it.
- **Withdrawer (W)** — moves as a queen; if it moves one or more squares
  **directly away** from an adjacent enemy piece, that piece is captured
  (automatic). Only the piece exactly opposite its direction of travel.
- **Long Leaper (L)** — moves as a queen; **captures by leaping**: jumps a single
  enemy piece to any vacant square beyond, and may chain further jumps along the
  same line. Never jumps friendly pieces or two adjacent pieces. If a capture is
  only possible by landing on the ring, only the landing that crosses the fewest
  edge squares is legal.
- **Swapper (S)** — moves as a queen without capturing, **or swaps places with
  any piece of either side** an unobstructed queen-move away (a swap counts as a
  capture for the edge rule, so it can reach — and put pieces on — edge squares).
  It may also destroy itself together with **an adjacent enemy piece** (**mutual
  destruction** — legal even against the King). After a swap, the two pieces
  involved may not swap back on the immediately following turn.
- **Immobilizer (I)** — moves as a queen, never captures. **All enemy pieces
  adjacent to it are frozen** (cannot move at all). A frozen piece other than a
  King may **commit suicide** (remove itself) as its move — in this
  implementation, click the frozen piece twice. Two adjacent enemy Immobilizers
  freeze each other. The Immobilizer never enters an edge square.
- **Chameleon (C)** — moves as a queen; **captures each victim by the victim's
  own method**: it steps onto an adjacent enemy *King*, withdraws from
  *Withdrawers*, approaches *Advancers*, leaps over *Long Leapers*, swaps with
  (or mutually destructs with) enemy *Swappers*, and captures *Cannon Pawns*
  cannon-style by leaping an adjacent mount onto the Pawn beyond. Several
  methods may combine in one move (e.g. leap a Long Leaper while withdrawing
  from a Withdrawer and approaching an Advancer, or while ending in a swap).
  It **freezes enemy Immobilizers** (and only Immobilizers) but cannot capture
  them; an Immobilizer and an adjacent enemy Chameleon freeze each other.
- **Cannon Pawn (P)** — moves without capturing either a single step in any
  direction, or by **leaping over an adjacent piece of either side** to the empty
  square just beyond. It **captures by that leap**: jumping the adjacent mount and
  landing on the enemy piece just past it. **Promotion:** a Pawn that, by its own
  move (not by being swapped), lands on the rank where the enemy King started
  (rank 8 for White, rank 1 for Black) or on the edge rank beyond it *may*
  optionally promote to any friendly non-Pawn piece that is currently off the
  board (promotion recycles captured material; with nothing captured, no
  promotion is available).

## Draws

Rococo has no natural draws; as engine safeguards, the game is drawn after 600
total plies or 100 consecutive plies without a capture, removal, pawn move or
promotion.

## Notation used here

Cells are `col,row` with `0,0` the bottom-left **edge** corner (the inner 8×8 is
cols/rows 1–8). `a>b` move (captures implied), `a>b=swap` swap, `a>b=boom`
mutual destruction, `a>a` suicide of a frozen piece, `a>b=L` (etc.) Pawn
promotion choice.

## Documented interpretations

The official page leaves a few corners open; this implementation chooses:

1. **Suicide is only available to frozen pieces** (the rule grants it to
   immobilized pieces; the authors' ZRF gates it the same way).
2. **All removed friendly non-Pawn pieces** (captured, suicided, or mutually
   destroyed) are available as promotion targets, matching the ZRF's recycling.
3. A Chameleon may not jump a Long Leaper that stands *directly* adjacent to the
   Swapper it wants to swap with (every jumped Leaper needs an empty square
   beyond it, as in a normal leap).
4. The swap-back ban is implemented as: a swap between exactly the two squares
   of the previous move's swap is illegal on the following turn (the ZRF's
   ko-check; equivalent to the stated rule in all reachable cases).
5. Mutual destruction targets an adjacent **enemy** piece — the Swapper may
   boom any adjacent enemy, the Chameleon only an adjacent enemy Swapper. This
   matches the authors' ZRF, whose `swap-capture` verifies an enemy target. The
   Chameleon's *swap* is likewise restricted here to **enemy** Swappers
   ("opposing Swappers", per the ZRF's game-level description and the
   illustrated guide); note the ZRF's *executable* `swap1` is looser — it
   checks only that the target *is* a Swapper, so it would allow swapping with a
   friendly Swapper too. The sources conflict on this minor point (a friendly
   swap is of little practical use), and we take the stricter enemy-only
   reading. Separately, we follow the official page's "*swaps with Swappers may
   be combined with other captures*" (a Chameleon may leap a Long Leaper /
   approach / withdraw in the same move it swaps); the ZRF v2.2 instead makes a
   Chameleon swap a pure swap. Where the page and the ZRF disagree we treat the
   later-dated official page as canonical.
6. Where the formal edge rule would allow two equally-short edge landings for
   the same capture, neither is legal ("must be the only legal move…") — a
   corner case we have never seen arise in play.

Source: the official page — https://www.chessvariants.com/other.dir/rococo.html
(including its Illustrated Guide) and the authors' own Zillions implementation
(rococo.zip v2.2), which were used to cross-check the setup, the edge rule, the
promotion zone, and the stalemate/repetition loss rules.
