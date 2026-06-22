# Yoté

Yoté is a war game played across West Africa. It is famous for one brutal rule:
**every capture lets you remove a second enemy piece for free.** These are the
rules **as implemented** here.

## The board

A grid of **5 columns × 6 rows** (30 cells), all empty to start. Each player has
**12 men in hand**. Player 1 (red) moves first.

## Your turn — three choices

On your turn you do exactly one of:

- **Drop:** place one man from your hand onto any empty cell.
- **Move:** slide one of your men one step **orthogonally** to an empty cell.
- **Capture:** jump one of your men **orthogonally** over an adjacent enemy man to
  the empty cell beyond, removing the jumped man (as in draughts). You may not
  jump two in a line, and capturing is **not** compulsory.

## The bonus capture

Immediately after a capturing jump you **remove one more enemy man of your
choice**, from anywhere on the board. So each capture costs your opponent **two**
men. (If the jump already took the opponent's last man, there is nothing more to
remove.)

## Winning and draws

You win by **capturing all of the opponent's men** — they have none on the board
*and* none left in hand — or by **leaving them with no legal move** on their turn.
To guarantee the game ends, it is drawn after 50 plies with no capture or drop, by
threefold repetition, or at a hard ply cap.

## Documented simplification

Yoté has several regional variants. This package uses the common ruleset above; it
does **not** implement the optional end-game convention by which a player who has
three men in a row may, in some traditions, claim all the opponent's remaining men.

## Notation

A drop shows as `@c,r`, a step as `a-b`, a capturing jump as `a x b`, and the bonus
removal as `x c,r`. Cells are named by their `col,row` coordinate.
