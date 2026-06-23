# Tsoro Yematatu

**Tsoro Yematatu** ("the stone game played with three") is a traditional
two-player abstract game of the **Shona** people of **Zimbabwe**. It is a
three-in-a-row game played on one of the simplest boards known — only **seven
points** — but the ability to *jump* gives it real depth. The rules below are
the rules **as implemented** in this package.

## The board (seven points, five lines)

The board is an **isosceles triangle** with one line drawn **across its breadth**
(the horizontal midline) and another running **down its central axis** (the
vertical median). Their intersections give **7 points**, laid out as an apex over
two rows of three:

```
              0          (apex)
            / | \
          1 - 2 - 3      (horizontal midline)
        /     |     \
      4 ----- 5 ----- 6  (base)
```

Points are named by their `x,y` grid coordinate on this diagram (`0`..`6` above
are just labels; the actual ids are the coordinates shown on the board).

The board has exactly **five straight lines of three**, and these are the only
connections — two points are **adjacent** iff they are consecutive on one of
these lines:

| Line | Points |
|---|---|
| Left side | `0 – 1 – 4` |
| Right side | `0 – 3 – 6` |
| Horizontal midline | `1 – 2 – 3` |
| Base | `4 – 5 – 6` |
| Central axis | `0 – 2 – 5` |

So, for example, the apex `0` is adjacent to `1`, `2` and `3`; the centre `2` is
adjacent to `0`, `1`, `3` and `5`; a base corner such as `4` is adjacent only to
`1` and `5`. (Note `1` and `4` are **not** adjacent across to `3` and `6` — only
along a drawn line.)

These same five lines are the **winning lines**.

## Pieces

Each player has **three men** (the "three" of the name). One side is White (red
in the app), the other Black; White places first.

## Phase 1 — placement

Players **alternate placing** one of their men on any **empty** point until each
has placed all three (six placements in all).

## Phase 2 — movement

Once all six men are on the board, a turn is one of:

- **Slide** — move one of your men along a board line to an **adjacent empty**
  point; or
- **Jump** — move one of your men over an **adjacent** man (your own *or* the
  opponent's) along a straight board line, landing on the **empty point beyond**.

**Jumps do not capture** — the jumped man stays exactly where it is. A jump is
only legal when the three points (start, jumped, landing) are the three points of
one board line, the middle one is occupied, and the far one is empty (e.g. from
`4`, over `5`, to `6`).

In the move log a slide is shown as `from-to`, a jump as `from^to`, and a
placement as `@point`.

## Winning

You **win** by getting your three men onto the three points of any one of the
five board lines (three in a row).

**Standard rule — three-in-a-row must be made in the movement phase.** A line
that happens to be completed *during placement* does **not** win. This is the
implemented default and reflects how the game is actually played: it stops the
first player from trivially dropping all three men onto a line and winning before
the game has begun, and keeps Tsoro Yematatu the *movement* game it is named for.
Concretely, a three-in-a-row only counts as a win once **both** players have
placed all three of their men.

This behaviour can be changed with the **"Winning during placement"** option: set
it to *Allowed* and a line completed while still placing wins immediately. The
default is *Disallowed* (standard).

> **Ruleset note / chosen interpretation.** Published descriptions of Tsoro
> Yematatu agree on the 7-point figure above, the place-then-move structure, the
> non-capturing jump (over friend or foe), and the three-in-a-row goal, but are
> not explicit about whether a placement-phase line should win. Because allowing
> it makes the game a trivial first-player win, this package adopts the common
> "**must form the row in the movement phase**" interpretation as the default,
> and exposes the alternative as an option rather than baking in an unplayable
> rule. We do **not** implement a separate "you may not win on the exact line you
> originally placed on" restriction — the simpler movement-phase rule already
> prevents the degenerate opening and is the more widely described convention.

## Draws and termination

If **60 movement plies** pass with no new placement and no win, the game is
declared a **draw**. (Placement always resets this clock; it exists both as a
sensible stalemate rule and to guarantee the game terminates.)
