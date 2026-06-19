# Order and Chaos

An asymmetric variant of tic-tac-toe on a **6×6** board (Stephen Sniderman, 1981).
The two players have **different goals** and both use **both symbols**.

- **Order** (player 0, moves first) wants to make a line.
- **Chaos** (player 1) wants to prevent one.

## How to play

- On your turn, place **either an X or an O** on any **empty** cell — it does not
  matter which player you are; you may place whichever symbol you like.
- In this implementation a move is a cell plus a symbol, written `c,r=X` or
  `c,r=O`; clicking an empty cell offers an **X / O** picker.

## Winning

- **Order wins** the instant there is a line of **exactly five** identical symbols
  — horizontal, vertical, or diagonal. (It does not matter who placed the fifth
  symbol.)
- A line of **six** identical symbols does **not** count — Order must make exactly
  five.
- **Chaos wins** if the board fills (all 36 cells) with no five-in-a-row.

There are no draws.
