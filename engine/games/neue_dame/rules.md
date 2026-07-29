# Neue Dame ("New Draughts")

*Heinrich Adolf Schmidt, Hildesheim (Germany), 1904* — published by his
*Gesellschaft für den Vertrieb moderner Spiele*, presented at the Leipzig trade
fair in Mädlers Kaufhaus in 1904, and protected as a *Gebrauchsmuster* (utility
model) at the Imperial Patent Office in Berlin on 4 April 1908. An advertisement
of the day called it "the most interesting game of present times". It never
caught on: the English rules of the 1900s are lost, the set is a collector's
rarity, and the game had no BoardGameGeek entry of its own when it was
rediscovered.

Neue Dame is one of the **oldest stacking games in existence** — only Bashni
(1875), the Towers of Hanoi (1883) and the Diplomaten-Spiel (1895) are older, and
Lasker's Lasca is seven years *younger*.

These are the rules **as implemented here**. The source is Ralf Gering's article
**"Neue Dame: A forgotten stacking game"**, *Abstract Games* **18** (Winter/Spring
2020), **pp. 30–31**, which reconstructs the rules from the German original, plus
the **four composed problems** printed there with their full solutions on p. 1 of
the same issue. Every interpretation below is flagged and justified, and the
problems are replayed move-for-move in `selftest.py`.

## Board, pieces, setup

Play is on the **32 dark squares of an 8×8 board**, placed so that the bottom
right square is white (a1 is dark, h1 is light — the chess orientation). Each
player has **12 checkers**, on the dark squares of the **three rows nearest
them**: **Green** at the bottom (rows 1–3) playing *up*, **Black** at the top
(rows 6–8) playing *down*.

Historically the pieces were two-sided like Reversi discs — green/red and
black/white — with the dark side (green, black) face up. Turning a piece over to
its light side is how a promotion is shown. This package uses the seat colours
plus the letter **D** on the top band of a column.

A **column** ("Turm", tower) is a stack of one or more pieces. **A column belongs
to whoever owns the piece on top**, it **moves and captures exactly like that top
piece**, it always moves **as one unit**, and it may **never be split**.

> **Who moves first.** The German rules did not say, "so it must be assumed that
> it did not matter" (Gering). This implementation lets **Green** (the bottom
> player, seat 0) move first — the convention of every diagram in the article,
> where Green is the player to move in three of the four problems.

## Moving

- A **man** ("Stein") moves **one square diagonally forward** to an empty square.
- A **Dame** ("Dame", Lady) moves **any number of unobstructed squares
  diagonally, forwards or backwards** — a flying king, as in International
  draughts.

## Capturing — the tower rule

**Capturing is mandatory.** You capture by jumping an enemy-owned column and
landing on an empty square beyond it:

- a **man** jumps an **adjacent** enemy column **forwards only**, landing one
  square beyond it (the short leap of Anglo-American draughts);
- a **Dame** flies: she slides over empty squares to the first column in that
  direction and, if it is enemy-owned, jumps it.

Then comes the mechanic the game is named for:

> **The captured piece is not removed.** Only the *top* piece of the jumped
> column is taken, and it is placed *under* the capturing column — at the very
> bottom — so the capturing column grows by exactly one piece per jump.

The **rest of the jumped column stays where it is**, now owned by whoever its new
top piece is. Taking an enemy top therefore **liberates** whatever was buried
under it, and a single capture can hand a nine-piece tower to the other player.

### The four capture restrictions

These, not the stacking, are what make Neue Dame its own game:

1. **Captures must be continued as long as possible** — a multi-jump is one move.
2. **A capture by a Dame takes precedence over a capture by a man.** If any
   column you own that is topped by a Dame can capture, then *only* Dame captures
   are legal that turn.
3. **If a Dame can capture in more than one way, the nearest piece must be
   captured first.** Among all the pieces she could take, only the closest one(s)
   may be jumped — measured in squares along the diagonal, and re-applied at
   *every* step of a multi-capture.
4. **A Dame must stop on the square immediately behind the last piece taken.**
   The landing squares *inside* a chain are free (she may fly on past a jumped
   piece in order to reach the next one), but the square she finishes on must be
   the one directly behind the final piece she took.

Restriction 4 makes the Dame a *landing-restricted* flying king that exists in no
other draughts game we ship, and together 2–4 make most Dame captures completely
forced.

## Promotion

A man that **ends its move on the far row** (row 8 for Green, row 1 for Black) is
turned over and becomes a **Dame**. Only the **top** piece of a column promotes,
and a column whose top man reaches the last row promotes just like a lone man.
A **man that reaches the far row while capturing is crowned there and the move
ends** — it does not carry on jumping as a Dame.

Promotion is permanent: a Dame that is captured and buried is still a Dame, and
still counts for the score.

## Ending the game and scoring

The game ends when **one player owns every column on the board**, or when the
player to move **has no legal move** (a *blockade* — Puzzle 3 ends exactly this
way). That player loses.

The winner scores **one point for every Dame on the board** — of either colour,
including Dames buried inside towers. If **no piece was ever promoted**, the
winner scores **½ point** (a house rule added by Gering, not in the original).
**A draw scores 0–0 for both players.** The point total is shown in the caption
and by `score(state)`; the engine's own `returns` are the usual ±1 / 0-0, so the
bot and the ladder treat a win as a win.

The original rules did not mention resigning ("obviously players were supposed to
play to the bitter end"); the platform's resign button is of course still there.

### Draws / termination

Neue Dame recycles material — nothing ever leaves the board — so play could in
principle cycle. Three rules bound it, in this order of priority:

- a **decisive result always outranks them**: if the player to move has no legal
  move, that is a loss, even on the ply a draw counter trips;
- **threefold repetition** of the exact position (every tower, bottom to top,
  plus the side to move) is a draw;
- **100 plies** with no capture and no promotion is a draw ("no progress");
- a hard cap of **1200 plies** is a backstop that measurement never reaches.

Measured over **2,500 random games**: exactly **one** draw (0.04%, by threefold
repetition); the no-progress rule and the ply cap never fired at all, and the
longest game was 305 plies (average 78). An independent **3,000-game** QA run
found **zero** draws, a longest game of **380** plies and a peak no-progress
count of **36** of the 100 allowed. So no cap is outcome-load-bearing in
practice — they exist only so that termination is guaranteed.

## Is this just Bashni / Lasca / Emergo?

We already ship three column-draughts games, so the question deserves an answer.
Neue Dame shares only the *prisoner-under* mechanic with them; everything that
decides a game is different.

| | **Neue Dame** | Bashni | Lasca | Emergo |
|---|---|---|---|---|
| Board | 8×8, 32 dark, 12 men | 8×8, 32 dark, 12 men | 7×7, 25 dark, 11 men | 9×9, 41 dark, 12 in hand |
| Man captures | **forward only** | forward *and* backward | forward only | any direction |
| Promoted piece | **flying Dame** | flying king | one-step officer | **none — no promotion** |
| Crowning in a chain | **stops the move** | promotes and jumps on | stops the move | — |
| King capture priority | **Dame outranks man** | none | none | none |
| Which piece may be taken | **the nearest one first** | any | any | any |
| Where the king lands | **immediately behind the last piece taken** | any square beyond | one beyond | one beyond |
| Maximum capture | no | no | no | **yes (majority)** |
| Object | **own every column; score = Dames on the board** | opponent cannot move | opponent cannot move | opponent cannot move |

The distinguishing block is restrictions **2–4** plus the **Dame-count scoring**.
They are not cosmetic: because a Dame must take the *nearest* piece and must stop
*directly behind* it, a Neue Dame flying king has (usually) exactly **one** legal
capture, so sacrificing into her is a precise, calculable tempo weapon — the
motif every one of the four composed problems is built on. Puzzle 4 is a
ten-ply forced shuttle (b6↔d4) that exists only because of restriction 4, and
Puzzle 2's key line is annotated "(forced) … (also forced)" only because of
restriction 3. None of those lines is playable under Bashni's or Lasca's king.
Conversely, the *scoring* changes the endgame: you do not merely want to win, you
want Dames on the board when you do.

## Interpretations (rules the article leaves open)

Each of these was settled by the four composed problems, which are replayed
exactly in `selftest.py`; the evidence is named.

1. **A square already jumped in this move may not be jumped again.** The article
   does not say. *Evidence:* Puzzle 4, 1…g1xb6 — the Black Dame takes the top of
   the c5 tower and lands on b6, from where c5 (still four men tall) is adjacent
   again. Without this rule "captures must be continued as long as possible"
   would force her to eat the whole tower in one move, and the printed solution
   (one capture per turn, ten plies long) would be impossible.
2. **Only the final landing square of a chain is constrained**, not the
   intermediate ones. *Evidence:* Puzzle 4, 6.a7xd4xb2 (the Dame jumps b6 and
   flies on to d4, two squares past it, before taking c3 and stopping directly
   behind it) and Puzzle 2, 7…a7xd4xf6. Both are illegal if every landing must be
   the adjacent one; both are the printed moves.
3. **"Nearest piece first" is re-applied at every step of a chain**, not only at
   the start. *Evidence:* Puzzle 2, 1…b8xe5**xg3** is annotated "(also forced)",
   which is true only if, from e5, the Dame must take f4 (distance 1) rather than
   the Green Dame on c3 (distance 2).
4. **Crowning ends the move** (Anglo-American, not Russian). *Evidence:*
   Puzzle 1, 3.d4xf6xd8*D — from d8 the newly crowned Dame could take c7 and land
   on b6; the printed solution stops.
5. **There is no maximum-capture ("majority") rule.** The article lists the
   capture restrictions exhaustively and this is not among them, and the men are
   explicitly Anglo-American (which has no such rule). *No printed move
   discriminates* — this was checked, not assumed: replaying all four problems
   under an added majority rule breaks nothing, because every capture the
   composer plays happens to be a longest one.
5b. **A Dame may stop on the square immediately behind the piece she just took
   even when flying further would have let her take another.** "Captures must be
   continued as long as possible" is applied *from the square she lands on*, not
   as an obligation to pick the landing that prolongs the chain. This is also
   **undiscriminated** by the printed corpus (replaying all four problems under
   the stricter "you may not choose a landing that escapes a further capture"
   reading breaks nothing either) — the two readings differ only in positions the
   composer never reached. The permissive reading is the one that follows the
   article's wording most literally.
6. **Dame precedence is evaluated per turn, over the moving player's own
   columns** — if you have a Dame capture available you must make *a* Dame
   capture (not necessarily with that particular Dame).
7. **A man may capture a column topped by a Dame.** (Italian draughts forbids it,
   and the article says some rules resemble Italian draughts.) *Evidence:*
   Puzzle 1, 3.d4xf6 and Puzzle 3, 3.h2xf4 both have a man jump a Dame-topped
   column.
8. **Score counts buried Dames.** *Evidence:* all four problems. Puzzle 4's
   "6 points for Green" is exactly the four Black Dames of the diagram plus
   Green's two promotions — every one of them buried inside a tower by the end.

## The problems as anchors (and their hidden pieces)

Puzzles 1 and 4 print all 24 pieces, so their positions are fully determined.
Puzzles 2 and 3 show only 9 and 11 pieces; the article says the rest "are stacked
beneath other pieces in such a way that they do not alter the solution", without
saying where. `selftest.py` therefore replays those two from an explicit
**witness** arrangement (Puzzle 2: all 15 under Green's Dame on e5, the one column
whose top is never captured; Puzzle 3: one under b8 and the rest under Green's man
on h2). The choice is **not** free, and it is not nearly free either: of **400
random** legal fillings only **1** (Puzzle 2) and **0** (Puzzle 3) replay the
whole printed line — burying a piece under a column whose top *does* get captured
leaves that square occupied afterwards and changes every diagonal through it.
That is exactly what the article means by "stacked … in such a way that they do
not alter the solution", but it does mean the hidden-piece problems are a
**weaker** anchor than Puzzles 1 and 4 (which show all 24 pieces): a witness is
*chosen* to make the line work. The interpretations that matter are therefore
anchored on the fully-determined problems wherever possible — no-re-jump and
free intermediate landings on Puzzle 4, crowning-ends-move and man-takes-Dame on
Puzzle 1, buried-Dame scoring on Puzzles 1 and 4 — and any re-derivation should
say which witness it used.

## Errata found in the printed solutions

The article's solutions were replayed against this implementation. **Puzzles 1, 2
and 3 replay exactly, move for move, including every "(forced)" annotation and
the final point counts.** The remaining problems are:

- **Puzzle 4, White's 4th move** (printed `4.dg7-f8*D` — the stray *d* is in the
  magazine) is **illegal**: after 3…d4xb6 the Black Dame stands on b6, a7 is
  empty and Green's two-man column on c5 can jump it, so by the mandatory-capture
  rule Green's **only** legal move is **c5xa7**. This is not a move-order
  accident: all six orderings of Green's four quiet moves (`a7-b8*D`, `b8-a7`,
  `h6-g7`, `g7-f8*D`) that respect their dependencies fail as well — putting the
  tower on g7 while the Dame stands on b6 lets her continue b6xd4x**h8**, and
  keeping the Dame off a7 lets c5 capture. Everything else in Puzzle 4 —
  **39 of the 40 plies**, all eighteen "(forced)" replies, the alternatives
  offered at moves 18 and 20, the side variation (a), and the final "6 points for
  Green" — checks out exactly.

  An illegal printed move is only an *erratum* if the ruleset is right, so the
  three rule readings that *would* legalise it were each tried, and each is
  refuted by a printed move somewhere else (this is asserted in `selftest.py`):

1. *Italian: a man may not capture a Dame-topped column.* **Refuted by** Puzzle 1,
   `3.d4xf6xd8*D` and Puzzle 3, `3.h2xf4xh6xf8*D` — both are a man jumping a
   Dame-topped column, and under this reading Puzzle 3 has no legal move at all
   at that point.
2. *"A capture by a Lady takes precedence" read as: if you own a Lady, only a
   Lady may capture.* **Refuted by** Puzzle 2 variation (f), 6.g3xe5 — a man's
   capture played while Green owns a Dame that cannot capture — and by Puzzle 3,
   `1…c3xe1*D`.
3. *A column may not jump a column taller than itself.* **Refuted by** Puzzle 1,
   `3.d4xf6xd8*D`; Puzzle 2 variation (f), 5…h2xf4; Puzzle 3, 6…a1xf6.

So the printed 4th move is illegal under *every* ruleset consistent with the
other three problems, and the slip is in the composition, not in the rules.

The remaining errata are notation slips:
- **Puzzle 2, variation (a)**, "3.b4-c5 g1-b6": the move is right but it is a
  *capture* (of the man just played to c5), so it should read **g1xb6**.
- **Puzzle 2, variation (g)**, "7…h2xd6x**c4**": c4 is a **light** square and is
  not part of the board at all. The move is **h2xd6xb4**, after which the printed
  8.e1xa5 follows.
- **Puzzle 2, variation (i)**, "7…h2x**d4**xc7": d4 is not on either diagonal
  through h2. The legal readings are h2xe5xc7 and h2xf4xc7 — both end on the
  printed square c7 and both let the printed 8.a5xd8 follow.
- **Puzzle 4, variation (a)** ends "5 points for Green" where the position holds
  the same **6** Dames as the main line.

None of these affects the *rules*; they are notation/analysis slips in a
21-move-deep composition.

## Notation

The article's chess notation is used in the move log: `a1-b2` for a quiet move,
`c3xa1` for a capture (a multi-capture lists the landing squares, `c3xe1xh4xd8`),
and a trailing `*D` when the move promotes. Internally a move is the
`>`-separated path of cells, `"0,0>1,1"`.

## Sources

- Ralf Gering, "Neue Dame: A forgotten stacking game", *Abstract Games* **18**
  (Winter and Spring 2020), pp. 30–31; solutions on p. 1. — the primary source
  for every rule above.
- Ralf Gering, *12 Neue Dame Puzzles* (self-published e-book, June 2019).
- Ulrich Schädler (ed.), *Spiele der Menschheit: 5000 Jahre Kulturgeschichte der
  Gesellschaftsspiele*, WBG, Darmstadt 2007 (brief mention).
