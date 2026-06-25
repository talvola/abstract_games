# Arimaa

Arimaa was invented by Omar Syed in 2002 as a game that is simple for humans but
was deliberately hard for computers. It is played with chess-like equipment on a
standard 8x8 board. Official rules: [arimaa.com/arimaa/learn](https://arimaa.com/arimaa/learn/).

## Board and traps

- 8x8 board. Files **a-h** (columns 0-7), ranks **1-8** (rows 0-7).
- Four **trap squares**: **c3, f3, c6, f6** (shown tinted). Any piece standing on a
  trap with no orthogonally-adjacent friendly piece is immediately captured.

## Pieces and strength

Each side has 16 pieces:

- 1 **Elephant** (E) — strongest
- 1 **Camel** (M)
- 2 **Horses** (H)
- 2 **Dogs** (D)
- 2 **Cats** (C)
- 8 **Rabbits** (R) — weakest

Strength order: **E > M > H > D > C > R**.

**Gold** is player 0 (home rows 1-2 / rows 0-1, bottom). **Silver** is player 1
(home rows 7-8 / rows 6-7, top). **Gold moves first.**

## Setup phase

Before play, each player **deploys all 16 pieces** onto their own two home rows in
any arrangement. Gold places all 16 first (one at a time), then Silver places all
16. This is the full free Arimaa setup (not a fixed opening).

## The turn: up to four steps

A turn is **1 to 4 steps**. A **step** moves one of your pieces one square
orthogonally (N/E/S/W) to an **empty** square. You may spread the steps over
several pieces, and you may stop after 1, 2 or 3 steps. You must make at least one
step that changes the position.

- **Rabbits may not step backward** (toward their own side): a Gold rabbit may not
  step toward row 1, a Silver rabbit may not step toward row 8. Rabbits move
  forward or sideways only. (All other pieces move in any of the four directions.)

## Push and pull

A piece may **push** or **pull** an enemy piece that is **strictly weaker** than
itself and orthogonally adjacent. Each push or pull uses **2 steps**.

- **Push:** move the weaker enemy to an adjacent empty square, then move your piece
  into the square the enemy vacated.
- **Pull:** move your piece to an adjacent empty square, then move the adjacent
  weaker enemy into the square your piece just vacated.

You can only push/pull if you have at least 2 steps left in the turn.

## Freezing

A piece is **frozen** if it is orthogonally adjacent to a **stronger enemy** piece
**and** has **no orthogonally-adjacent friendly** piece. A frozen piece cannot move
on its own and cannot be the mover of a push or pull. A frozen piece **can** still
be pushed or pulled by the enemy. A friendly neighbour "unfreezes" a piece.

## Traps

After **every** step, any piece standing on a trap square with no
orthogonally-adjacent friendly piece is removed. A piece can be trapped mid-turn —
for example if the friendly piece supporting it on the trap moves away.

## Winning (checked at the end of a turn)

1. **Goal:** you win if one of your **rabbits** reaches the opponent's home rank
   (a Gold rabbit on row 8 / a Silver rabbit on row 1).
2. **Rabbit elimination:** if a player has no rabbits left, the **other** player
   wins.
3. **Immobilization:** a player with no legal move on their turn loses.

These are checked **at the end of the moving player's turn**. If transient goal
conditions appear and disappear mid-turn they don't count; only the end-of-turn
position matters. If both a goal and a counter-condition hold at turn end, **the
player who just moved wins** (mover wins ties).

## No net-null turn / repetition

You may **not** end your turn with the board exactly as it was at the start of your
turn — every turn must change the position. In addition, a full position (with the
same side to move) may not occur a **third** time. To guarantee termination the
engine also caps the game at 600 turns and declares a **draw** at the cap or on a
3-fold repetition (these are rare; standard Arimaa has no draw but uses a similar
repetition rule and time controls).

## Move encoding

- **Setup placement:** `L@c,r` — drop a reserve piece (E/M/H/D/C/R) on a home cell.
- **Single step:** `c1,r1>c2,r2`.
- **Push:** `push c1,r1>c2,r2>c3,r3` — pusher at c1, weaker enemy at c2 (adjacent),
  empty destination c3 (adjacent to c2). Enemy moves c2→c3, pusher c1→c2.
- **Pull:** `pull c1,r1>c2,r2>c3,r3` — puller at c1, empty destination c2 (adjacent
  to c1), weaker enemy at c3 (adjacent to c1). Puller c1→c2, enemy c3→c1.
- **End turn:** `finish` (action button; legal only after at least one step that
  changed the board).

Move-log notation follows Arimaa's: `Ee2n` = Elephant e2 north, with `push`/`pull`
annotations for two-step moves.

## Interpretations and simplifications

- **Setup** is the full free deployment (each player chooses any arrangement on
  their home rows), implemented as a placement phase.
- **Repetition / draws:** the net-null-turn rule and 3-fold position rule are
  enforced; a hard 600-turn cap and 3-fold both yield a draw so the game always
  terminates. Official Arimaa resolves long games by time control rather than a
  formal draw, so draws here are an engine convenience and essentially never occur
  in real play.
