# Daldøs

**Daldøs** (also *Daldøsa*) is a traditional Scandinavian "running-fight" board
game from Denmark and Norway. It survived in living tradition into the 20th
century, so its rules are reasonably well attested (though hole counts and a few
fine points vary by region). This package implements the standard ruleset as
described on Wikipedia and corroborated by the St. Thomas Guild reconstruction
and boardandpieces.com.

## The board

A boat-shaped board of **three parallel rows of holes**:

- an **outer "home" row for each player** (their private starting row), and
- a **shared middle row**, which has **one extra hole at the prow** (the front).

Two documented sizes (choose via the **Board size** option):

- **Norwegian (default):** 12 + 13 + 12 holes — **12 pieces** each.
- **Danish:** 16 + 17 + 16 holes — **16 pieces** each.

At the start, every hole of a player's home row holds one of that player's
pieces, standing **un-dalled** (perpendicular to the row). In this package an
un-dalled piece is marked with a small dot glyph.

## The dice

Movement is by **two four-sided long ("stick") dice**, each marked **1, 2, 3, 4**.
The face **1 is the "dal"** (historically "dallen", marked *A* or *X*). The two
dice are rolled together at the start of a turn and shown in the caption.

This platform models randomness **without a chance node**: the rolled pair is
stored in the game state. The two dice are then played **one at a time** — each
die is a separate move by the *same* player (so "both dice must be used if
possible" falls out naturally). When the dice are spent — or none of the
remaining dice can be legally used — the turn ends and the opponent's fresh pair
is rolled and stored. So the roll is always known when a move is chosen, and the
generic UI needs no chance handling.

## The path

Every piece runs the **same circuit**, and **never returns to its own home row**:

1. up its **home row toward the stern** (the rear),
2. then through the **middle row toward the prow** (entering at the stern end),
3. then into the **enemy's home row**, entered "from behind" at the prow end,
   running **back toward the stern**,
4. then back into the **middle row**, repeating middle → enemy → middle → … for
   ever.

## The "dal" (the signature mechanic)

A piece is **dead in its hole until it is "dalled" (activated)**:

- A piece can only be dalled by **rolling a dal (a 1)**. Dalling turns the piece
  parallel to its row and advances it **one hole**.
- Pieces must be dalled **in order from the stern**: only the **un-dalled piece
  closest to the stern** may be dalled next. (The very first dal of the game
  takes the stern-most piece straight into the middle row; later dals step a
  piece one hole up its home row toward the now-vacated stern.)
- An **un-dalled piece cannot move and cannot capture**. With no dalled pieces
  and no dal showing, the move is simply lost (a *pass*).
- Once a piece has moved it is **dalled for the rest of the game** and thereafter
  advances by any die value.

## Moving and capturing

- A **dalled** piece advances by the value of a die used on it (1, 2, 3 or 4
  holes along the circuit). It may **not** land on one of your own pieces.
- **Capture:** when a dalled, moving piece lands **exactly** on a hole occupied
  by an enemy piece, that enemy piece is **removed permanently** (it never
  re-enters). Pieces may be passed *over* without effect — only an exact landing
  captures. Only **dalled** pieces capture (un-dalled pieces never move, so they
  can never land on anyone).

## Winning

The object is to **remove ALL of the opponent's pieces**. The game ends the
moment one player has no pieces left; that player's opponent wins.

## Termination cap (this implementation)

A capture race can in principle shuffle indefinitely, so this package adds a hard
**6000-ply draw cap**; if it is ever reached, the player with **more pieces** is
declared the winner (ties → player 0). In practice random play ends in a genuine
capture-out far below the cap.

## Move / roll encoding (for the UI)

- A move is the string `"src>dst"` (two cell ids, `col,row`), e.g. `"12,0>12,1"`
  for the first dal, or `"12,1>10,1"` to advance a dalled piece by 2. Click the
  source hole, then the highlighted destination.
- When no remaining die can be used, the only legal move is the action button
  **`pass`** (the turn's unused dice are forfeit).
- `has_randomness` is true; the dice live in the state, so there is no chance
  node.

## Interpretations & ambiguities (documented)

- **Sizes / piece counts** follow the two documented standards; the Norwegian
  12-piece board is the default for a faster game.
- **One-die-at-a-time turn:** the sources say both dice must be used if possible,
  with the option to *add* the two dice onto a single piece. This package plays
  the two dice as two successive single-die moves by the same player (which
  satisfies "use both dice if possible"). It does **not** offer the *added* two
  dice as one combined hop onto a single piece; each die moves a piece on its
  own. This is a faithful-but-simplified reading that keeps every move a single
  clickable `src>dst` step.
- **Dal-dal extra throw:** the historical rule grants a *fresh* extra throw on
  rolling dal-dal. Here, dal-dal simply means both of your dice are dals, so you
  get to make two dal/advance plays this turn; we do not additionally re-roll.
- The exact prow/stern geometry of the circuit is reconstructed to be internally
  consistent with the attested description ("home → stern → middle → enemy row
  from behind → never home again"); the precise hole-by-hole transition at the
  prow is not pinned down identically across sources.

## Sources

- Wikipedia, "Daldøs": <https://en.wikipedia.org/wiki/Dald%C3%B8s>
- St. Thomas Guild, "A medieval 'ship' game":
  <https://thomasguild.blogspot.com/2018/02/a-medieval-ship-game.html>
- Board and Pieces, "Daldøs":
  <https://sites.google.com/site/boardandpieces/list-of-games/dalds>
