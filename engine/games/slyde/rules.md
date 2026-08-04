# Slyde

**Mike Zapawa, 2020.** Published by **Kanare Abstract** (rulebook and art by Kanare Kato)
and playable at **MindSports**, the designer's canonical page.

Slyde starts with the board completely **full** — a checkerboard of pieces, every one of
them *mobile*. Each move you swap one of your mobile pieces with an adjacent mobile enemy
piece, and **your own piece freezes for good**. So the board slowly seizes up, and the
question is what shape your army is in when it stops. The player with the **biggest group**
wins; if the biggest groups are equal the second biggest decide, then the third, and so on.

> "One important feature of Slyde was the visual impression of a highly ordered structure
> being broken down and reorganized into more chaotic puddles — one chemist I know compared
> it to the melting process. I determined that the goal should be to have your little
> puddles as coalesced as possible." — Mike Zapawa

## Board and setup

The board is a square grid, filled with pieces in a **checkerboard pattern** — White and
Black alternating, no empty cells. Every piece begins **mobile**.

Sizes offered: **12×12** (default — the designer's own board, and "the smallest board where
the game can be expected to have reasonable depth"), **10×10** and **8×8** (the two sizes on
Kanare's published double-sided board), and **6×6** / **4×4** as small learning boards.

**White moves first**, then turns alternate. Passing is not allowed.

## Pieces: mobile and fixed

A piece is either **mobile** or **fixed**. A fixed piece is immobile for the rest of the
game: it can never move, and it can never be moved by an opponent either. In this
implementation a mobile piece is drawn as a plain disc and a **fixed piece as a ring with a
dot inside** — the grey disc that the physical game stacks on a frozen tile.

The two sides keep their traditional names here, **White** (who moves first) and **Black**,
but they are drawn in the platform's usual seat colours: White is the **red** player and
Black the **blue** one.

## The move

**Swap one of your own mobile pieces with an orthogonally adjacent mobile enemy piece.**
Both pieces must be mobile, and they must be neighbours up/down/left/right — never
diagonally.

After the swap:

- **your** piece — now standing where the enemy piece was — becomes **fixed**;
- the **opponent's** piece — now standing where yours was — stays **mobile**.

Click your piece, then click the enemy piece you want to trade places with.

*(Kanare's edition dresses this up as sliding: black tiles on a board of white empty cells,
"slide a single tile horizontally or vertically to an adjacent empty space; neither the tile
nor the target space can have discs on them", then the White player discs the cell that just
emptied and the Black player discs the tile that just moved. That is the same rule — a
black tile is a Black piece, an empty cell is a White piece, and the disc is the fixed
marker.)*

## The anti-mirroring rule

Copying your opponent's moves in mirror image is a real nuisance in a game this symmetric,
so the designer added a counter-weapon:

> "If a symmetric position arises, the next player to move can choose to **change the state**
> (mobile to fixed or vice versa) **of any pawn regardless of color** instead of performing
> the standard swap."

A position counts as symmetric when the board is a **left-right or a top-bottom mirror of
itself with the two colours exchanged**, and every cell's mobile/fixed state matches its
mirror image's. When that happens, instead of swapping you may pick **any** piece on the
board — yours or your opponent's, mobile or fixed — and flip its state. **Click the cell
twice** to do it; the caption tells you when the option is available.

The option is **not** offered on the very first move (the opening checkerboard is trivially
a mirror of itself), and after a state change the position is never still symmetric, so the
two players cannot trade state changes back and forth.

You can turn the whole rule off with the **Anti-mirroring rule** option, which gives exactly
the ruleset in Kanare's printed rulebook.

## End of the game, and who wins

**The game ends when no more moves can be made.** (A swap needs a mobile piece next to a
mobile enemy piece, which is a move for *both* owners at once — so if one player is stuck,
so is the other. The two sheets' different phrasings mean the same thing.)

A **group** is a set of same-coloured pieces connected **orthogonally**. Its size is how
many pieces it holds. **A lone piece is a group of size 1.**

Sort each player's group sizes largest first and compare them term by term:

1. bigger largest group wins;
2. if those tie, bigger **second** largest group wins;
3. if those tie too, the third, then the fourth, and so on.

Two groups of the same size count as **two separate entries** — four scattered lone pieces
are `1, 1, 1, 1`, never "a 4". If the two lists are identical all the way down, the game is
an honest **draw**: as MindSports puts it, "a draw is only possible when both sets of pieces
are partitioned in the same way". Draws are not exotic — an exhaustive solve of the 4×4
board finds that **13.34%** of all terminal positions are exact ties.

## Termination

Every swap fixes exactly one previously-mobile piece, and a fixed piece can never be swapped
again, so **the number of mobile pieces strictly decreases every ply**. With the
anti-mirroring rule off the game therefore ends within `size × size` plies, and the ply cap
below is provably never consulted. An exhaustive solve of the 4×4 board confirms it: all
1,607,132 reachable states, longest possible line 15 plies (bound: 16), and the game is a
**first-player win**. The solve also checks the monovariant on every one of the
**4,397,292 edges** of that state graph, which is *why* it is acyclic — a strictly
decreasing integer cannot return to a value it has left.

With the anti-mirroring rule on, an "unfix" state change can hand mobility back, so that
monovariant is only *non-increasing* across a state-change-plus-swap pair. Two things keep
this bounded. First, **two state changes can never happen back to back**: changing a piece's
state always unbalances that piece against its mirror image, and an exhaustive check of all
**130,816** symmetric 4×4 positions — 65,536 for each mirror axis, overlapping in 256 —
finds not one where any state change leaves the position symmetric. Second, there is a hard backstop at `4 × size × size` plies, at which point the
game simply ends and is scored by the normal cascade — no fabricated result. The backstop
has never been approached: a player who unfixes at every single opportunity still never
repeats a position and never gets past `0.9 × size × size` plies, and against a perfectly
mirroring opponent only one state change per game can ever be *used*: taking it destroys the
symmetry for good, so the mirror never re-forms. (Declining it is different — a mirroring
opponent keeps re-offering the option, about 9 times a game on average.)

Under random play a game lasts about **0.25–0.35 × the number of cells, per player** — which
is exactly the designer's own published figure ("an 8×8 board has 64 fields, so the games
should last 16–23 moves each"). This package measures 20.6 moves each on 8×8. Two further
published numbers from Stephen Tavener's Ai Ai report agree: a 12×12 **random playout runs
94 plies (SD 4)** — this package measures 93.75 (SD 3.80) over 1,000 games — and the game has
**528 distinct actions** on 12×12, which is exactly the 2 × 2·n·(n−1) ordered orthogonally
adjacent cell pairs. Ai Ai also records a **0.00% draw rate** over 1,000 12×12 games, which
this package reproduces.

## The bot

The bot evaluates a cut-short position by **coalescence** — the difference between the two
players' sums of *squared* group sizes. The cascading goal is lexicographic and so gives a
search no gradient to follow, while the sum of squares is smallest exactly when every piece
is a lone group (the opening) and largest when an army is one solid block. Measured through
the platform's MCTS bot on 6×6 **with the rollout cutoff forced** (`max_rollout=4`, so the
evaluation is consulted on every rollout), it scores **0.925 over 120 games** against the same
bot with no evaluation at all (control: 0.533 none-against-none). That figure measures the
*evaluation*, not the bot's strength at default settings — it is sensitive to the search
budget, scoring 0.825 at 60 iterations and 0.942 at 200.

An evaluation is only consulted when a rollout is cut short, and that depends on the board.
A rollout **from the opening** hits the default 50-ply cutoff every time on 12×12 (games run
~94 plies) and on 10×10 (~70), but never on 8×8 (~41), where rollouts always reach a real
finish and the evaluation is not called at all. Averaged over a whole game the rate is lower,
because rollouts started from deep nodes have fewer than 50 plies left to run: **46.8% on
12×12, 24.1% on 10×10, 0% on 8×8 and below**. So the evaluation earns its place on the big
boards and is simply inert on the small ones — which is why a head-to-head on 8×8 returns
exactly 0.500: both sides are then the identical player and the evaluation is never reached.

## Interpretations

Every ambiguity, and the artefact that settled it.

| Question | Decision | Adjudicated by |
|---|---|---|
| Is "adjacent" orthogonal or also diagonal? | **Orthogonal only.** | Both sheets. Kanare: "slide a single tile **horizontally or vertically**". MindSports scores by "**orthogonal** connectivity". Confirmed numerically: 2·n·(n−1) = **264** opening moves on 12×12, the published count. |
| Do lone pieces count as groups? | **Yes, individually.** | Kanare, twice: "an isolated tile/cell is also considered a group of size 1" and "if there are multiple groups of the same color and size, they are **taken as separate groups** for comparison". Its GROUPS figure circles each lone piece on its own — two separate "1"s for Black and two more for White. |
| Does the game end when the *mover* is stuck, or when *nobody* can move? | The distinction is **vacuous**. | The swap relation is symmetric, so one player has a move exactly when the other does. Asserted in `selftest.py` over hundreds of positions rather than assumed. |
| What counts as a "symmetric position"? | A **left-right or top-bottom mirror with the colours exchanged and fixed states matching**. | The sheet never defines it; this is the reading its own worked example requires (after 1.f3-f4 f10-f9 2.k6-j6 k7-j7 the position is a top-bottom mirror, and `selftest.py` replays that example move for move), and the one the AbstractPlay implementation uses. 180° rotation is *not* included. |
| Is a state change available on move 1? | **No.** | The opening checkerboard *is* symmetric under both mirrors, so the clause matters. Three independent sources state the exclusion: Ai Ai's ruleset ("**This does not apply to the first move**"), BGG's description ("if the board reaches a symmetric position (**except on the first move**)"), and the AbstractPlay implementation. |
| Which parity of the checkerboard holds White? | **Unobservable**, so free. | A left-right mirror carries one parity onto the other and is an automorphism of adjacency, of grouping and of the symmetry test, so the two setups are the same game with the colours renamed. Neither sheet specifies it. Proved as a lemma in `selftest.py`. |
| Board size | An **option**; 12×12 default. | MindSports and the designer's essay use 12×12; Kanare's physical board is 8×8 / 10×10. Both are the same game. |
| Anti-mirroring rule | An **option**, on by default. | On MindSports (the designer's canonical page) since its first archived capture in 2020; **absent** from Kanare's 2024 printed rulebook. Turning it off gives the Kanare ruleset exactly. |

## Provenance

- **MindSports**, [mindsports.nl/index.php/the-pit/1019-slyde](https://mindsports.nl/index.php/the-pit/1019-slyde) — the designer's
  canonical page, including his essay on inventing the game. Its rules text is
  **byte-identical across every Wayback capture from 2020-08-05 to 2026-04-20** (only the
  Joomla copyright footer changed), and identical to the page as served today; the
  anti-mirroring rule was present from the first capture.
- **Kanare Abstract**, `Slyde_EN.pdf` (PDF ModDate 2024-06-13) — the published rulebook.
  Never archived on Wayback; fetched live. Its GROUPS figure is the scoring anchor used by
  `selftest.py`.
- **Ai Ai report**, [mrraow.com/uploads/AiAiReports/Slyde.html](http://mrraow.com/uploads/AiAiReports/Slyde.html)
  (generated 2020-06-11) — Stephen Tavener's independent implementation. A third statement
  of the ruleset, and the source of the two playout numbers above. It states the
  anti-mirroring exclusion outright ("This does not apply to the first move") and notes that
  Ai Ai does not enforce the rule at all, for performance reasons.
- **BoardGameGeek** [#308111](https://boardgamegeek.com/boardgame/308111/slyde).

## A note on the AbstractPlay implementation

This package was differentialled against AbstractPlay's `gameslib` (9,298 plies over 200
games at five board sizes, both directions, **zero** rule mismatches). One genuine bug was
found **in the oracle**: it collapses all of a player's lone pieces into a single count and
compares that count as though it were a group size, so `4,1,1,1,1` is scored as `4,4`. That
flips the declared winner on about **1.3%** of 4×4 and **0.7%** of 6×6 finishes. Kanare's
rulebook decides the point explicitly, and this package follows the rulebook.
