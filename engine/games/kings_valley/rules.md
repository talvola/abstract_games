# King's Valley

**King's Valley** is a compact abstract by **Kanare Kato** (published by Logy Games /
Kanare_Abstract). Two players race to march their King to the middle of the board.

## Board

- A **5×5** square board (25 cells), addressed `col,row` with `0,0` in a corner.
- The **central square `(2,2)`** is the **King's Valley** — the goal. The renderer
  tints it and marks it as a target.

## Pieces and setup

Each player has **5 pieces: 1 King + 4 Soldiers**, all on their back row:

- **White (player 0)** on **row 0**, **Black (player 1)** on **row 4**.
- The **King sits on the centre file** of the back row (`(2,0)` for White, `(2,4)`
  for Black); the **4 Soldiers** fill the other four back-row squares.

White moves first.

## Movement — the maximal slide

Every piece (King and Soldier alike) moves the **same way**:

- Pick one of the **8 directions** (horizontal, vertical, or diagonal) and slide
  **as far as possible** — the piece continues until it reaches the **board edge**
  or the square **just before another piece**.
- **You may NOT stop short.** Mid-slide stops (chess-style) are illegal. If the
  square next to a piece in a given direction is already blocked, that direction
  gives no move.
- **There are no captures.** Pieces only block one another; nothing is ever
  removed from the board.

A move is written as the path `from>to`, e.g. `1,0>1,3`.

## The King's Valley (centre square)

- **Only a King may stop on the centre `(2,2)`.**
- The centre is otherwise an ordinary empty square: pieces (Kings and Soldiers
  alike) **slide through it** freely.
- Because a Soldier may not stop on the centre **and** may not stop short, a
  Soldier whose maximal slide would *naturally end* on the centre simply has **no
  move in that direction**. (It never "stops just before" the centre.)
- A King ends on the centre only when its maximal slide **naturally terminates**
  there (edge/piece just beyond) — reaching it wins the game immediately.

## How to win

- **Move your King onto the centre `(2,2)` to win** — that instant ends the game.

## How you lose / other endings

- **Trapped King:** on your turn, if your **King has no legal move**, you lose —
  even if your Soldiers could still move. Keeping your King mobile (and trapping
  your opponent's) is the core tension. Passing is illegal; you must move a piece.
- **Opening restriction:** the first player (White) **must move a Soldier on the
  very first move** — the King may not move on ply 0.
- **Defensive draw cap:** pieces are never removed and positions can repeat, so to
  guarantee the game terminates, if neither side has won after **200 plies** the
  game is scored a **draw**. This is a platform safety cap, not a traditional rule.

## Ruleset notes (as implemented)

- Rules verified against
  [logygames.com](https://www.logygames.com/english/kingsvalley.html) (the
  designer's site) and the [Ludii ruleset](https://ludii.games/details.php?keyword=King's+Valley).
  The one point sources leave implicit — whether the centre blocks a Soldier's
  slide — is resolved the Ludii way: the empty centre does **not** block movement
  (pieces slide through it); a Soldier merely can't *stop* on it. This is the only
  interpretive decision and it is documented here.
- The trapped-King loss follows the designer's site: *"If King is fixed on the
  square he can't move at next turn, game is lose."*
