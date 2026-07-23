# Hi-Jack

A territorial stacking game by **Barrie Evans** (developed after 1996), first
published in *Abstract Games* issue 14 (Summer 2003). Two players, an empty
board (8×8 suggested; 6 and 10 also selectable). This package implements the
rules exactly as printed, and its self-test replays both of the magazine's
annotated sample games move-for-move.

## Aim

Control the most territory at the end of the game and hi-jack the opponent's
stacks. A playing piece **never moves once placed** — the whole game is about
*where* you place pieces and how their stacks project strength.

## Turn

On your turn you either **place one piece** on a square or **pass**. The game
ends when both players pass consecutively (a hard 400-ply cap also ends it, for
safety). Either colour may move first; it does not matter.

## Stacks and territorial strength

Pieces pile up into **stacks**. A stack's **height** `h` is its number of
pieces (a lone piece is a 1-high stack). A stack exerts a **territorial
strength** of 1 on each square in the pattern below, for the benefit of the
player who owns its **top** piece (its colours underneath don't affect the
range):

- **Orthogonally** up to `h` squares out in each of the 4 directions.
- **Diagonally** up to `max(0, h − 2)` squares out in each of the 4 directions.

So 1- and 2-high stacks are **orthogonal-only**; a 3-high reaches **1** square
diagonally; a 4-high reaches **4** orthogonally and **2** diagonally; and so on.
(This matches the magazine's "strengths exerted by stacks of various heights"
diagram and its text: *"A 4-high stack would exert strength up to four squares
orthogonally and two squares diagonally."*)

### Blocking

A stack exerts **no** strength on the **furthest orthogonal** square of a ray
(the square at distance `h`) **if all the intervening squares along that ray are
occupied**. Nearer squares always receive their strength. Blocking applies only
where there is at least one intervening square (so a 1-high stack, which has
none, is never blocked), and — per the printed rule, which speaks only of the
*"furthest orthogonal square"* — **only to orthogonal rays**, not diagonal ones.

Your **territorial strength at a square** is the sum of the strengths your
stacks exert there (it can exceed 1 if several of your stacks reach it).

## Placing a piece

Strength is always measured **before** the new piece is laid.

- **Empty square** — legal if *your* strength there **≥** the opponent's
  strength there.
- **Opponent's square (an attack)** — legal if *your* strength there **≥ the
  height of the attacked stack + the opponent's** strength there. Only the
  attacked stack's **height** matters, not its composition. Your piece goes on
  top and you now own (occupy) the square. Successfully attacking a stack that
  was **2-high or taller** is a **hi-jack**.
- **Your own single piece** — you may always add a **second** piece to it
  (making it 2-high), regardless of strength.
- **A stack you have attacked-and-occupied** — on a **later** turn you may add
  **one** more piece to it, regardless of strength (a one-time free
  reinforcement per capture; using it or being re-captured clears the credit).

These are the only ways to add to a square you already control: an own-built
stack tops out at height 2, and captured stacks can be reinforced by exactly one
extra piece (which is how the taller stacks in the sample games — e.g. the
4-high hi-jacked f6 — are built).

## Scoring

At the end each player scores:

- **1 point** for every **unoccupied** square where they exert **strictly
  greater** territorial strength than the opponent, plus
- **1 point** for every stack they have **hi-jacked and still occupy**.

Higher total **wins**. An equal total is an honest **draw** — there is no
tie-break (a symmetric game can end level, and that is a genuine draw).

## Anti-mirroring "switch" rule

Because one player can try to mimic the other into a symmetric, drawn game, the
following option exists: **if a symmetric board position occurs at any time
after each player has made at least three moves, the player to move may instead
play `switch`** to reorder the next moves. (Symmetry here means the position is
unchanged under a 180° rotation of the board combined with swapping the two
colours — exactly the pattern a mirroring copier produces.)

Invoking `switch` forgoes your placement this turn; the next four half-moves
then proceed **opponent — you — you — opponent**, after which normal alternation
resumes. This reproduces the article's example ordering
`B W B W B W W B B W B W …` (for the mirror-broken side). `switch` is offered as
an action button only when the trigger condition holds.

## Notation

A placement move is the target cell id `c,r` (shown in the move log in algebraic
form, e.g. `d4` = file d, rank 4). Passing is the `pass` action; the
anti-mirror option is the `switch` action. In the renderer each stack is drawn
as a tower of its pieces (bottom → top) in the owners' colours; a hi-jacked
stack is marked **H**.
