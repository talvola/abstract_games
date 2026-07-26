# Xiang Hex

**L. Lynn Smith, 2008.** Chinese Chess (Xiangqi) transplanted onto an elongated
hexagonal board — the first hex xiangqi. Two players, no hidden information, no
randomness. Red (seat 0, bottom) moves first; Blue (seat 1) sits at the top.

This page describes the rules **as implemented here**. The primary sources are
the [chessvariants.com rules page](https://www.chessvariants.com/rules/xiang-hex)
(prose plus Fergus Duniho's eight movement diagrams) and the rule-enforcing GAME
code of Duniho's Game Courier preset. Where they differ, this file says so.

## The board

Nine **vertical files** `a`–`i`. The two outer files are 7 cells long, the
centre file 11; the lengths run **7, 8, 9, 10, 11, 10, 9, 8, 7 = 79 cells**, an
elongated hexagon with sides of 7, 5, 5, 7, 5, 5.

Every file is numbered from Red's end upwards, starting at 1: `a1`–`a7`,
`b1`–`b8`, … `e1`–`e11`, … `i1`–`i7`. (The Game Courier preset instead numbers
by a *global* rank 1–11, so its `a5` is this page's `a1`. All notation here, and
in the move log, is the per-file numbering the rules page and its diagrams use.)

Each cell has six **orthogonal** neighbours (through its edges) and six
**diagonal** neighbours (through its vertices, two cells away).

### The river

The **river** is the board's horizontal mid-line. Five cells sit astride it:
the 4th cell of the outer files, the 5th of the `c` and `g` files and the 6th of
the centre file — **`a4`, `c5`, `e6`, `g5`, `i4`**. A player's own side of the
board is everything *before* the river.

### The palace

Each palace is seven cells: the first three cells of the centre file and the
first two of each flanking file — Red's is **`d1 d2 e1 e2 e3 f1 f2`**, a
one-cell-radius hexagon centred on `e2`; Blue's is the exact 180° rotation,
**`d9 d10 e9 e10 e11 f9 f10`**, centred on `e10`.

## The pieces

Each player has 16: 1 General, 2 Mandarins, 2 Elephants, 2 Horses, 2 Chariots,
2 Cannons, 5 Soldiers. Any piece captures by displacement, moving onto an
enemy piece's cell.

| | Piece | Move |
|---|---|---|
| **S** | Soldier | One step straight forward while on its own side of the river. **On and beyond the river**, also the two other forward orthogonals *and* the two sideways diagonals — five destinations. Never retreats, never promotes. |
| **H** | Horse | One orthogonal step to a **vacant** cell, then one diagonal step continuing in the same direction: 12 destinations, each lamed by a piece on its first step. |
| **C** | Chariot | Slides any distance along the six orthogonals. |
| **A** | Cannon | Slides like the Chariot when **not** capturing; captures by leaping **exactly one** piece (of either colour) along one of those six lines and taking the first piece beyond it. |
| **E** | Elephant | Two diagonal steps in the same direction (six destinations). The intermediate cell must be **vacant**, and the Elephant **may never cross the river**. |
| **M** | Mandarin | One diagonal step, never leaving the palace. |
| **G** | General | One orthogonal step, never leaving the palace, and never on an otherwise-empty file with the enemy General. |

### Consequences worth knowing

* A hex diagonal is **two cells long**, so a Mandarin's step jumps the palace's
  own ring. The palace's seven cells therefore split into **two disjoint
  Mandarin triangles** — `{d1, f1, e3}` and `{e1, f2, d2}` — plus the centre
  `e2`, from which a Mandarin has **no move at all**. Both of a player's
  Mandarins start in the same triangle (`d1`, `f1`) and can never leave it.
  The board draws both triangles inside each palace, as the source's diagrams do.
* An Elephant is confined to just **five** cells — Red's to `{c1, g1, a3, e5,
  i3}`, Blue's to `{c9, g9, a5, e7, i5}` — because its move changes its
  distance from the river by 0 or by three cells' worth, and the river bound
  then closes off the far band. It can never stand on a river cell, so the
  bound is never actually tight. (This is exactly the diagram on the rules
  page: an Elephant on `e5` reaches `a3`, `c1`, `g1`, `i3` and nothing else.)
* The two Chariots have **no legal move at all** in the opening array: an outer
  file's first cell has only three neighbours on the board and all three are
  occupied.
* The **flying-general** line is the file and only the file. (Red's palace cells
  all have hex coordinates with `r ∈ {3,4,5}` and `q+r ∈ {3,4,5}`, Blue's the
  negatives, so no other straight line can ever join the two palaces — asserted
  in `selftest.py`.) The preset writes the test as `checkride #0 #1 1 0`, whose
  symmetric expansion is **four** of the six hex lines — the file *and* the
  NE/SW line — but the NE/SW line is one of those that can never join the
  palaces, so file-only is exactly equivalent. Facing is scored as **mutual
  check**: it makes the two Generals attack each other, so the player who would
  create it — by moving a General onto the line, or by unblocking one — is
  simply leaving himself in check, and the move is illegal for him. (Move
  generation also emits the General-takes-General capture the preset's `def g`
  admits, for exactness against that oracle; it is unreachable in play, since a
  facing position could only arise from a move that was already illegal.)

## Ending the game

* **Checkmate wins.**
* **Stalemate loses.** Combining the two: *a player with no legal move loses.*
* **Repeating a position loses.** The player whose move recreates a position
  (piece placement + side to move) that has already occurred in this game loses
  immediately. There is no draw by repetition and no perpetual check.
* If **neither** side has a piece left that can cross the river — that is, if no
  Soldier, Horse, Chariot or Cannon remains anywhere on the board — the game is
  a **draw** (an honest draw: `winner = None`, returns `[0, 0]`). Generals,
  Mandarins and Elephants are the three pieces that can never cross.

Order of precedence, when a single move could trigger more than one: having no
legal move (checkmate or stalemate) is decisive and is judged first, then
repetition, then the no-crossers draw. In fact the orderings never collide — a
position that ends the game cannot recur, because the game ended the first time
it arose.

**Termination is guaranteed by the repetition rule alone**: no position can
occur twice, so no game can be infinite. A `PLY_CAP` of 20,000 plies (scored as
a draw) is kept purely as a hang guard; it is *not* outcome-load-bearing — see
the numbers below.

## Interpretations and source notes

1. **"A player loses if stalemate or repetition of position"** (rules page) is
   read as: *the first* recurrence of a position ends the game at once, and the
   player who created it loses. Position identity is piece placement **plus the
   side to move**. The Game Courier preset enforces checkmate and stalemate but
   not repetition, so the prose is the only source; this is the plain reading
   and the only one that keeps the rule meaningful (any weaker threshold would
   need a count the source never gives).
2. **"If both players have no pieces which can cross the river, the game is
   drawn"** is read by piece **type**: the draw fires when no Soldier, Horse,
   Chariot or Cannon is left on the board at all. A Soldier that has *already*
   crossed still counts as a river-crosser — reading it positionally would
   declare a draw in positions that a lone advanced Soldier can still win.
3. **The Soldier's river gate is on the DESTINATION, not the origin.** The
   preset tests `rank #1` / `file #1` — the square moved *to* — so a Soldier
   standing one cell short of the river may use a *forward-diagonal* step to
   enter it (e.g. Red's Soldier on `f5` may go to `e6` or `g5`, both river
   cells), even though from `f5` it could not yet step sideways. The prose
   ("**upon** and after entering the river") reads naturally as the act of
   entering, and the enforcing code is unambiguous; the alternative
   origin-based reading would differ **only** for those two forward-diagonal
   steps, since the two sideways steps never change the distance from the river
   at all.
4. **The Elephant's river bound** is implemented exactly as the preset writes
   it: the destination must be on the Elephant's own side *or* on the river
   line itself. Whether the river cells count as "not crossed" is unobservable —
   writing `D = q + 2r` for the distance from the river (`D = 0` on it), an
   Elephant move changes `D` by 0 or ±6 and Red's Elephants start at `D = 8`,
   so an Elephant is always on `D ∈ {2, 8}` and can never stand on the river.
5. **The Mandarin and General are confined to their *own* palace.** The preset
   flags all fourteen palace cells with one undifferentiated flag, so it would
   also accept a step into the *enemy* palace — unreachable in both cases (the
   palaces are six cells apart and both pieces move one step), so the two
   readings coincide.
6. **Flying general — a copy-paste bug in the preset.** *Both* of its General
   clauses read `checkride #0 #1 1 0 and == #G #1`, and `#G` is the variable
   holding **Red's** General's square. So `def g` is right (Blue's General may
   fly to Red's General) while `def G` is wrong (Red's General may fly only to
   *its own* square — i.e. never). The effect is not "no flying general" but an
   asymmetric one, and in the direction opposite to what the shape of the typo
   suggests: **Red may not face, Blue may.** Blue's General attacks Red's down
   the file, so `sub checked #G` is true in a facing position and Red's move is
   rejected by `postauto1`; `sub checked #g` stays false, so Blue is free to
   create the facing.

   Three independent facts show this is a typo and not a rule:

   * the `xiangqi` include the preset itself pulls in (`include xiangqi;`,
     `chessvariants.com/play/pbm/includes/xiangqi.txt`) carries the symmetric
     original — `def G … == space #1 g` and `def g … == space #1 G`, each
     testing the *contents* of the destination for the **other** General;
   * the preset's own move-candidate helper stayed symmetric:
     `def GL merge leaps #0 1 0 array … cond == #0 var g var G var g`, i.e.
     "whichever General square is not mine";
   * the prose ("Not permitted be on an empty file with the opposing GENERAL")
     and the General diagram — which bars *Red's* General from the `d` file —
     are symmetric.

   So **the rule is implemented symmetrically here**, and a facing position is
   check for both sides at once (which is what makes creating one illegal for
   whoever would create it). A differential run measures the divergence from the
   preset's literal text at 587 of 7,353 positions (8%).
7. **Erratum in the rules page's General example.** "It cannot move to f2,
   because it cannot move diagonally" — but in that same diagram `f2` is one of
   the two marked legal moves, and `f2` is orthogonally adjacent to the General
   on `e3`. The intended cell is **`f1`**, which *is* a diagonal step from `e3`
   and is left unmarked. (The other two sentences of that example — the `d`-file
   ban from the enemy General on `d10`, and `e1` being out of reach — match the
   diagram exactly.) The Horse example's "d3 or f3" is correct as printed.
8. **The move log** writes moves as piece letter + from + `-`/`x` + to, with
   `+` for check: `Ce6xe9+`, `Se4-e5`, `Ge3-e2`.

## Verification

* **Differential against the Game Courier GAME code.** `_diff_gamecourier.py`,
  shipped beside this file (manual/one-time — `PYTHONPATH=. python3
  games/xiang_hex/_diff_gamecourier.py [games] [positions] [--literal-G]`), is
  an independent reimplementation of Duniho's preset: his `def` clauses
  transcribed verbatim and evaluated with Game Courier's own `checkaleap` /
  `checkaride` / `checkahop` / `checkatwostep` primitives in his (file, rank)
  coordinates. Its header pins the three GAME-language properties the
  transcription rests on (`a`-prefix = exact delta, no `and`/`or` precedence,
  0-based `rank`/`file`) against the `xiangqi` include the preset itself pulls
  in, where the geometry is already known. Legal-move sets agree exactly,
  position for position: **0 mismatches in 10,675 positions** (40 full random
  games played out ply by ply, plus 600 scattered random positions scored from
  both sides). Run with `--literal-G` it also measures the flying-general bug of
  note 6: the preset's literal `def G` gives a different move list in **804 of
  those 10,675** positions, so the bug is not academic.
* **The preset's own board string** (`$default['code']`) is parsed in
  `selftest.py` and must reproduce both the 79-cell shape and the entire opening
  array — a second primary source for the setup, independent of the diagram.
* **All eight movement diagrams** on the rules page (the seven pieces, the
  Soldier twice) are reproduced
  cell-for-cell, including the two Horse moves the diagram's Cannon lames, the
  two Elephant moves the river forbids, the Cannon's blocked slide *and* its
  screen capture, and both of the Soldier's two states.
* **Check detection** (`_attacked`, a separate path from move generation) is
  tested for the Horse's lame leg and for the Soldier's river gate, so a
  restriction cannot go missing there and manufacture a phantom checkmate.
* **Ending precedence** is tested on constructed collisions — a real checkmate
  and a real stalemate re-scored with the repetition counter and the ply cap
  both tripped — plus the one collision that *is* reachable, where the capture
  removing the last river-crosser also stalemates the loser. All must stay
  decisive.
* **The flat-top orientation is derived, not asserted**: under the renderer's
  flat-top map a file is vertical and the river's five cells fall on one
  horizontal line, exactly as the rules page draws them; pointy-top does
  neither.
* **Frozen perft** from the opening array: 30 / 874 / 28,968.
* All of the above except the differential run in `selftest.py`, which is pure
  standard library.

**The history-clearing shortcut is safe.** `apply_move` drops the repetition
history on a capture or on a Soldier move that changes `D = q + 2r`, on the
argument that both are irreversible: a capture removes material for good, a Red
Soldier's `D` never increases (its five steps change `D` by −2, −1, −1, 0, 0)
and a Blue Soldier's never decreases, so two equal positions can have no such
move between them. Re-running 6,000 random games against an implementation that
keeps **every** position from ply 0 and never clears gives the same verdict at
every one of the ~1.57 million plies: **0 disagreements**.

**Random-play statistics** (6,000 games, uniform random moves): shortest 4
plies, median 261, 99th percentile 643, longest 1572. Endings split
checkmate 2199 / repetition 2884 / no-river-crossers 606 / stalemate 311, and
results split 2671 Red / 2723 Blue / 606 draws — so all four endings, including
both unusual losses and the honest draw, are comfortably reachable. (An earlier
8,000-game run agreed to within 0.5 percentage point on every share and found
the same 1572-ply maximum.)

**The ply cap is not outcome-load-bearing.** The longest of those 6,000 games is
a factor of **12.7** below the 20,000-ply cap, and the cap fired 0 times even
when set to 4,000. The tail is heavy enough (the longest game is 2.4× the 99th
percentile) that the manifest raises `max_random_plies` to 6,000 rather than
leave conformance's 3,000-ply default less than a factor of two above the
observed maximum — that limit only decides whether the harness calls the game
non-terminating, never a result.
