# Rosette

**Rosette** is an almost literal transposition of **Go** to the *triple contacts*
(the vertices) of a honeycomb grid. It was invented in **1975 by Mark Berger**
(the pen name of **Richard Kramberger**) and published in the magazine *Games &
Puzzles*; Christian Freeling revived and hosts it on MindSports. These are the
rules **as implemented** in this package.

## The board

The board is the set of vertices of a hexagonal patch of hexagons with *n*
hexagons on each side. There are exactly **6·n² points**:

- **Base-5** — 150 points (default; sized so the built-in bot stays fast)
- **Base-6** — 216 points
- **Base-7** — 294 points (Berger's original board)

Every **interior** point has exactly **three** neighbours (along the honeycomb
edges); points on the outer border have two. The board starts empty.

## Play

- **Black moves first.** On your turn you **place one stone** on a vacant point,
  or **pass**. Passing does not forfeit your right to move again.
- The game **ends when both players pass in succession**.
- A **group** is a set of like-coloured stones connected through single steps
  along the edges. A group **lives** so long as it has at least one **liberty**
  (an adjacent vacant point) **or** it contains a **rosette** (see below).
- After you place a stone, any **enemy** group left with no liberty (and no
  rosette) is **captured** and removed. Enemy captures are resolved before your
  own group is checked.
- **Suicide is illegal**: you may not play a stone that leaves your own group
  with no liberty — *unless* the move captures enemy stones (the capture grants a
  liberty) or completes a rosette.

## The rosette — the one new rule

> A group also lives, **unconditionally and permanently**, if it contains a
> **rosette**: six like-coloured stones around one small hexagon.

Concretely, whenever all **six** vertices of a single honeycomb cell are occupied
by one colour, that group is **immune from capture** forever — it is skipped in
every capture check, and playing the sixth stone to complete a rosette is never
suicide even if the resulting group has no liberties. (Berger added this safety
mechanism because on the honeycomb an extension out of *atari* gains at most one
liberty, which would otherwise let a single liberty be filled to run a group to
its death — the rosette lends richer strategy than pure capture tactics.)

## Ko / repetition (superko)

Rosette uses **situational superko**, exactly as the MindSports rules state: *a
move may not result in a position that already occurred with the same player to
move.* This subsumes the simple ko rule and forbids longer repetitions.

To **guarantee termination** (the platform plays random games to a terminal), two
further backstops apply, as in this platform's Go: double-pass ends the game, and
a hard **ply cap** (twice the number of points) forces scoring in the rare event
a game runs extremely long. These never affect normal play.

## Scoring

At the end (two passes) the game is scored by **Chinese / area scoring**, chosen
here because it is completely algorithmic — *there is no dead-stone marking step*:

- Each side scores **one point per stone** it has on the board, **plus** one point
  for every empty point in a region that touches **only** that colour (a region
  bordering both colours is neutral — including the vacant points inside a *seki*).
- **White additionally receives the komi.**

The higher score wins. **Komi**: Freeling notes that Black's first-move advantage
"is not known and can only be guessed", suggesting **4.5 or 5.5** is "probably not
too far off"; this package offers **0 / 4.5 / 5.5** with **4.5 as the default**. A
half-integer komi avoids ties; with komi 0 the game can end in a draw.

> **Note on dead stones.** Under area scoring, capture stones you consider dead
> before passing — they are not removed by agreement. Filling neutral points does
> not change the area score, so passing only once the position is settled gives
> the natural result.

## Notation

A move is the **id of a point** (an integer, shown as `@42` in the move log);
passing shows as `pass`. In the app, click a point to place; **Pass** is a button
beneath the board, and the running area score (with komi) is shown in the caption.

## Credits & sources

- Game © **Mark Berger** (Richard Kramberger), 1975.
- Rules: <https://mindsports.nl/index.php/arena/rosette/1098-rosette-rules>
- History: <https://mindsports.nl/index.php/arena/rosette/1099-about-rosette>
