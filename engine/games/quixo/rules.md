# Quixo

Quixo (Gigamic) is a five-in-a-row game played with 25 cubes on a 5×5 frame.
Each cube has three kinds of face: **blank**, a **cross (X)** and a **circle (O)**.
All 25 cubes start blank. **X is player 1 (red); O is player 2 (blue).**

## Your turn

1. **Take** a cube from the **border** — the 16 cubes on the outer ring. You may
   take a cube that is **blank** or that **already shows your own symbol**. You may
   **never** take a cube showing your opponent's symbol.
2. The taken cube is **stamped with your symbol**.
3. **Push it back** into the same row or column from one edge. The cube re-enters
   at that edge and every cube between the edge and the gap it left **shifts one
   step** to fill the gap. The cube must actually move, so you cannot simply put
   it back where it came from.

A cube on an edge can be pushed back from up to three edges; a corner cube from
two.

## Notation

A move is `c,r=DIR` — the taken border cell `c,r` (column,row, 0-indexed from the
top-left) plus the **edge the cube re-enters from**:

- `L` — from the **left** (valid unless the cube is already in column 0)
- `R` — from the **right** (unless column 4)
- `U` — from the **top** (unless row 0)
- `D` — from the **bottom** (unless row 4)

In the web UI, click a border cube and pick one of the offered directions.

## Winning

After your slide, a straight line of **five of your symbol** — any row, column,
or diagonal — wins.

Because a slide shoves a whole line, it can complete a line for **either** player:

- If your move makes a five of **your** symbol, **you win**.
- If your move makes a five of **only your opponent's** symbol, **your opponent
  wins** (you must avoid handing them the game).
- If a single move makes five for **both** symbols at once, the **mover wins**.

## Termination

Quixo has no natural draw, but to guarantee the engine's random-play conformance
terminates, a no-progress cap of **400 plies** ends an unresolved game as a draw.
This never binds in real play.
