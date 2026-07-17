# Keil

**Keil** (Luis Bolaños Mures, November 2019) is Go adapted to a hexagonal
board. Plain Go rules on a hex grid lose crosscuts and ko because every point
has six neighbours — the board is "too connected". Keil restores them with one
idea, **linking**, which weakens the board's connectivity; otherwise the rules
are the same as in Go. Played here on the cells of a **hexhex board**
(equivalent to the designer's "intersections of a hexagonal grid of triangles"),
sides 4–7 via the *Board size* option, default side 5 (61 points).

## Linking (the defining rule)

> Two adjacent points, and any stones on them, are **linked** if there is
> another point adjacent to both that is the **same type** as at least one of
> them. Two points are the same type if they are either both empty or both
> occupied by stones of the same color.

Every adjacent pair has two such "witness" points in the interior (one along
the board edge). Consequences:

- Two adjacent **same-colour stones** connect only if a *third stone of that
  colour* is adjacent to both (the designer: stones "are not permanently
  connected until there is a third, same-color stone adjacent to both").
- A **crosscut** exists: two adjacent black stones whose two witnesses are both
  white are mutually cut — four stones, four separate groups.
- A **group** is a maximal set of like-coloured stones connected by links. A
  **liberty** of a group is an empty point *linked* to one of its stones (an
  adjacent empty point whose witnesses are all enemy stones is NOT a liberty —
  so a corner stone can be captured by just two enemy stones).
- A **territory** is a maximal set of empty points connected by links (two
  adjacent empties link via an empty witness). You **own** a territory if all
  stones linked to its points are yours.

## Play

- **Black plays first**; turns alternate. On your turn: place a stone on an
  empty point, take the **button** (if still available), or **pass** (only
  legal once the button has been taken).
- After a placement, **all enemy groups without liberties are removed**. Then
  the placed stone's group must have at least one liberty (**no suicide**), and
  the position must differ from the positions at the end of **all your own
  previous turns** (the repetition rule that handles ko: an immediate ko
  recapture recreates your previous position and is illegal; after a ko-threat
  exchange it becomes legal again). Two otherwise identical boards are
  *different* positions if the button had been taken in one but not the other.

## Komi, button, scoring

- **Komi pie**: before play, the first player names a **whole-number komi**
  (buttons `komi=0` … `komi=12`), then the second player **chooses sides**
  (`black` = swap, `white` = keep). Komi is added to White's score.
- **The button**: while it is unclaimed, passing is illegal, but you may take
  the button instead of a board play. Whoever holds it scores an extra **half
  point**. Because a game can only end after the button is gone, a whole komi
  plus the button makes **ties impossible**.
- The game ends on **two consecutive passes**. Score = your stones on the board
  + points in your territories (+ komi for White, + ½ for the button holder);
  higher score wins.

## Sources

- [Sensei's Library: Keil](https://senseis.xmp.net/?Keil) — the designer's
  current ruleset (implemented verbatim; the designer-written BGG description
  is word-for-word identical).
- [BGG entry 295889](https://boardgamegeek.com/boardgame/295889/keil); the
  designer-endorsed [MindSports implementation](https://mindsports.nl/index.php/the-pit/1029-keil)
  states the same linking rule verbatim. The designer's rules thread on
  lifein19x19 (Dec 2019) has an earlier, **superseded** wording of the linking
  rule that is a genuinely different predicate (there, two adjacent empty
  points are *always* linked and two same-colour stones link via an *empty*
  witness) — all three current designer-authored sources agree on the "same
  type" rule implemented here.

## Interpretations / notes (as implemented)

- **Komi range 0–12** is our discretisation of "the whole number of points"
  (the designer's sample game used komi 6).
- **Board sizes**: the rules name no size; the designer's sample game is a
  side-7 hexhex (its published score, 67 + 60 board points, is exactly 127 =
  the side-7 point count). Default here is side 5 for playable game length.
- A territory linked to **no stones at all** (e.g. an empty board) is neutral —
  the page's ownership condition is vacuously true for both players there, and
  Go convention (Tromp–Taylor) scores such regions for no one.
- A hard ply cap (3× board points) guarantees termination; a game cut off at
  the cap is scored as it stands, where a tie (possible only if the button was
  never taken) is an honest draw. Normal double-pass endings cannot tie.
