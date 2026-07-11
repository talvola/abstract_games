# Flipway

A drawless connection game by **Luis Bolaños Mures** (July 2020), played on
the points of a square board. *(Rules as implemented in this package.)*

## Goal

- **Black** (player 0) wins by connecting the **top** and **bottom** edges.
- **White** (player 1) wins by connecting the **left** and **right** edges.

A winning chain is a sequence of your stones each **orthogonally** adjacent
to the next (no diagonals), touching both of your edges. **Draws are not
possible** (see below).

## Play

To start, **Black places a single black stone** on any empty point. From then
on, starting with White, the players take turns. On your turn you **must**
perform exactly one of these actions:

- **DROP** — Select a 2×2 area including one or more empty points, *such that
  no other 2×2 area includes all those empty points as well as at least
  another empty point*. Place a stone of your colour on **each empty point**
  in the selected area.
- **FLIP** — Replace the **two enemy stones in a crosscut** with stones of
  your colour. A *crosscut* is a 2×2 area containing two diagonally adjacent
  black stones and two diagonally adjacent white stones.

The condition on DROP is a **maximality rule**: the set of points you fill
must not fit inside any 2×2 window that still has a further empty point. The
designer's equivalent phrasing: fill a 2×2 area's empty points; while all
stones placed so far also fit in a different 2×2 area with an empty point,
fill that one too — at most four stones per turn.

In the UI, click the cells of a drop (in left-to-right, bottom-to-top order)
or the two enemy stones of the crosscut you want to flip.

## Options

- **Board size** — 6×6 … 16×16 (the Zillions edition offers 3×3 up to 40×40).
- **Starting position** — *Empty board* (standard), or the designer's
  **Checkered** / **Bicheckered** variants: the board starts completely full
  in a checkerboard (or 2×2-block checkerboard) pattern, so the game is all
  crosscut flips. Black still moves first: per the designer's description,
  Black's opening move is **replacing any single white stone with a black
  stone** (the full-board analogue of the single-stone opening); from White
  on, normal turns (flips) follow.

## Drawlessness & termination

On a full square board where neither player connects orthogonally, a crosscut
always exists, so there is always a legal move; and flip cycles are
impossible (a flip never decreases the number of orthogonally adjacent
same-colour pairs), so play always ends with exactly one winner. As a purely
defensive backstop this implementation also ends the game in an **honest
draw** if a hard ply cap (10·n²+100) is ever hit or a full, crosscut-less,
winner-less board is ever reached — both unreachable per the argument above,
and never observed across thousands of random playouts.

## Implementation notes / interpretations

- Source of truth: the designer's ReadMe in Zillions of Games submission
  id 3051 (identical wording on the BGG game page). The Zillions `.zrf` is
  machine-generated and only checks the win on 3×3–5×5 boards; the win check
  here is a proper orthogonal flood-fill on every size.
- The Zillions bundle's 60 variants = board sizes × {plain, checkered,
  bicheckered} plus colour-mirrored copies of the checkered patterns; the
  mirrors are omitted (they are the same game with colours swapped). Our
  checkered patterns put White on the corner point (matching the primary
  Zillions files); only even board sizes are offered so both patterns fill
  the board evenly.
- There is no pie/swap rule in the base rules — Black's single-stone opening
  (versus multi-stone drops afterwards) is the balancing mechanism. The
  designer's BGG description also offers an optional *Pie* variant (Black
  opens with 1–4 stones in a 2×2 area, then White may swap sides); it is not
  implemented here, matching the Zillions edition.
- Checkered-family opening: the BGG description says Black replaces **any**
  white stone; the Zillions files effectively restrict this to a white stone
  of a crosscut (identical on the plain checkered start, where every white
  stone is in a crosscut; slightly more permissive here on the bicheckered
  start). We follow the description's wording.
