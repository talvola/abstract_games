# Mirador

Connection game by **Andrew Perkis** (first published in *Games* magazine, January 2010;
presented in *Abstract Games* #22 with an annotated game by Paul van Wamelen; long
playable on SuperDuperGames). Rules as implemented here.

## Board and placement

- The board is a **27×27 grid** of small squares.
- A move fills an empty **2×2 block** in your colour — a **mirador**. It is named by its
  bottom-left square: letter (column A–Z) + number (row 1–26), e.g. `E4` (676 possible
  first placements).
- **Miradors may never overlap or touch** — not along sides and not corner-to-corner —
  with one exception: **two miradors of the same colour may touch corner-to-corner**
  (diagonally).
- **Green** moves first. **Pie rule:** instead of placing, the second player's first move
  may be `swap` — they take over the opening mirador as Green, and the first player
  continues as Blue. (Both colours have identical goals, so the mirador is simply
  re-owned in place.)

## Connection

Two miradors of the same colour are **connected** if:

- they touch **corner-to-corner**, or
- there is an **unobstructed line of sight** between them: an empty corridor **one full
  square wide**, along a row or column that *both* miradors cover (any square of either
  colour in the corridor blocks it — a friendly mirador in the corridor is itself a relay,
  not a bridge).

A mirador is connected **to a side of the board** if one of its own rows/columns runs
unobstructed to that edge (touching the edge counts).

## Winning — declaring and challenging

You win by building a chain of connected miradors linking **either pair of opposite
sides** (left–right or top–bottom; *either* player may connect *either* axis). Because a
connection only counts if it is unbreakable, wins are adjudicated by declaration:

1. **After placing**, if your miradors currently link two opposite sides, you may
   **Declare** (or *Continue* and keep playing). The declare button appears only when a
   side-to-side chain actually exists — declaring without one is a guaranteed loss, so it
   is not offered.
2. Your opponent then **challenges**: they place miradors, as many turns in a row as
   they like, trying to cut the declared connection.
   - The moment your colour no longer links two opposite sides (on **any** axis), the
     challenge succeeds and **the challenger wins the game**.
   - If the challenger cannot break it, they **Accept** (or run out of legal
     placements), and **you win**.

The declarer does not specify an axis: they win if *any* side-to-side connection
survives the challenge (a simultaneous double connection is possible and legal).

## End without declaration (interpretation)

The published rules don't cover a fully locked board. Here: if the player to move has no
legal placement, they must declare if they have a side-to-side chain; otherwise the game
ends in a **draw**.

## Notes

- Move entry: click the **bottom-left square** of the 2×2 you want to fill.
- Notation in the move log matches the magazine: letter+number of the anchor square.
- The magazine's printed move list for the annotated game contains a typo ("16. O16",
  which would overlap 12. P16); the final-position diagram shows the move was **C16**,
  which this implementation's replay test uses.

Sources: *Abstract Games* #22 pp. 35–38; the designer's rules
(miradorthegame.blogspot.ca, the SuperDuperGames rules PDF). Cross-checked against the
AbstractPlay implementation coded by fritzd (the Green player of the annotated game).
