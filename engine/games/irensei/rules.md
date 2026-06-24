# Irensei (囲連星)

Irensei — "surrounding-connected-stars" — is a hybrid of **Go** and **Gomoku**,
played with Go stones on a **19×19** Go board. It keeps Gomoku's line-making goal
but borrows Go's capturing, so a connection game becomes a fight over territory and
liberties.

## Setup
- Board: 19×19 intersections, empty to start.
- **Black moves first**; players then alternate.

## A turn
Place one stone on any empty intersection (or **pass**). After you place:

1. **Captures resolve (Go rules).** Any opponent group with no liberties is
   removed, then — only if you captured nothing — your own group is checked
   (see Suicide). Liberty/adjacency is **orthogonal only**.
2. **The win is checked on the resulting board** (after captures).

## How to win — the signature rule
The goal is an **unbroken line of seven stones** — horizontal, vertical, or
diagonal — **but every stone of that line must lie inside the central 15×15
area.** The **outer two lines on every side of the board are excluded**: a line of
seven that touches any point on the two outermost rows or columns is **not** a
win.

- On a 0-indexed 19×19 board, the valid (inner) coordinates are **2…16** on both
  axes. The first two and last two rows/columns can never be part of a winning
  line.

### Black vs. White asymmetry (offsets the first-move advantage)
- **Black** must make **exactly seven** in a row. A Black **overline** (eight or
  more in a row, inside the central area) is **not a win — Black loses
  immediately** when such an overline is formed (the opponent wins). The single
  exception: if the same move also completes a valid **exact-seven** line, that
  seven wins for Black.
- **White** wins with **seven or more** in a row. Overlines are fine for White, as
  long as a span of seven consecutive White stones lies wholly inside the central
  area.

Because the win is judged after captures, a move that captures opposing stones and
thereby completes your own seven-in-a-row wins, and a move whose own line gets
captured does not.

## Go rules that apply
- **Capture:** a group with no orthogonal liberties is removed (diagonal contacts
  count only for winning lines, never for capture or liberties).
- **Suicide is illegal** — *except* a suicidal move that simultaneously completes a
  winning seven-in-a-row is allowed (it wins before the self-capture matters).
- **Ko / positional superko:** a move may not recreate any earlier whole-board
  position.

## End of game
- The game ends the moment a player forms a valid winning line (or Black forms a
  forbidden overline → opponent wins).
- If the board fills (361 stones) or a hard ply cap is reached with no winner, the
  game is a **draw**. (Documented Irensei games always end in a line; a full board
  is essentially unreachable and is scored as a draw only to bound the game — the
  classic sources do not define a board-full result.)

## Interpretations / notes (as implemented)
- "Outer two lines" is read as the two outermost rows/columns on each side, i.e.
  the winning seven must lie within the central **15×15** square (coordinates
  2…16). This matches the Wikipedia / Online-Go descriptions.
- The Black overline ban and White's "seven-or-more" allowance follow the
  Online-Go Irensei rules thread and Wikipedia.
- A board-full draw is a platform-imposed bound (no documented natural outcome).

## Sources
- Irensei — Wikipedia: https://en.wikipedia.org/wiki/Irensei
- Irensei — BoardGameGeek: https://boardgamegeek.com/boardgame/48871/irensei
- "Irensei" — Online-Go (OGS) Go-variants discussion:
  https://forums.online-go.com/t/irensei/51897
