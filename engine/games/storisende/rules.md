# Storisende

*A group/territory game by **Christian Freeling** (2018). One of the designer's
own favourites.* Official rules: [mindsports.nl Storisende](https://www.mindsports.nl/index.php/arena/storisende/747-storisende-rules).

Two players move stackable men in straight lines on a hexagonal board. The
moment a fresh ("virgin") cell is vacated it crystallises permanently into
either **green** established territory or a **dark Wall** cell. Play thereby
self-divides the board into territories separated by a contiguous Wall, and the
winner controls the most territory.

## Board

A hexagonal **hexhex** board. The board-size option picks the base:

- **Base 4** — 37 cells (default).
- **Base 5** — 61 cells.
- **Base 6** — 91 cells.

Every cell starts **virgin** (beige). Coordinates are axial `q,r`.

## Setup — the placer / chooser opening

Storisende opens with a placer/chooser (pie-style) procedure. As implemented:

1. **Black (the placer)** places one man on any cell.
2. **White (the chooser)** then either:
   - **accepts** — the man stays Black's and counts as Black's first move
     (White now moves), or
   - **swaps** — White takes the placed man as its own; Black then moves.

*Interpretation:* the published procedure lets the placer distribute 2–5 men on
1–5 cells in any stacking. To keep the opening a single clear click in the
generic UI we implement the canonical minimal opening (one single man) plus the
chooser's pie decision, which preserves the balancing intent. Larger custom
openings are a documented simplification, not a rule change to mid-game play.

## Men, stacks and movement

Each player has a supply of identical **men** (flat checkers that stack). On a
turn a player either **passes** or moves.

- A man or **stack** moves **straight** in one of the **six** directions and
  travels **exactly as many cells as its height** (a single moves 1, a stack of
  3 moves 3, …).
- **Splitting:** you may move the top *k* checkers of a stack (1 ≤ k ≤ height),
  leaving the rest behind. The moving portion travels **exactly k cells** — by
  *its own* height, not the original stack's.
- Pieces **jump**: the cells passed over are irrelevant; only the landing cell
  matters.
- Because the distance equals the moved height, a move is written simply as
  `from>to` (e.g. `0,0>2,-2` moves a 2-stack two cells).

### Landing

- On an **empty** cell — the moved portion is simply placed there.
- On a **friendly** piece — the two **merge** into one taller stack.
- On an **enemy** piece — **capture by replacement**: the captured single or
  stack is removed entirely (regardless of size) and the mover takes its place.

## Crystallisation — green territory and the dark Wall

The heart of the game. **The instant a virgin cell is fully vacated** (its last
man/stack leaves), it permanently becomes either green or dark, based on the
established (green) territories it is adjacent to:

- adjacent to **no** established territory → it starts a **new** territory
  (green);
- an expansion of **exactly one** territory → it joins that territory (green);
- adjacent to **two or more separate** territories → it becomes a **dark Wall**
  cell (the Wall keeps territories apart — territories never merge).

Green and dark cells are **permanent**; they never revert to virgin, and pieces
may still move over or land on them.

### The double sprouts a man

**If and only if** a virgin cell is vacated by a **double** (a stack of exactly
two that leaves entirely), it **sprouts one new man** of the mover's colour on
that cell — whether the cell becomes green or dark.

## Passing and the end of the game

Movement is optional; a player may **pass** without losing future turns. The
game ends when **both players pass in succession**.

The winner is the player who **controls the most territory**, counted by the
**total number of cells** in the territories they control. A player **controls**
a territory if they are the **only** colour with men inside it (one man
suffices). Wall cells never count, and a territory occupied by both colours (or
empty) counts for nobody. Equal totals are a **draw**.

## Termination safeguards (this implementation)

To guarantee the game always halts (required by the platform's conformance
self-play), in addition to the natural mutual-pass ending:

- **3-fold repetition** (the same full position with the same player to move
  occurring a third time) ends the game, **resolved by territory score** (a tie
  draws). **This is a deliberate DEVIATION from the designer's literal
  "repetition = draw":** a repeated position means no further progress, and the
  territory leader would have won anyway by simply passing, so awarding the
  leader matches good play — and it lets the generic MCTS bot resolve the game.
  Under the literal repetition-draw, random/bot play shuffles stacks and draws
  ~every game; resolving by score makes active play decisive (verified). A human
  game normally ends by mutual pass and is unaffected.
- A hard cap of 400 plies ends the game and scores it (a non-original safety net
  that is far beyond any sensible game length).
