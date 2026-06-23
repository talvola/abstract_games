# Four Field Kono (네밭고누)

A traditional **Korean** two-player capture game, also written *nei-pat-ko-no*.
Played on a **4×4** grid of points (here drawn as a 4×4 board of cells, coords
`c,r`). Player 0 is **Black**, player 1 is **White**.

## Setup

The board starts **completely full** — every one of the 16 cells holds a piece:

- **Player 0 (Black):** all 8 cells of rows 0 and 1 (the two nearest rows).
- **Player 1 (White):** all 8 cells of rows 2 and 3.

Because there are no empty cells, **the first move must be a capturing jump**
(there is nowhere to slide to until captures open up space).

## Moving

On your turn you make **one** move, of either of two types.

### 1. The signature capturing jump

This is what makes Four Field Kono distinct: **you capture by leaping your own
man to take the enemy beyond it.**

1. Pick one of **your** pieces (the *jumper*).
2. Jump it **orthogonally** (up/down/left/right — never diagonally) over an
   **adjacent piece of your OWN colour**.
3. Land on the cell **directly beyond** that friendly piece — this landing cell
   **must contain an OPPONENT piece**, which is **captured (removed)**. Your
   jumper ends on that cell.

The three cells (jumper → your own piece → enemy) form a straight orthogonal
line of three, with the enemy at the far end.

You may **NOT**:

- jump onto an **empty** cell;
- jump **over an enemy** piece (the jumped piece must be your own);
- jump over an **empty gap**;
- make more than **one capture** per turn (no multi-jumps).

### 2. The non-capturing slide

You may instead move one piece **one step orthogonally** (up/down/left/right —
never diagonally) into an **adjacent empty cell**. Nothing is captured; the
piece simply relocates. This lets you maneuver and set up future jumps once the
board has opened up.

### Move notation

Both move types are written `c,r>c2,r2` — the **from** cell and the **to** cell
— and are told apart by distance:

- **capturing jump:** the two cells are **two steps apart** orthogonally
  (lands on the enemy);
- **non-capturing slide:** the two cells are **one step apart** orthogonally
  (to an empty cell).

## Winning

**You win when your opponent has no legal move** — i.e. on their turn they can
make **neither a capturing jump nor a slide**. A player who is completely
blocked (all pieces unable to jump or slide) loses. This is the standard Four
Field Kono win condition.

## Termination safety nets

Because slides allow non-capturing maneuvering, play could in principle loop, so
two safety nets force a **draw**:

- a **no-progress cap (60)** — if 60 consecutive plies pass with no capture, the
  game is drawn (any capture resets the counter);
- a **hard ply cap (200)**.

These are conformance safeguards; ordinary play resolves well before either cap.

## Ruleset note

Standard Four Field Kono (per Wikipedia "Four-field kono", R.C. Bell, and
Cyningstan) allows **both** the capturing jump **and** the non-capturing
single-step orthogonal slide; this package implements that standard game. An
earlier version of this package implemented a capture-only variant, which
degenerated: once the armies separated with no captures available the game ended
instantly, declaring a loser who still had mobile pieces. With the slide
restored the win condition ("opponent cannot move") is correctly reached only
when a player is genuinely blocked.
