# Lotus

**Christian Freeling** (1980s). Lotus and its ancestor *Medusa* are featured in
R. Wayne Schmittberger's *New Rules for Classic Games* (John Wiley & Sons, 1992).
Official rules: [MindSports](https://mindsports.nl/index.php/the-pit/538-lotus).

Lotus is a Go-like territory game with **Othelloanian (flip) capture**: captured
stones are never removed from the board — they are turned over to the capturer's
colour.

## The board

Play is on the **72 intersections** (vertices) of the Kensington
rhombitrihexagonal (3.4.6.4) board — the same point set as *Kensington*. Every
point has 3 or 4 neighbours along the drawn lines. The board contains **7
hexagons**; the six points around any one hexagon form a **lotus**.

## Stones and moves

Each player has plenty of **bi-coloured "flip" stones** — White on one face,
Black on the other. **White moves first.** On your turn you either:

- **Place** one stone on any vacant point, or
- **Pass.**

Passing is always allowed and does not forfeit your right to move later.

## Groups, liberties and the lotus

A **group** is one stone or several connected stones of the same colour. Its
**liberties** are the adjacent vacant points, shared across the group.

- A group **lives unconditionally** if it contains a **lotus** (all six points
  around one hexagon of that colour). A lotus group can never be flipped.
- Any other group lives only while it has at least one liberty.

## Capture — reversal, not removal

Assuming no group involved is protected by a lotus, placing a stone may cause:

1. **One or more enemy groups with no liberty.** They are **captured and
   reversed** (flipped) to your colour in the same turn, uniting with your
   adjacent groups into one new group.
   - **Cascade:** this new group may *itself* have no liberties. In that case
     the original capture was in fact suicidal, and a **second reversal** flips
     the whole new group back to the opponent.
2. **Your own group left with no liberty.** If you also captured an enemy group
   (case 1), that procedure applies instead. Otherwise the move is **suicide** —
   and **suicide is legal**: your liberty-less group flips to the opponent.
3. **Neither** — an ordinary placement.

A lotus-protected group at zero liberties simply lives; it is skipped by capture.

Because stones are only ever **added or flipped, never removed**, no *ko* rule is
needed and the number of stones on the board strictly increases — so the game is
guaranteed to end (at most 72 placements, then only passes remain).

## The pass marker

A marker sits on a **15-point track** centred between the players (the centre is
0, with up to **7 points toward each side**). Each time you pass, the marker
moves **one point toward you** (clamped at 7). At the end of the game, the side
the marker rests on adds that many points to its score.

## End of game and scoring

The game ends when **both players pass on successive turns** (or by resignation).
Each player's score is:

- the number of **their stones** on the board, plus
- the number of **empty points bordered only by their colour**, plus
- the **marker points**, if the marker is on their side.

Empty regions bordered by *both* colours (or by neither) are **seki / neutral**
and count for no one. The higher total wins; an exact tie is a **draw**.

### Implementation notes / interpretation

- **Dead-stone adjudication.** The official rules say that after a double pass
  "dead stones are reversed." This engine does **not** auto-detect dead stones:
  it scores the final position exactly as it stands (an area count — stones +
  solely-bordered empty regions + marker). Because captures resolve fully on the
  board and suicide is legal, dead groups can always be captured by playing them
  out, so the played-to-resolution position is the source of truth. This mirrors
  Tromp-Taylor-style area scoring used for the platform's Go.
- **Marker track.** Modelled as a signed offset in the range −7…+7 (15 points
  total, centre 0). "The corresponding number of points" is the marker's
  distance from the centre.
- **Termination safety net.** In addition to the double-pass end, a hard ply cap
  (4 × 72) guards random self-play; normal games end well before it.
