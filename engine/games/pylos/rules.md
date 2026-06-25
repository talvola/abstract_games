# Pylos

*David G. Royffe (Gigamic).* A two-player pyramid stacking game. Out-build your
opponent so that **you** are the one who places a sphere on the very top.

## Equipment & board

- A **4×4 base** (16 positions).
- **30 spheres**, **15 per player** (one colour each), all starting in each
  player's **reserve**.
- The pyramid has **four levels**, drawn here top-down:
  - **Level 0** — a 4×4 grid (16 positions).
  - **Level 1** — a 3×3 grid (9), each sphere nestling in the hollow at the
    centre of a 2×2 block of level-0 spheres.
  - **Level 2** — a 2×2 grid (4).
  - **Level 3** — the single **apex** (1).
- Position id = `"L,c,r"` (level, column, row). A level-`L` position sits at
  pixel `(c + 0.5·L, r + 0.5·L)`, so higher levels are offset by half a cell and
  overlap the 2×2 below them — giving the pyramid look.

## Your turn — place or raise

On your turn you make **one** of the following (you must move if you can):

1. **Place** a sphere from your reserve onto any **empty valid** position.
2. **Raise** one of your own **free** spheres (a sphere with nothing resting on
   top of it) **up** to a higher empty valid position.

A position is **valid** to place/raise onto iff it is empty **and** its support
is present:

- **Level 0** — any empty base square (always supportable).
- **Level L ≥ 1** — the **2×2 block of four spheres directly beneath it must be
  fully present** (its four supporters are level-`L-1` positions
  `(c,r), (c+1,r), (c,r+1), (c+1,r+1)`).

**Raise constraints:** the moving sphere must be free, the destination must be a
**strictly higher** level, and the moving sphere **may not be one of the four
that support the destination** (you can't lift a sphere onto a spot it props up).

## The square — take back 1 or 2 spheres

If the sphere you just placed or raised **completes a 2×2 square of four spheres
all of YOUR colour** (at any level), you **may** then **take back 1 or 2 of your
own spheres** that are currently **free**, returning them to your reserve.

- Taking back is **optional** — you may keep all of them (take back 0).
- The spheres you take back can be **anywhere** on the pyramid, not just in the
  square, as long as they are **your colour** and **free** (nothing on top).
- Even if a single sphere completes more than one square, you still take back at
  most two.

## Winning

The **first player to put a sphere on the apex** (level 3) **wins immediately** —
whether by placing it from the reserve or by raising a sphere onto it.

A player who **cannot move** (no spheres in reserve and no legal raise) **loses**.
With take-backs recycling spheres the game is normally decided by the apex.

## Move encoding (how clicks work)

- **Place** from reserve = the target position id, e.g. `"0,1,2"` — one click on
  an empty valid position.
- **Raise** = `"from>to"`, e.g. `"0,1,1>1,0,0"` — click your free sphere, then
  the destination.
- After a square-completing move it is **still your turn**: take back a sphere
  with `"take:L,c,r"` (click a free own sphere) up to twice, then press
  **`done`** to end your turn (take back fewer than two, including zero).

## Interpretations & termination

- **Raise onto the apex wins** (it is a placement on the top position).
- **Moving is mandatory** when a legal place or raise exists.
- Because raising plus take-backs **recycle** spheres, play could in principle
  cycle. A **hard ply cap of 300** ends an over-long game as a **draw**; random
  playouts finish (and reach apex wins) far inside that cap.
