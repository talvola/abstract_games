# Crossway

A connection game for two players by **Mark Steere** (June 2007), played with a
Go set. *(Rules as implemented in this package.)*

## Goal

- **Black** (player 0) wins by forming a contiguous chain of Black stones
  connecting the **top (North)** edge to the **bottom (South)** edge.
- **White** (player 1) wins by connecting the **left (West)** edge to the
  **right (East)** edge.

A corner cell counts as part of **both** of its adjoining edges.

## Connectivity

Two of your stones are connected when they are adjacent **orthogonally OR
diagonally** (the 8 king-move directions). A chain is any sequence of your
stones each connected to the next. You win the instant such a chain spans your
two goal edges.

## Placing & the Crossway rule

On your turn you place **one** stone of your colour on any empty cell — **except**
you may never place a stone that **completes the forbidden crossing formation**:
a 2×2 square whose two diagonals are filled with opposite colours, so the two
diagonal links would cross.

The two forbidden 2×2 patterns (a pattern and its 90° rotation) are:

```
 B W        W B
 W B        B W
```

Equivalently: you may not place at a cell if, in some 2×2 square containing it,
the diagonally-opposite corner is **your** colour while **both** of the other two
corners are the **opponent's** colour.

Because that checkerboard can never appear, no two opposite-colour diagonal
connections ever cross — that is the whole point of the game (its name). This is
the only placement restriction; everything else is plain 8-adjacency.

If you have **no legal placement**, you forfeit the turn (**pass**) and your
opponent keeps placing until someone connects.

## No draws

Like Hex, **Crossway can never end in a draw** — when the board can take no more
stones, exactly one player has connected their edges. Termination is therefore
automatic; there are no draw or repetition caps.

## Pie rule (swap)

Black places first. On White's first turn, instead of placing, White may
**swap**: take over Black's opening. Because the goals are transposed (Black
joins the top/bottom edges, White the left/right), the swap reflects Black's
lone stone across the main diagonal — (c,r)→(r,c) — and recolours it White, so
White's position is exactly as strong as Black's was. This equalises the
first-move advantage and can be used only once, only on move 2.

## Board size

Crossway is traditionally played on a 19×19 Go board. This package offers
**9 / 11 / 13 / 19**, defaulting to **13** for quicker play.

Official rules: <https://www.marksteeregames.com/Crossway_rules.pdf>
