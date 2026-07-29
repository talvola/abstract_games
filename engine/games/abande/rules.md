# Abande

**Dieter Stein, 2005** — *"Connection and stacking"*. These are the rules **as
implemented** in this package, taken from three independent publications of the
same ruleset and cross-checked move-for-move against the AbstractPlay
`gameslib` reference implementation ([BGG 21324](https://boardgamegeek.com/boardgame/21324/abande)):

| Source | What it pins |
|---|---|
| [spielstein.com/games/abande/rules](https://spielstein.com/games/abande/rules) — the designer's page, "This version: 30 December 2005" | the entry figure (11 points), the hexagonal capture figure, a scored final position **White 13 – Black 15** |
| **Dieter Stein, "Abande – Rules of Play", PDF, © 2005** (same 30 December 2005 version; mirrored at [superdupergames.org/rules/abande.pdf](https://superdupergames.org/rules/abande.pdf)) | the same rules **plus two worked positions on the orthogonal 7×7 board** that the web page no longer shows, and a *different* scored final position |
| **nestorgames rulebook** ([ABANDE_EN.pdf](https://nestorgames.com/rulebooks/ABANDE_EN.pdf), rule book © 2009 Néstor Romeral Andrés, rules © 2005 Dieter Stein) — the published edition | the hexagonal capture figure and the scored position **White 12 – Black 15**, independently |

All **six** distinct published worked positions — three hexagonal, two
orthogonal, plus the second scored example — are reproduced exactly by
`selftest.py`, including every printed move list and both printed final scores.

## Material and board

Each player has **18 stackable pieces** — Black and White — held off the board
as the *pieces in hand*. The board starts **empty**; pieces sit on the
**intersections** of the printed lines.

The official rules offer three standard boards. This package ships:

| Board | Points | Neighbours | Status |
|---|---|---|---|
| **Square** | **49** (7×7 grid of points) | up to **8** | **default** |
| Hexagonal | 37 (hexhex; rows a–g of 4/5/6/7/6/5/4 points) | up to **6** | manifest option `board = hex` |
| Snub-square | 49 | up to 5 | *not implemented* |

**Why square is the default:** the designer's own 2005 rules PDF offers exactly
these two boards and no others — "An orthogonal board providing 49 spaces, or a
hexagonal board providing 37 spaces … Abande is played on a 7 × 7 orthogonal
board, or a hexagonal board providing 37 spaces" — and lists the orthogonal one
first. The current web page's *Material* section keeps that order and inserts
the snub-square board between them. The AbstractPlay reference implementation
also uses square as its base game with `hex` and `snub` as variants. The rules
explicitly state that the same rules apply to every board ("In the following only
hexagonal boards are shown, the same rules apply to the square, the snub-square
or any other board"), so the choice is purely a board option, and the two
implemented here are the two the ruleset shipped with.

**Snub-square is not implemented**: it is a later addition to the web page (it is
absent from the 2005 PDF and from the published nestorgames edition, which is
hexagonal-only), and its 49 points lie on a snub square tiling (alternating
squares and triangles) whose adjacency is irregular. Drawing it faithfully would
need the hand-built polygons of its dual tiling; rendering it on a plain square
grid would show connections that do not exist, which is worse than omitting it —
so it is deferred rather than approximated.

Rows/points are named as on the printed board (`a1`…`g7` on the square board,
`a1`…`g4` on the hexagonal one) in the move log; internally cells are `c,r`
(square, row 0 at the bottom) and axial `q,r` (hexagonal).

## Objective

Score more points than your opponent. **A stack's height is its value** (1, 2 or
3) — but only if it is awake; see *Scoring*.

## Play

Black opens by entering a piece on **any** space (the *initiative*). After that,
a turn is exactly one of:

1. **Enter** a piece from your hand onto an **empty space adjacent to the
   band** — i.e. touching at least one occupied space.
2. **Move** a stack you control **one space onto an adjacent opponent stack**.
3. **Pass** — allowed **only** when your hand is empty.

### The band

All occupied spaces must always form **one single connected group** — the
*band* (forks and networks are fine). This constrains **both** kinds of move:

- an entered piece must touch the band;
- a stack move that would **split** the band is **illegal**, because the moving
  stack vacates its space. The designer's own worked example makes this
  explicit ("The pieces on `c4` and `d4` cannot be moved because that would
  split the band"), and this package reproduces that example's complete
  capture list exactly (see `selftest.py`).

### Moving a stack

- A single piece counts as a **stack of height one**. The **topmost piece owns
  the stack**, and only its owner may move it.
- A stack moves **one space in any direction** and **never splits** — the whole
  column travels and lands on top of the target, keeping its order.
- It may move **only onto an opponent-controlled stack** — never onto an empty
  space, never onto a friendly stack.
- **No stack may exceed 3 pieces.** A move whose combined height would be 4 or
  more is illegal.
- **Moving is locked until Black has entered a second piece**, so Black cannot
  immediately capture White's reply to the initiative. In practice the first
  stack move that can ever be played is White's second turn (ply 4).

### Passing and the end

You may pass only with an **empty hand**; passing is always **optional** (you
may still move a stack, and you may move again on a later turn). **Two passes
in succession end the game.**

## Scoring

To make scoring easy the rules let you first remove all **"sleeping"** stacks —
stacks **not connected to an opponent stack**. This package computes the score
directly rather than physically removing anything.

- A stack **touching no opponent-controlled stack scores 0**.
- Every other stack scores **its height**: 1 for a single, 2 for a double, 3 for
  a triple.
- Pieces buried inside a mixed stack do **not** count as "connected" — only
  board adjacency matters, and only the top piece decides ownership.

Higher total wins. **An equal score is an honest draw** (the rules say "Games
can end in a draw"); no tiebreak is invented. Draws are common — about one
uniform-random game in ten ends level (6,000 test games: 10.6% square, 10.3% hex).

## Interpretations and implementation notes

- **"Connected to an opponent stack" means directly ADJACENT.** Under the band
  rule every stack is path-connected to every other one, so a path-based reading
  would make sleeping impossible; adjacency is the only coherent meaning, and it
  reproduces **both** published final positions exactly — the web page's (its
  five stacks marked "0" are precisely the adjacency-isolated ones, totalling
  **White 13 – Black 15** as printed) and the 2005 PDF / nestorgames one (six
  marked stacks, **White 12 – Black 15** as printed).
- **Removing sleeping stacks can never cascade**, so "remove them, then count"
  (the PDF and nestorgames wording) and "a sleeping stack is worth zero" (the web
  page's wording) are the same rule. Proof: if my stack X touches your stack Y
  then Y touches X, so an awake stack is never woken *by* a sleeping one and a
  removal can never put a third stack to sleep. Nothing here rests on which
  wording you take.
- **Connectivity is checked on the position *after* a stack move**, not only on
  placement — settled by the published `capture` example above.
- **A player holding pieces is never stuck.** At most 36 pieces occupy a 49- (or
  37-) point board, so an empty space adjacent to the band always exists; a
  legal entry is therefore always available while you hold pieces. Passing with
  pieces in hand is consequently never legal *and* never needed.
- **Termination is structural.** Every stack move merges two stacks, so it
  strictly reduces the number of occupied spaces; every entry raises it by one.
  Both hands must empty before anyone may pass, so a complete game contains
  exactly 36 entries and ends with 36 pieces in at least 12 stacks — hence at
  most 36 − 12 = **24 stack moves ever**, ≤ 60 non-pass plies and ≤ 122 plies in
  total. A `PLY_CAP` of 200 exists purely as a backstop and **provably never
  fires** — over 6,000 random games it fired zero times and the longest game was
  66 plies. The selftest asserts the cap is not reached, that every game ends by
  a double pass, that the cap can be made to bite when deliberately shrunk (so
  the assertion is not vacuous), and that a decisive score survives any counter
  being tripped. `max_random_plies` (150) sits above the observed tail and below
  the cap on purpose, so a termination regression fails loudly.
- **Abande Libre** (spielstein.com/games/abande/rules/libre, 1 October 2009) is a
  separate "design experiment" — no board at all, pieces laid freely on the
  table, with a *weak/strong connection* placement restriction. It is a distinct
  game rather than a board option and is **not** implemented here.
- The web page's **second** capture example ("There is only one possible capture
  for White: `c3-d4`, the stack on `e3` cannot move …") sits inside an HTML
  comment with its diagram stripped. The diagram survives in the designer's 2005
  PDF, where it turns out to be **on the orthogonal 7×7 board** — so it *is* used
  as an anchor here, together with the PDF's orthogonal entry figure (14 legal
  entry points). These are the only published anchors for the default board's
  8-neighbour geometry and for its connectivity-on-a-move rule.

## How this differs from the platform's other stacking games

Abande's signature is the pair of constraints no other stacker in this library
has: **every occupied space must stay in one connected band** (which both
restricts entry and freezes stacks whose departure would sever the group), and
**stacks may move only onto enemy stacks**, so movement is purely aggressive and
strictly reduces the number of stacks. Scoring then rewards *contact*: a group
that has walled itself off from the opponent is "sleeping" and worth nothing at
all.

- **Avalam** (Deweys) is the closest relative — one-step stacking merges with a
  height cap and a count at the end — but it starts from a fixed full board with
  no hand, lets you move **any** stack of either colour onto **any** occupied
  neighbour, caps at 5, has no connectivity rule, and scores **1 per tower**
  regardless of height (and nothing "sleeps").
- **Mixtour** (also Stein) enters on any empty square, moves a *distance equal to
  the target's height*, **splits** stacks, and is won outright by a 5-stack.
- **Accasta** (also Stein) starts from a fixed setup on the same hexhex-4 board,
  splits stacks, has ranged pieces and a positional (castle) goal.
- **Lasca / Bashni / Emergo / Focus** are all draughts-family jumpers or
  splitters with capture-by-jump, not connectivity-constrained placement.

## Notation and interface

- Entering a piece: the reserve tray below/above the board holds your remaining
  pieces — click the chip, then a highlighted space. (Move string `P@c,r`.)
- Moving a stack: click the stack, then the enemy stack it captures. (Move
  string `c,r>c,r`.)
- Passing appears as a **pass** button when your hand is empty.
- The move log uses the printed board names: `d4` for an entry, `c3-d4 (3)` for
  a stack move (the number is the resulting stack height).
- The caption shows the running score and both hands.
