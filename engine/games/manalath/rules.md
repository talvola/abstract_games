# Manalath

**Manalath** — "a simply difficult game for 2 players" — was designed by
**Dieter Stein** and **Néstor Romeral Andrés**. Stein's own page dates it
*first sketches 2006*, *first published version 18 July 2012*, with a *wording
change to the end condition on 8 May 2014* (suggested by Ken Shoda). It is
published by nestorgames. BGG id **127993**.

Primary source: the designer's official rules at
<https://spielstein.com/games/manalath/rules>. Every rule below was also checked
move-for-move against the AbstractPlay `gameslib` reference implementation
(`src/games/manalath.ts`, MIT), used here purely as a rule-enforcing oracle — see
`_diff_ap.py`.

Two further published sources were consulted, and they are **not identical** to
the designer's page; the differences are itemised under **"Sources that
disagree"** below:

- the **nestorgames rulebook** for the physical edition
  (<https://nestorgames.com/rulebooks/MANALATH_EN.pdf>, © 2018);
- **Ludii**'s `Manalath.lud` (`Common/res/lud/board/space/group/Manalath.lud`),
  a fourth independent implementation.

## Board

A **hexagon of hexagons** ("hexhex") with **5 cells per side = 61 cells**, the
same board as Yavalath, Pentalath and Blooms. It starts **empty**.

Cells use **axial coordinates** `q,r`; the implied third cube coordinate is
`s = -q-r`, and a cell is on the board iff `max(|q|,|r|,|s|) <= 4`. Each cell has
up to **6 neighbours**: `(q±1,r)`, `(q,r±1)`, `(q+1,r-1)`, `(q-1,r+1)`.

## Pieces and colours

There are two stone colours. **Player 1 owns colour 0 and moves first; Player 2
owns colour 1.**

> The designer's rules call the two colours **White** (Player 1) and **Black**
> (Player 2). This implementation names them **Red** and **Blue** so that the
> names match what you actually see: the platform paints seat 0 red and seat 1
> blue. Red = the rules' White, Blue = the rules' Black. Nothing else changes.

Stones are never moved and never captured.

## Groups, quarts and quints

A **group** is a maximal set of same-coloured stones connected through the
6-neighbour adjacency. A lone stone is a group of 1.

- A group of **4** is a **quart**.
- A group of **5** is a **quint**.

## Play

1. **Player 1 (Red) moves first**, then players alternate.
2. On your turn you place **one stone of *either* colour** — your own or your
   opponent's — on any empty cell.
3. **A stone may never be placed so that a group of more than 5 stones is
   created.** This is a **legality restriction on the placement**, not a losing
   condition, and it applies to **both** colours equally. (The designer's second
   worked example states it directly: *"e7b is simply illegal"*.) A placement
   that joins several groups is measured on the whole merged group, so joining a
   3-group and a 2-group is illegal (3+1+2 = 6) while joining a 3-group and a
   1-group is legal (3+1+1 = 5).
4. **At the end of your own turn**, look at the board:
   - if there is a **quint of *your* colour**, you **WIN**;
   - if there is a **quart of *your* colour**, you **LOSE**.

   These conditions are checked **only after your own move, and only for your
   own colour**. Building a quart or a quint of your *opponent's* colour does
   nothing on your turn — it lands on them at the end of *their* next turn.
5. **Passing** is allowed only when you have **no legal placement at all**
   (rare). An end condition can still become effective on a forced pass. If
   **both** players pass in succession, the game is a **DRAW**.

### Which end condition wins: "whichever occurred first"

The designer's rule is: *"An end condition (win or loss) is effective when it
occurred first and cannot be averted."* Concretely, when you finish your turn
and two conditions of your colour are on the board, the **older** one decides.
Because a single placement can only change the one group that contains the new
stone, "older" is exactly "any quart/quint of your colour that does **not**
contain the stone you just played" — i.e. one your opponent built for you last
turn. So:

| Situation at the end of your turn | Result |
|---|---|
| A quart of your colour that you did **not** just touch | **You lose** — even if the same move built you a quint elsewhere. |
| A quint of your colour that you did **not** just touch | **You win** — even if the same move built you a quart elsewhere. |
| Otherwise, the group containing the stone you just played is a quart | You lose. |
| Otherwise, that group is a quint | You win. |
| Otherwise | Play continues. |

The first row is the designer's own worked example: *"Black has just completed a
white quart… Even if White is going to play on one of the three marked spaces
building a quint, the game is lost for White as the losing condition was created
first and is still active after White's move."*

**A quart can, however, be averted by absorbing it.** "…and is still active after
White's move" is load-bearing: if you extend your own quart with an adjacent
stone, the group becomes a quint and the quart no longer exists — so you **win**.
(Verified against the oracle: white `e3-e6`, White plays `e7w` → White wins.)
That is usually impossible in practice, because a well-built quart is placed
where it cannot be extended without exceeding five.

## Ending, and why it always terminates

Termination is **structural** — no ply cap is needed and none is used:

- every non-pass move fills one of the 61 cells, and stones are never removed;
- the set of legal placements does **not** depend on whose turn it is (any
  player may place any colour), so if one player must pass, the other must pass
  too, and the game ends immediately on that second pass.

A game therefore lasts at most **61 placements + 2 passes = 63 plies**
(`PLY_BOUND` in `game.py`, asserted by `selftest.py`). Nothing in the code is a
*cap*: `PLY_BOUND` is only ever asserted against, never used to force a result,
so no outcome can be manufactured by a limit. Real games end far sooner: over
**20,000 random playouts** the average was **19.8 plies**, the longest was
**45**, and there were **zero passes and zero draws** (outcomes split
9,999 / 10,001 between the two seats).

A genuine tie — both players passing with no end condition on the board — is an
honest **DRAW** (`winner = None`, returns `[0, 0]`); no tiebreak is fabricated.

Random play never finds a pass, but the pass positions are genuinely
**reachable**, and `selftest.py::t_pass_is_reachable` *reaches* them by legal
play rather than hand-building them:

- A 51-stone dead position (every group of size 1–3, all 10 remaining cells
  illegal for both colours) can be filled in **any order**: a group in a partial
  position is a connected subset of a final group, so it also has size ≤ 3, so
  no placement ever exceeds five and no player ever finishes a turn with a quart
  or a quint. Playing those 51 placements in plain sorted order leaves seat 1 on
  move with only `pass`; both pass; **draw**.
- Recolour one stone and play it last, on ply 51 (seat 0's): seat 0 completes a
  **Blue** quart — harmless on Red's own turn, and the whole point of the game's
  attacking idea — and seat 1, with no legal placement, **must pass and loses to
  it**. So "an end condition may become effective even on a pass" is exercised
  on a position the engine actually walked to.

The converse — a *second* passer with an end condition, which is the only
position where our pass ordering could differ from the oracle's — is
**unreachable** — see *Implementation notes and interpretations*, item 3.

## Move encoding (as implemented)

Moves are drop strings, so the standard reserve-tray UI drives them with no
custom front-end:

| Move | Meaning |
|---|---|
| `R@q,r` | place a **Red** stone on cell `q,r` |
| `B@q,r` | place a **Blue** stone on cell `q,r` |
| `pass` | pass (offered only when no placement is legal) |

Both colour chips sit in the mover's reserve tray: **click a colour, then click
a cell** — only the cells that are legal for that colour light up, so you can
never place the wrong colour by mis-clicking. The tray is a *colour picker*, not
a limited supply: the designer's material list is 30 stones of each colour (the
nestorgames edition ships 25), but the rules
impose no supply limit and none is enforced here (a game ends long before 30 of a
colour could be placed). Each chip is drawn in the colour of the stone it will
*put on the board* — the `R` chip red and the `B` chip blue in **both** trays
(the renderer's `reserveOwners` key), so the chip you click always looks like the
stone you get.

## Sources that disagree

Four published sources describe Manalath, and they are not unanimous. This
implementation follows **the designer's own page**, which is the living primary
source (it carries a dated change log, and the end-condition wording was
deliberately revised on 8 May 2014). The differences are recorded here rather
than silently resolved:

| Question | spielstein (designer) | AbstractPlay `gameslib` | Ludii `Manalath.lud` | nestorgames rulebook (2018) |
|---|---|---|---|---|
| Board | hexhex-5, **61** spaces | 61 | `(hex 5)` = 61 | **5-5-6 hexagon, 70** spaces |
| Pieces | 30 + 30 | — | — | 25 + 25 |
| No group > 5 | yes | yes | yes | yes, "**of either colour!**" |
| Quart + quint together | "effective when it **occurred first**" | occurred first | prose says "occurred first"; its **code** checks the quart first, unconditionally | "If both conditions are present at the end of your turn, **you lose**" |
| Cannot move | you **pass**; both pass = draw | same | — | the **game ends**; examine the final position |
| Blockers | — | — | — | optional variant: 1–3 green pieces as dead cells |

What this implementation does, and why:

1. **Board = 61 cells.** Three of the four sources (including the designer's own
   page and both digital implementations) use hexhex-5. The nestorgames 70-cell
   5-5-6 board is the physical edition's; it is not offered here.
2. **Precedence = "occurred first".** The two rules differ in exactly **one**
   case: a friendly **quint that was already on the board** plus a friendly
   **quart you have just built**. "Occurred first" says you **win**;
   nestorgames' and Ludii's shortcut says you lose. Every other combination
   agrees, including the designer's own worked example (pre-existing quart +
   fresh quint = you lose). We follow the designer's page and gameslib. The case
   is also nearly unreachable in practice: holding a pre-existing quint you would
   simply play a move that builds no quart and win under either reading.
3. **Cannot move = pass.** The two formulations are equivalent in effect. Under
   spielstein, the stuck player passes (their own end condition may fire), then
   the opponent passes (theirs may fire), then it is a draw. But the opponent's
   condition was already checked at the end of the opponent's own last turn and a
   pass changes nothing, so the opponent can never have one — which is precisely
   nestorgames' "examine the final position, otherwise a draw".
4. **The green-blocker variant is not implemented.** It appears only in the
   nestorgames rulebook, is agreed between the players rather than fixed, and
   would change the board the oracle validates against.

## Distinctness (dedup gate)

Manalath shares its 61-cell hexhex board with three games already in this
library, and is a distinct game from each:

- **Yavalath** (Browne, 2007) — the nearest relative in spirit (make N, avoid
  N-1). It differs on every mechanical axis: Yavalath scores **straight lines**
  along the three hex axes, Manalath scores **connected groups of any shape**;
  Yavalath players place **only their own colour**, Manalath players place
  **either colour** (so you attack by building your opponent's quart and defend
  by building your own quint); Yavalath is 4-wins/3-loses judged *only from the
  stone just placed*, Manalath is 5-wins/4-loses judged over the *whole board*;
  Yavalath resolves a simultaneous 3-and-4 by **length** (the longer wins),
  Manalath resolves a simultaneous quart-and-quint by **age** (the *older* wins,
  so a fresh quint can lose to a stale quart — the opposite resolution);
  Yavalath has **no legality restriction** on placement, Manalath forbids any
  placement that would build a group of more than five; Yavalath draws on a full
  board, Manalath only on a double pass.
- **Pentalath / Ndengrod** (Browne, 2009) — five-in-a-**row** with Go-style
  capture, own colour only. Manalath has no lines and no captures.
- **Blooms** (Bentley, 2018) — Go-style capture for a capture *count*; each
  player owns two private colours out of four, places 1–2 stones per turn, and
  no group-size rule exists. Manalath has two shared colours, one stone per
  turn, no capture, and its whole game is the group-size rule.

## Verification

- **The designer's own two worked examples, executed.** Both diagrams on the
  rules page were transcribed cell by cell (read pixel-by-pixel from
  `winorloss.png` and `wl2.png`) and are asserted by
  `selftest.py::t_designer_diagrams`. Example 1 confirms the precedence rule
  end-to-end: the position holds exactly one White quart (the group Black
  completed at `i1`), the cells where White can build a quint are **exactly**
  the three the designer marks (`d2`, `d3`, `e2`) — an independent check that the
  transcription is right — and White loses after **all 46** of its legal moves.
  Example 2 confirms the rest: `c7w`/`d7w`/`e7w` each build a White quint yet end
  nothing on Black's turn, `c7b` is legal and harmless, `d7b` builds a Black
  quart and loses on the spot, and `e7b` is rejected because it would join Black
  groups into six.
- **Opening count** — 122 legal moves (61 cells × 2 colours), matching the
  oracle exactly.
- **Lockstep differential** (`_diff_ap.py`) against AbstractPlay `gameslib`:
  random games played move-for-move through both engines, comparing the **legal
  move set** (as (cell, colour) pairs — never as move strings, whose notations
  differ), the board, the side to move, terminality and the winner at **every
  ply**. The algebraic↔axial mapping is itself proved against the oracle's own
  graph dump (61 cells, bijection onto hexhex-4, all 156 edges preserved) before
  a single position is compared, so the differential cannot pass vacuously.
  A second, independently written harness (adversarial QA pass) re-ran this in
  **both** directions — 250 games chosen by our engine and replayed through the
  oracle, plus 250 chosen by the oracle and replayed through ours:
  **10,289 positions, 0 mismatches**, and **1,772** oracle `moves()`
  over-reports, **every one** of them a `b` placement (see note 7).
- **Constructed positions** (`_diff_ap.py --cases`) settle the ten rule
  questions that random play only answers statistically — the win/lose
  conditions, "only your own colour", both precedence directions, quart
  absorption, and the >5 cap on both colours. `selftest.py` asserts each of them
  in our coordinates and cites the oracle case letter.
- **Randomised constructed-position sweep** (adversarial QA pass, its own
  harness): 200 boards built by legal placement while *ignoring* end conditions —
  so they carry quart/quint combinations random games end too early to reach —
  then, for each board and each side to move, the legal-move set and the result
  of up to six moves were compared to the oracle. **2,400 cases, 0 mismatches**,
  covering the whole precedence matrix of the mover's colour: 62 positions with a
  pre-existing quint, 52 with a pre-existing quart, and 17 with **both** at once.
- **Frozen oracle games** — eight complete games chosen and adjudicated by the
  oracle (two per end-condition cause) are replayed by `selftest.py`, so the
  oracle's verdicts survive as a pure-stdlib regression anchor.
- **Mutation testing** — two independent sweeps. The build pass injected sixteen
  rule breaks and `selftest.py` caught fifteen; an adversarial QA pass injected a
  different twenty-six and it caught twenty-four. The three survivors across both
  sweeps are all **provably equivalent** mutants, not gaps:
  `== QUINT` → `>= QUINT` (the >5 cap makes a group of six unreachable);
  dropping the `board.get(placed) == colour` guard (a cell holding the
  *opponent's* stone is in no group of the mover's colour, so `current` stays
  `None` either way); and reordering the pass branch to check the double-pass
  draw first (see interpretation 3 — the positions that would separate the two
  orders are unreachable). The last one is now pinned by an explicit assertion
  anyway, so a refactor cannot flip it silently.

## Implementation notes and interpretations

1. **Colour naming** — Red/Blue instead of the rules' White/Black, to match the
   seat colours the platform draws. Purely cosmetic.
2. **Precedence between two *pre-existing* conditions** — the code checks a
   pre-existing quart before a pre-existing quint. In a real game at most one
   pre-existing condition of your colour can be on the board (your previous turn
   ended with none, and your opponent's single stone can change only one group),
   so the order is never exercised; it is fixed only so the behaviour is
   defined. This matches the oracle, whose source carries the same observation.
3. **Ordering on a forced pass** — the designer's rules say an end condition
   "may become effective" even on a pass, so this implementation evaluates the
   end condition *first* and only then applies the double-pass draw. The oracle
   checks the double-pass draw first. The two orders can only differ if the
   *second* passer has a quart/quint of their own colour, which is unreachable:
   a pass changes nothing, so that condition would already have decided the
   game one ply earlier. (The differential cannot separate them either, because
   random play never produces a pass at all — the argument above, not a test, is
   what settles this one.)
4. **No pie/swap rule** — the designer's rules contain none, so none is offered.
5. **No board-size or variant options** — Manalath is defined on hexhex-5 only.
6. **No stone-supply limit** — see the move-encoding section.
7. **A known bug in the oracle, not shared here** — `gameslib`'s `moves()`
   applies the "no group larger than 5" filter to player 1's groups but not to
   player 2's (the second term of the filter is a bare array, always truthy), so
   it over-reports placements that would build an oversized *Blue* group. Its own
   `validateMove()`/`move()` reject them, so gameslib's actual play is correct.
   The designer's rules are explicit that the restriction is symmetric
   (*"e7b is simply illegal"*), and the nestorgames rulebook spells it out
   (*"a group of more than 5 pieces … of either colour!"*); this implementation
   enforces it for both colours. The differential therefore compares against
   `moves().filter(validateMove)` and separately counts the over-reports.
   The minimal demonstration: with a lone **owner-2** quint on `e3`–`e7`,
   `moves()` returns **112** entries but only **98** survive the oracle's own
   `validateMove` — the 14 over-reports are exactly the `b` placements on the 14
   cells touching that quint. With the same quint owned by **player 1**, `moves()`
   returns 98 and over-reports nothing.
