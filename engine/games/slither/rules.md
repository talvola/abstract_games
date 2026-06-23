# Slither

**Slither** (Corey Clark, 2010) is a modern connection game played on a square
grid of intersections. It is best known for its distinctive *slide-then-place*
turn and its *no-bare-diagonal* placement restriction.

## Board and goal

- An **N×N square board** of intersections. Clark recommends **8×8 as a
  minimum**; this package defaults to **8×8** and offers 6, 8, 10 and 12 via the
  *Board size* option.
- **Black (player 0)** aims to connect the **top** edge to the **bottom** edge.
- **White (player 1)** aims to connect the **left** edge to the **right** edge.
- The four **corner intersections belong to both sides**.
- **Black moves first.**

## A turn

On your turn you perform two actions, **in this order**:

1. **Optional slide.** You *may* move one of your own stones already on the
   board to an **orthogonally or diagonally adjacent empty intersection** (a
   chess **king's move**, one step in any of the 8 directions). You may also
   skip the slide.
2. **Mandatory place.** You **must** place a **new** stone of your colour on an
   empty intersection. (After a slide, the cell you vacated is empty and is a
   legal placement target.)

The whole turn — the optional slide plus the placement — is a single move.

## The no-bare-diagonal rule (the defining constraint)

At the **conclusion of your turn**, your position may contain **no "bare"
diagonal connection**:

> Every pair of your stones that are **diagonally adjacent** must share at least
> one common **orthogonally-adjacent** stone of your colour.

In other words, two of your stones touching only at a corner are illegal *unless*
a third like-coloured stone sits in one of the two cells orthogonally adjacent to
**both** of them (filling out the corner). Both the slide and the placement must
respect this — the test is applied to the final board after the whole turn. The
slide exists precisely so you can reshape your group to legalise an otherwise
bare diagonal.

This rule constrains only **diagonal** contacts. Orthogonal adjacency of your own
stones is always fine.

## Winning

You win the instant you form an **unbroken orthogonal chain** of your own stones
linking your two opposite edges:

- **Black:** top row to bottom row.
- **White:** left column to right column.

Connection counts **only in the orthogonal directions** — diagonal contact does
*not* join a chain for the purpose of winning (it is governed by the legality
rule above, not by the connection itself). The win is checked on the board after
your move, so only the player who just moved can win on their turn.

## Move notation (clickable)

- **Place only:** the target cell id, e.g. `3,4`. One click on the empty cell.
- **Slide + place:** `from>to>place`, e.g. `2,2>2,3>5,5`. Click your stone, then
  the empty adjacent slide target, then the empty placement cell.

Cell ids are `col,row`, 0-indexed, with row 0 drawn at the top.

## Termination

*Deviation from the published rules, for guaranteed termination (flagged):* in
the original game a player with no legal turn **passes**, and Slither **cannot
end in a draw** — one side eventually completes a connection. This engine
requires every game to terminate, and the optional slides admit cycles, so this
package instead treats **no legal turn as a loss** for the stuck player and
declares a **draw at a hard ply cap (400 plies)**. Both differ from the strict
ruleset only in rare/degenerate positions (a player almost always has a legal
placement, and real games connect well before 400 plies); the core
connect-your-edges game is unchanged.

## Ruleset choices and flags

- **Core rules faithful to the published game** (the one deviation is the
  termination handling noted above). Independent sources (LittleGolem rules
  docs, MindSports, and Clark's own description) agree: the restriction is on
  **bare diagonal** contacts and the win is an **orthogonal** chain. This
  package implements that. *(Note: an earlier informal brief described the rule
  inversely — as forbidding orthogonal self-adjacency with a diagonal win. That
  is not the real game; this package follows the published rules.)*
- **First player.** Sources differ — BoardGameGeek lists Black first; MindSports
  lists White first with a swap option. This package has **Black move first**,
  matching the platform convention that seat 0 owns the top/bottom edges.
- **Pie / swap rule omitted.** Some presentations grant the second player a swap
  after the first move. This package does **not** implement it (documented
  omission); board sizes and first-move balance are left to the players.
- **Advanced Slither** (a variant where a stone may move only if it is part of a
  mixed-colour orthogonal group) is **not** implemented.

## Sources

- BoardGameGeek — *Slither* (Corey Clark, 2010).
- LittleGolem rules documentation for Slither.
- MindSports — Slither.
