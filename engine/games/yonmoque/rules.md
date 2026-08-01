# Yonmoque

**Yonmoque** ("yon" = four, "moku" = the counting word for stones in a row) was
designed by **Mitsuo Yamamoto** and is published by **Logy Games** (Japan, 1997).
Two players, 25 squares, six pieces each — but the board's squares are coloured,
and a piece's colour decides how far it may travel. The rules **as implemented**
here are described below; every interpretive decision is named at the end.

Official rules: [logygames.com/english/yonmoque.html](http://www.logygames.com/english/yonmoque.html)

## Seats

Seat 0 (**Red** on screen) is the **first** player — the physical game's *blue*.
Seat 1 (**Blue** on screen) is the **second** player — the physical game's
*white*. The platform's palette is used for the pieces and for the board tints,
so *your* pieces and *your* squares always share a colour.

## The board

The 5×5 board has three kinds of square: **8** belonging to the first player,
**12** belonging to the second, and **5 neutral** ones. They are laid out by
distance from the centre:

- the **centre** square and the **four corners** are **neutral**;
- the eight squares at *Manhattan distance 2* from the centre — the diamond
  ring — are the **first player's**;
- everything else (distance 1 or 3) — the twelve remaining squares — are the
  **second player's**.

```
  N  W  B  W  N        N = neutral            (5)
  W  B  W  B  W        B = first player's     (8)
  B  W  N  W  B        W = second player's   (12)
  W  B  W  B  W
  N  W  B  W  N
```

Note the asymmetry: the second player's squares form a much larger network. The
first player moves first as compensation — "To keep the balance between blue and
white, the blue player always plays first."

The pattern is unchanged by any rotation or reflection of the board, so the
board has no orientation.

## A turn

On your turn you must do exactly one of:

- **Place** one piece from your hand on any **empty** square, or
- **Move** one of your pieces that is already on the board.

Both are available while you still hold pieces (there is no separate "drop
phase"). Once your hand is empty you must move. Your very first turn is
necessarily a placement — you have nothing on the board yet. **You may not pass**:
if you can neither place nor move, you **lose** (see *Losing*).

## Moving

A piece may move in either of two ways:

1. **One step** to any adjacent **empty** square — all eight directions,
   orthogonal and diagonal (a chess king's step). The destination may be any
   colour, including a neutral square.
2. **A slide** — only if the square it currently stands on is **its own
   colour** — any distance in a straight **diagonal** line, along squares of its
   own colour. Every square it passes over, and the square it lands on, must be
   **its own colour** and **empty**. Neutral squares are neither player's, so
   they stop a slide.

Because the second player owns *every* odd square, a second-player slide is a
plain bishop move blocked only by pieces. The first player's eight squares form
a ring whose corners are broken by neutrals, so a first-player slide is at most
two squares and only along one of the four sides of the diamond.

## Flipping

Pieces are two-sided, one colour per face. If your **move** lands a piece so
that an unbroken line of one or more **enemy** pieces lies between it and
another of **your** pieces — horizontally, vertically or diagonally — every
enemy piece in that line is **flipped** to your colour.

- Flipping happens **only on a move, never on a placement**.
- It is **mandatory and total**: you may not decline it or flip only some.
- A gap (an empty square) in the line breaks the sandwich, and so does the edge
  of the board.
- Pieces of **your own** colour caught between two enemy pieces are **not**
  flipped.
- The square you just vacated is empty, so it can never be the far end of a
  sandwich.

Several directions can flip on the same move. Pieces are never removed from the
board — only converted — so the twelve pieces are conserved.

## Winning: four in a row, **made by a move**

You **win** the moment a **move** of yours creates a line of **four** of your
colour — in any direction, including diagonally. Pieces that your move *flipped*
count: a four completed entirely by flipped pieces still wins.

A four created by a **placement** does **not** win. The game simply continues,
and that standing four does not win on some later turn either — the four has to
be *created* by the move that claims the win. (Breaking it and remaking it works,
but that gives your opponent a turn in between.)

## Losing: five in a row, ever

If you ever create a line of **five** of your colour — **by moving or by
placing** — you **lose** immediately. Making five is a legal move; it is simply
a losing one. Five is checked before four, so a move that makes a five never
wins, however many fours it also makes.

## Losing: no legal move

"Players must either place or move a piece; if they cannot, they lose." That
happens when your hand is empty **and** every one of your pieces is hemmed in on
all sides — or when your last piece has been flipped away and you have nothing
left to place. While you hold even one piece in hand you always have a move:
there are 25 squares and at most 12 pieces, so an empty square always exists.

## Drawing

The published rules contain **no** draw, repetition or move-count rule at all —
"Play continues until either a player has won (4 in a row), or a player has lost
(5 in a row)". Because pure movement can in principle repeat forever, this
package declares an honest **draw** after **412 plies** (the at most 12
placement plies plus a 400-ply movement allowance). This is a practical
backstop, not a rule of the game: over **60,000 random games** the longest ran
**125 plies** and not one reached the cap. A decisive result always outranks
the cap — a win, a five-in-a-row loss or a no-move loss on the capping ply is
still decisive.

## Notation

- A placement is the square, e.g. `@2,3`.
- A move is `from-to`, e.g. `1,2-2,3`; `x2` means it flipped two pieces, `#4`
  that it won with four in a row, `!5` that it made a losing five.
- Squares are `column,row` with `0,0` at one corner. The board has no
  orientation, so the labelling is arbitrary.

## Interpretive decisions

Every point below was decided from the publisher's own page — the current
"Complete Rules" text, its two diagrams, and the noticeably more explicit **2016
revision** of the same page (archived at the Internet Archive), which is quoted
where it settles something.

1. **The tile map.** The page gives only a census ("8 blue, 12 white and only 5
   neutral spaces") and the 2016 sheet's "the half white and half blue squares,
   **at the center and on the corners**, are neutral". Those two facts, plus the
   fact that a colour must form diagonal *chains* for the bishop slide to mean
   anything, determine the map uniquely: a diagonal step preserves the parity of
   *column + row*, the 13 even squares are the centre, the four corners and the
   eight-square ring, and the 12 odd squares are the rest. The publisher's board
   photograph and movement diagram show exactly this.
2. **Flipping direction.** The current sheet says only "between two of theirs".
   The 2016 sheet is explicit: "surrounds an opponent's pieces in a line
   (**horizontally, vertically or diagonally**)". All eight directions.
3. **Slides are diagonal only.** "may move as many spaces as the player chooses
   in a diagonal straight line"; 2016: "may move along the entire chain of white
   squares (**like a Bishop in Chess**)". (On this board no two orthogonally
   adjacent squares ever share a colour, so a "rook" reading would in fact be
   indistinguishable — but the sheets are explicit.)
4. **A four completed by flipped pieces wins.** The sheet attributes the win to
   "when moving one of their pieces to a new space they create 4-in-a-row"; the
   flip is part of that move, and the 2016 sheet's own worked example ends with
   a four made partly of just-flipped pieces.
5. **A standing four does not win later.** The win is for *creating* four with a
   move. A four left over from a placement is inert until it is remade.
6. **Five outranks a simultaneous four.** A single move can make a five in one
   line and an independent new four in another (it happened 80 times in 695,000
   random plies). The sheet states the five-in-a-row loss unconditionally and
   offers no tie-break, so the loss wins.
7. **Making five is legal, not forbidden.** "A player *can lose* the game by
   moving or placing a piece to create 5-in-a-row" — so such moves stay in the
   legal-move list.
8. **Placement never flips and never wins**, both stated outright.
9. **The draw** is this package's addition; the game as published has none.
