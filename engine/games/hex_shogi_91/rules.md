# Hex Shogi 91

**Fergus Duniho, November 2000.** Shogi on the 91-hex hexagonal board — the same
board as Gliński's and McCooey's Hexagonal Chess, but *oriented differently*.
Two players, no chance, no hidden information.

This page describes the rules **as implemented here**. It is the local source of
truth; the "official source" button links to the designer's page at
chessvariants.com.

## The board

91 hexagons in a hexagon of side 6. Every hex **stands on a corner**
(pointy-top), which is what gives the board **horizontal ranks and no vertical
files**. In the designer's words: "Instead of vertical files, there are
left-leaning files and right-leaning files."

* **Ranks** `a`–`k` run horizontally, `a` at the top (6 cells, files 6–11) down
  to `k` at the bottom (6 cells, files 1–6). The middle rank `f` is 11 wide.
* **Files** `1`–`11` are numbered right-to-left (file 1 on the right), exactly as
  in Shogi. A file is the *up-right / down-left* line of hexes, so it is not
  vertical.
* A cell is written file-then-rank: `8b`, `4j`, `6f` (the centre). Internally
  cells are axial `q,r` with `r` = rank (−5 = a … +5 = k) and file = `6 − q − r`.
* The board is three-coloured: orthogonally adjacent hexes never share a colour,
  diagonally adjacent hexes always do — so bishops are colourbound.

**Twelve directions.** Six are **orthogonal** (through a shared edge: left,
right, and the four slanting up/down-left/right) and six are **diagonal**
(through a shared corner: straight up, straight down, and four slanting ones).
On a clock face the orthogonals are the odd hours and the diagonals the even
hours. Each player has **two orthogonally forward** directions (1 and 11
o'clock) and **three diagonally forward** ones (10, 12 and 2 o'clock).

## Setup

**Black (seat 0, bottom, moves first — sente)**

| rank | cells |
|---|---|
| `k` | Lance 6k, Knight 5k, Gold 4k, Gold 3k, Knight 2k, Lance 1k |
| `j` | Rook 6j, Silver 5j, King 4j, Silver 3j, Bishop 2j |
| `h` | nine Pawns, 9h–1h |

**White (seat 1, top)**

| rank | cells |
|---|---|
| `a` | Lance 11a, Knight 10a, Gold 9a, Gold 8a, Knight 7a, Lance 6a |
| `b` | Rook 10b, Silver 9b, King 8b, Silver 7b, Bishop 6b |
| `d` | nine Pawns, 11d–3d |

The two armies are mirror images of each other through the middle rank. The
setup satisfies the designer's stated constraints for the family: each lance
faces the enemy lance down a straight orthogonal ray (6k↔6a and 1k↔11a), and the
two bishops share one diagonal (2j↔6b).

## Pieces

Movement is described for the player moving *forward*; the other player's moves
are the exact negation.

| | piece | move |
|---|---|---|
| `K` | King | one step in any of the 12 directions |
| `G` | Gold General | one step in any of the 6 orthogonal directions, or any of the 3 diagonally forward ones (9 targets) |
| `S` | Silver General | one step in any of the 6 diagonal directions, or either orthogonally forward one (8 targets) |
| `R` | Rook | slides any distance along the 6 orthogonal rays |
| `B` | Bishop | slides any distance along the 6 diagonal rays (colourbound) |
| `L` | Lance | slides any distance along either **orthogonally forward** ray |
| `N` | Knight | **leaps** to 4 forward cells: one step orthogonally forward, then one step diagonally outward (equivalently: two steps in one forward direction, turn 60°, one more). It jumps over anything in between. |
| `P` | Pawn | one step on either orthogonally forward direction; it captures the same way. Because one of the two is along the file and the other crosses to the next file, pawns *can* share a file. |

Promoted pieces (shown `+P`, `+L`, `+N`, `+S`, `+R`, `+B`):

* `+P` (Tokin), `+L`, `+N`, `+S` all move exactly like a **Gold General**.
* `+R` (Dragon King) = Rook **+** one step in any diagonal direction.
* `+B` (Dragon Horse) = Bishop **+** one step in any orthogonal direction.
* Gold and King never promote.

## Promotion

* **The zone is the opponent's first FOUR ranks** — ranks `a`–`d` for Black,
  `h`–`k` for White (30 cells each). It is four ranks rather than Shogi's three
  because the near ranks of this board are narrow.
* A piece that can promote **may** promote on any move that **starts in or ends
  in** the zone. (The designer also says "moves through" the zone; on this board
  that adds nothing — rank changes monotonically along every straight line, so a
  move cannot cross the zone and end outside it.)
* Promotion is **compulsory** when the piece would otherwise have no move at
  all: a Pawn or Lance reaching the last rank, and a Knight reaching either of
  the last two ranks.
* A dropped piece is never promoted by the drop itself; it must move first, on a
  later turn.
* A captured promoted piece **reverts** to its unpromoted type in hand.

## Drops

Captured pieces change side and go into the capturer's hand; on a later turn one
may be dropped, unpromoted, onto an **empty** cell instead of moving. The Shogi
restrictions apply with these differences:

1. A piece may not be dropped where it **would have no move on an empty board** —
   so no Pawn or Lance on the last rank, and no Knight on either of the last two.
2. **There is no nifu rule** (Shogi's one-pawn-per-file): this board has no
   vertical files and pawns can legitimately share a file. In its place:
3. A **Pawn may not be dropped onto a cell defended by another friendly
   *unpromoted* Pawn** (i.e. a cell one of your pawns attacks). A Tokin does not
   count, and an enemy pawn does not count.
4. A **Pawn drop may not give check at all** — stronger than Shogi's rule against
   drop-*mate*. Drops of other pieces may give check and may give checkmate.
5. As always, a drop may not leave your own King in check.

## Ending the game

* **Checkmate wins.** (So does the opponent resigning.) Checkmate ends the game
  **immediately**: a mating move still wins even if one of the draw counters
  below fires on the very same ply.
* **Stalemate is a draw**: if the player to move has no legal move and is not in
  check, the game is drawn.
* **Threefold repetition is a draw**: the same position (board, both hands and
  the side to move) occurring for the third time ends the game.
* **50 turns with no capture is a draw** — implemented as 100 plies (50 moves by
  each player) without a capture. Only captures reset the counter; quiet moves
  and drops do not.
* A hard cap of 50,000 plies is a defensive backstop only, far outside anything
  reachable in play (see interpretation 9 below).

## Interpretations, and where the sources disagree

Four sources by the designer were used — the individual game page, the family
rules page, the Game Courier preset (with the `hexshogi` include file that
carries its actual rule code) and the 2000 Zillions rules file — and they do not
agree everywhere. The resolution of each conflict is recorded here.

1. **Stalemate.** The family rules page (`hexagonal.dir/hexshogi/index.html` —
   the page that "describes the rules in detail", the individual game pages being
   "abbreviated") says plainly: *"Stalemate is a draw. Stalemate can occur if a
   player has no legal move available, the exact same position has been repeated
   three times, or fifty turns have passed without anyone capturing a piece."*
   The **Game Courier preset disagrees** — its post-game code says
   `Stalemate! Black has won.` (i.e. Shogi's own rule, where the stalemated
   player loses). **We follow the rules page**, which is the fuller and more
   deliberate statement, and which the individual Hex Shogi 91 page defers to.
   This is the single most consequential interpretation on this page.
   Two further reasons to distrust the preset here: (a) it implements *no*
   repetition or no-capture rule at all, so its "stalemate" covers only the
   no-legal-move case and cannot be the rules page's three-way definition; and
   (b) the very same `postgame` block still carries **Shogi's** drop rule —
   `if == moved p ... die You may not checkmate a King by dropping a Pawn` —
   which Hex Shogi replaces with the stricter no-*check* rule that the preset's
   own `legaldrop` routine already enforces, making that line unreachable. The
   block is therefore un-updated boilerplate carried over from the author's
   Shogi preset, not a considered Hex Shogi ruling.
2. **"Fifty turns."** Read as the chess convention — 50 moves by *each* player,
   100 plies — because the same sentence calls these "standard stalemating
   conditions for other Chess variants". A stricter reading (50 individual
   turns) is possible.
3. **Checkmate outranks the draw counters.** The rules page lists checkmate as
   the win condition and repetition / 50 turns / no-legal-move as draws, but
   does not say what happens when a mating move *also* completes a counter.
   We score it as a win, because both of the designer's executable sources end
   the game on checkmate unconditionally and implement no counters at all (the
   ZRF's `(loss-condition (White Black) (checkmated King))`, the Game Courier
   preset's `postgame` block), and because it is the standard chess precedence
   (FIDE 5.1.1) that this codebase already applies in `agp/chesslike.py`.
   Stalemate needs no such rule — it draws either way.
4. **Repetition** is *threefold* as written, not Shogi's fourfold sennichite, and
   there is **no perpetual-check rule**: the designer lists repetition as a plain
   draw.
5. **Pawn drop defended "by another Pawn"** — the individual game page is
   ambiguous; the family page settles it: *"defended by another of **your
   unpromoted** Pawns"*, which is also exactly what the ZRF's `no-support` macro
   tests (a friendly `Pawn`, not a `Tokin`, on either backward-orthogonal
   neighbour).
6. **Rank lettering.** The setup diagram on the rules page letters the ranks `a`
   at the top down to `k` at the bottom, with files 11…1 left to right, and puts
   the first player at the bottom — i.e. exactly Shogi's own notation. The Game
   Courier preset **agrees**: its `ranks` list is `k j i h g f e d c b a`, so
   rank *index* 0 carries the label `k` (the first player's back rank) and index
   10 carries `a`; its move code then forces a Pawn or Lance to promote at
   `rank dest 10`, i.e. on the label `a`, and offers optional promotion at
   `rank dest >= 7` (labels `d c b a`). Only the internal index runs the other
   way round — the printed labels, and therefore our cell names, match a Game
   Courier log exactly.
7. **The opening array in the 2000 ZRF is the left–right mirror** of the one in
   the diagram and in the Game Courier preset (its rooks sit where the bishops
   are here and vice versa). A left–right reflection is an exact automorphism of
   this board — it preserves the cell set, both direction sets and each player's
   "forward" — so the two arrays are *the same game seen in a mirror*. We use the
   diagram's, which the Game Courier preset independently confirms.
8. **The Knight leaps.** The prose describes its move as a path, but it is a
   Shogi knight: the ZRF's `jump` macro is a direct leap and its own description
   says "The Knight may jump over intervening pieces."
9. **The ply cap.** Checkmate is the real terminator: over 300 uniform-random
   games with the cap disabled, 299 ended in checkmate and one by the no-capture
   rule (median 305 plies). But drops recycle material, so random play has a
   heavy tail — 95th percentile 2524 plies, **longest observed 10,561** — with an
   empirical survival ratio of about 0.67 per further 500 plies (83, 54, 34, 22,
   15 and 11 of the 300 games ran past 500, 1000, 1500, 2000, 2500 and 3000
   plies). The hard cap is therefore set **far outside that distribution, at
   50,000 plies**, where the same extrapolation puts the chance of a random game
   reaching it at roughly 1e-18: it is a guard against a pathological loop, not a
   participant in the game. The conformance harness is told about the tail
   through the manifest's `max_random_plies` (15,000 — above every game ever
   measured) rather than by shrinking the cap to fit the test, because a cap
   small enough to truncate random games is a cap that decides outcomes.
   A second, independent measurement of **5,124** uniform-random games
   reproduces this: median 313, mean 631, p95 2,505, longest 8,552; 5,102 ended
   in checkmate, 22 by the no-capture rule and none in stalemate; and the
   per-500-ply survival ratio is flat at 0.63–0.72 all the way from 1,500 to
   8,500 plies (maximum-likelihood exponential tail above 2,000 plies: 0.691
   per 500 — slightly heavier than the 0.67 the smaller first sample gave, which
   does not change any conclusion below). A geometric tail is also the *right*
   model rather than a
   convenience — uniform-random play is an absorbing finite Markov chain, whose
   survival function is a finite mixture of geometrics and therefore
   asymptotically geometric — and the flatness over a fifteen-fold range of `t`
   says the asymptotic regime is reached well before 1,500 plies. That puts
   P(length > 15,000) ≈ 5e-6 (≈ 2e-4 per 40-game `validate` run, i.e. the
   harness budget is not a flake source) and P(length > 50,000) ≈ 3e-17.
   Ordering the two limits this way round is deliberate: because
   `max_random_plies` < `PLY_CAP`, a future termination regression makes
   conformance **fail loudly** ("game did not terminate within 15000 moves")
   instead of being silently absorbed into a "move limit" draw — and it stops
   ~11x sooner, which matters because the harness serialises the state four
   times per ply against an O(ply) `reps` dict, so a runaway costs quadratic
   time.
   `selftest.py` re-plays fixed-seed games with the cap disabled and asserts the
   same length, result and reason, and that each finishes an order of magnitude
   short of the cap. In fairness: for a drop game, where material is recycled
   rather than consumed, **no finite cap is *provably* outcome-neutral** under
   uniform-random play — the honest claim is that this one now sits far outside
   the observed distribution instead of inside it, and that real play (a few
   hundred plies, with repetition and the no-capture rule biting first) never
   approaches it.

## Notation

The move log uses the printed labels: `S5j-5i`, `R6jx6d+` (capture with
promotion), `P*7f` (a drop). Internally a move is `"q,r>q,r"` with an optional
`=+` promotion suffix, or `"L@q,r"` for a drop.

## Verification

* Move generation was compared, position by position, against an oracle built by
  parsing the designer's own 2000 Zillions rules file (`hexshogi91.zrf`) — its
  direction table, promotion-zone cell lists and piece move macros — over **637
  positions and 65,602 legal moves, with zero mismatches** (positions drawn both
  from random playouts, so hands are non-empty, and from synthetic random
  boards).
* A **second, independent** move generator was then written from the *Game
  Courier* include file (`play/pbm/includes/hexshogi.txt` — a different primary
  source, with its own `checkaleap`/`checkride`/`legaldrop` definitions) and its
  own setup, `apply_move` and brute-force attack detection. It agrees over
  **15,244 positions and 1,349,642 legal moves, with zero mismatches**, and
  reproduces perft 45 / 2,024 / 92,922 from its own setup array.
* Frozen perft from the opening position: **45 / 2,024 / 92,922** at depths 1–3
  (4,257,310 at depth 4).
* The opening array was re-derived pixel-by-pixel from the setup diagram
  (`hex_shogi_91.png`), each glyph matched against the `motifshogi` piece GIFs
  the rules page itself uses, and independently decoded from the Game Courier
  preset's `code` field; all three agree. The array satisfies the designer's
  stated family constraints (facing lances, bishops on one diagonal) and his
  "no piece can capture on its first move" requirement — there are 45 legal
  moves and 0 captures for either side at move 1.
* Both statements of the "no move on an empty board" drop rule — the static
  rank test used here and the dynamic on-board test the ZRF and the Game
  Courier include actually write — were checked to agree on all 91 cells × 7
  droppable types × 2 colours.
* `selftest.py` additionally pins the opening array, every piece's target set
  from the central hex, the 30-cell promotion zones, optional and compulsory
  promotion, both pawn-drop restrictions, the dead-piece drop rule, capture
  demotion, checkmate, checkmate's precedence over every draw counter,
  stalemate, and both draw rules.

## Sources

* Fergus Duniho, *Hex Shogi 91* — https://www.chessvariants.com/hexagonal.dir/hexshogi/hexshogi91.html
* Fergus Duniho, *Hex Shogi* (the family rules, in detail) — https://www.chessvariants.com/hexagonal.dir/hexshogi/index.html
* The Game Courier preset `hexshogi91` (board, start array and the `postauto` /
  `postgame` GAME code), plus the rule file it `include`s —
  https://www.chessvariants.com/play/pbm/includes/hexshogi.txt — which carries
  the piece functions and the `legaldrop` subroutine and independently confirms
  every direction set, the four-rank zone, the forced promotions and all three
  pawn-drop restrictions. (One caveat if you read it: its Dragon King `def d`
  uses `checkleap #0 #1 1 2`, whose eightfold symmetry admits four offsets that
  are not hex diagonals at all — a slip in the include, not a rule; the prose
  and the ZRF both say "Rook plus one diagonal step", which is what we
  implement.)
* `hexshogi.zip` — the designer's Zillions of Games rules files (2000), used as the differential oracle.
