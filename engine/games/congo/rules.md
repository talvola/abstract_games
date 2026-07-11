# Congo

Invented by **Demian Freeling** (1982, aged 7) — son of games designer Christian
Freeling. A 7×7 chess variant blending chess and xiangqi ideas. These are the
rules **as implemented**, from the Wikipedia article and mindsports.nl.

## Board

- 7×7 squares; files **a–g**, ranks **1–7**. White starts on ranks 1–2 and moves
  up the board; Black mirrors on ranks 6–7.
- The **river** is the entire middle row (rank 4).
- Each side has a 3×3 **castle** housing its Lion: files c–e × ranks 1–3
  (White) and files c–e × ranks 5–7 (Black).

**Setup** (White rank 1, Black rank 7, mirrored): a‑file **Giraffe**, b‑file
**Monkey**, c‑file **Elephant**, d‑file **Lion**, e‑file **Elephant**, f‑file
**Crocodile**, g‑file **Zebra**; **seven Pawns** fill each player's second rank.

## Object

**Capture the enemy Lion.** The game ends immediately when a Lion is captured.
There is **no check rule**: you are never forced to answer a threat, and a Lion
may move to an attacked square — the opponent simply captures it and wins.
Consequently there is no draw by stalemate: a player with no legal move loses.

## The pieces

- **Lion** — moves and captures one step in any direction (a chess king), but
  may **not leave its 3×3 castle** — with one exception: if the two Lions face
  each other along a completely **open file or diagonal**, the player to move
  may capture the enemy Lion by moving as a chess queen along that line (like
  xiangqi's flying-general rule).
- **Zebra** — moves and captures exactly as a chess knight.
- **Elephant** — moves and captures one **or two** squares orthogonally; the
  two-square move is a straight-line **jump** (the intervening square may be
  occupied by either side).
- **Giraffe** — moves (but does **not** capture) one step in any direction; and
  moves **or captures** by jumping to the second square in any straight
  direction (orthogonal or diagonal), ignoring the intervening square.
- **Crocodile** — moves and captures one step in any direction. On land it also
  moves and captures as a chess **rook along its file toward the river**, up to
  and including the river square; **inside the river** it moves and captures as
  a rook along the river row.
- **Monkey** — moves (but does not capture) one step in any direction. It
  **captures by jumping** an adjacent enemy man (any of the 8 directions),
  landing on the empty square immediately beyond, and may **chain** jumps:
  - capturing is **never mandatory**, and a chain may stop after any jump;
  - successive jumps may change direction; a given man may be jumped only
    once; a square may be visited more than once;
  - jumped men are removed **only after the whole move**, so they still block
    landing squares during the chain;
  - **jumping the enemy Lion ends the move (and the game) at once**.
- **Pawn** — moves **and captures** one step straight forward or diagonally
  forward (yes, it captures straight ahead too). Once **past the river** it may
  also retreat (move only, never capture) one or two squares straight backward,
  without jumping.
- **Superpawn** — a Pawn reaching the last rank promotes to Superpawn
  (automatic). It keeps the Pawn's moves and additionally moves **and captures**
  one step sideways, and retreats (move only) one or two squares straight
  **or diagonally** backward, without jumping — from anywhere on the board.

## The river — drowning

Except for the Crocodile, **any piece that ends its move in the river must
leave it on its owner's next turn or it drowns** (is removed at the end of that
turn). This applies even if the piece did not move at all (its owner moved
something else), or moved *within* the river. A Monkey may pass through the
river freely during a chain — only its final square counts; if it ends a second
consecutive turn in the river it drowns, but the captures it made stand.
(The Lion can never enter the river; its castle doesn't reach it.)

## Draws

- If **only the two Lions** remain and the player to move cannot immediately
  capture the enemy Lion, the game is a draw (standard adjudication; a Lion
  plus any piece beats a bare Lion).
- **Threefold repetition** of a position (same board, same player to move) is a
  draw, and a hard **600-ply cap** guarantees termination. *(Both are this
  implementation's honest-draw backstops; the sources give no explicit
  repetition rule.)*

## Notation in this implementation

Moves are cell paths `col,row` with `0,0` = a1: `"3,1>3,2"` = d2‑d3. Monkey
chains list every landing square: `"1,2>3,4>5,2"`. Pawn promotion is automatic
(no choice suffix).
