# Banqi (Dark Chess / 暗棋) — Taiwanese ruleset

A traditional Chinese flip-and-capture game for two, played with all 32 xiangqi
pieces on a 4×8 board (half a xiangqi board, pieces **in the squares**).

## Setup

The 32 pieces — per colour: 1 General, 2 Advisors, 2 Elephants, 2 Chariots,
2 Horses, 2 Cannons, 5 Soldiers — are shuffled and placed **face-down**, one per
square. Neither player has a colour yet.

## Colours

The first player (P1) must begin by flipping a piece. **The colour of that
first revealed piece is the colour P1 plays**; the opponent takes the other
colour. Play then alternates.

## A turn

On your turn do exactly one of:

1. **Flip** any face-down piece, revealing it (legal whenever any face-down
   piece remains — even one that turns out to be your opponent's).
2. **Move** one of your own **revealed** pieces one square up, down, left or
   right to an **empty** square. All pieces move the same way.
3. **Capture** with one of your own revealed pieces. The captured piece is
   removed and the capturer takes its square.

Face-down pieces cannot move and **cannot be captured** — by anything,
including cannons. Only a face-up piece of the opposing colour may be captured.

## Capturing (the ranking)

Pieces capture by moving one square onto the victim. A piece may capture only
an enemy of **equal or lower rank**:

**General > Advisor > Elephant > Chariot > Horse > Soldier**

with one exception: **Soldiers can capture the General, and the General cannot
capture Soldiers.**

### The Cannon

The Cannon is outside the ranking:

- It **captures a piece of any rank**, but **only by jumping**: it flies any
  distance along a rank or file, leaps over **exactly one** intervening piece
  (the *screen* — friend, foe, or face-down, it doesn't matter) and takes the
  first face-up enemy piece beyond it. Every other square between cannon,
  screen and target must be empty.
- Because it must jump, a cannon **can never capture an adjacent piece**.
  Without capturing, it moves one step like everything else.
- The cannon itself can be captured by **any piece except a Soldier** (and by
  an enemy cannon's jump).

## End of the game

**A player who cannot make any legal move on their turn loses.** Most often
this happens because all of their pieces have been captured and no face-down
pieces remain to flip.

### Draws (as implemented)

Regional practice on stalling varies (some circles forbid perpetual chases,
xiangqi-style; others allow them as a drawing resource). This implementation
sides with the honest draw:

- **Threefold repetition** of the same position with the same player to move
  is a draw.
- **64 consecutive plies with no flip and no capture** is a draw.
- A hard 1500-ply cap (unreachable in practice) also draws.

## Notes on this implementation

- **Ruleset**: the **Taiwanese** rules above. Out of scope (documented
  alternatives): the Hong Kong ranking (General > Chariot > Horse > Cannon >
  Advisor > Elephant > Soldier, no cannon jumps), the Mainland version
  (non-jumping cannons ranked above Soldier), and house variants such as
  cannon-captures-without-a-screen, attempted capture of face-down pieces, and
  multi-capture turns.
- **Randomness**: the shuffle is decided at setup and stored in the game
  state; flips merely reveal it (`has_randomness: true`). The board you see
  shows unrevealed pieces only as neutral "?" discs.
- **The bot "peeks"**: the built-in MCTS bot reads the full stored state,
  including the identities of face-down pieces — the platform's standard
  simplification for stored randomness. Human players never see them in the
  UI, but expect the bot to flip suspiciously well.
- Piece letters follow the platform's xiangqi module: **G**eneral, **A**dvisor,
  **E**lephant, Chariot **R**, **H**orse, **C**annon, **S**oldier.
- Moves: click a face-down piece to flip it; click one of your pieces then a
  destination to move or capture (`"c,r"` / `"c,r>c,r"`).

Primary source: [Wikipedia — Banqi](https://en.wikipedia.org/wiki/Banqi).
