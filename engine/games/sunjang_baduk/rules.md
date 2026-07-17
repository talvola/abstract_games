# Sunjang Baduk (순장바둑)

The historical Korean form of Go, played from the late 16th century until it
died out under Japanese influence in the first half of the 20th century — the
last recorded game was published in the *Chosun Ilbo* in March 1937 (No Sa-ch'o,
White, vs Ch'ae Keuk-mun, Black, with a borrowed 4.5 komi). It differs from
modern Go in exactly two places: a **prescribed 17-stone opening setup** and a
**distinct scoring procedure** (Korean removal counting). Everything in between
is ordinary Go.

## Setup (fixed 19×19)

Before play, 8 White and 8 Black stones go on the marked "guard points", and
Black's first move is prescribed on tengen — pre-placed here, so **White makes
the first free move**.

- **White (8):** D16, K16, D13, Q13, D7, Q7, K4, Q4
- **Black (8):** G16, N16, Q16, D10, Q10, D4, G4, N4
- **Black's prescribed 17th stone:** K10 (tengen)

```
19 . . . . . . . . . . . . . . . . . . .
18 . . . . . . . . . . . . . . . . . . .
17 . . . . . . . . . . . . . . . . . . .
16 . . . O . . X . . O . . X . . X . . .
15 . . . . . . . . . . . . . . . . . . .
14 . . . . . . . . . . . . . . . . . . .
13 . . . O . . . . . . . . . . . O . . .
12 . . . . . . . . . . . . . . . . . . .
11 . . . . . . . . . . . . . . . . . . .
10 . . . X . . . . . X . . . . . X . . .
 9 . . . . . . . . . . . . . . . . . . .
 8 . . . . . . . . . . . . . . . . . . .
 7 . . . O . . . . . . . . . . . O . . .
 6 . . . . . . . . . . . . . . . . . . .
 5 . . . . . . . . . . . . . . . . . . .
 4 . . . X . . X . . O . . X . . O . . .
 3 . . . . . . . . . . . . . . . . . . .
 2 . . . . . . . . . . . . . . . . . . .
 1 . . . . . . . . . . . . . . . . . . .
   A B C D E F G H J K L M N O P Q R S T
```
(X = Black, O = White; columns skip I. The layout is 180°-rotation symmetric
colour-preserving, and 90°-rotation symmetric colour-swapping apart from the
tengen stone.)

## Play

Identical to ordinary Go (Fairbairn: "Ko and seki are treated exactly as in
Japan"): place a stone on an empty point or pass; enemy groups with no
liberties are captured; **suicide is illegal**; **positional superko** forbids
recreating any earlier whole-board position; the game ends when **both players
pass in succession** (plus a hard ply-cap backstop for termination).

Because of the scoring below, a play inside your own territory costs nothing
(as in Chinese scoring), so fill dame and resolve life-and-death **by playing
it out** before passing — dead enemy stones left on the board neutralise the
surrounding points.

## Scoring — Korean removal counting

After the game ends:

1. Each empty region is classified by what it touches: only Black → Black's
   territory; only White → White's; both → neutral (this zeroes dame and
   seki's shared liberties automatically).
2. **Removal:** stones interior to their own area are removed, leaving only
   the minimal boundary walls. A stone may be removed if the point it vacates
   is still surrounded exclusively by its own colour, and **no removal may
   leave any remaining friendly group in atari** (fewer than 2 liberties);
   cutting points may remain. Each removed stone's point becomes its owner's
   territory.
3. **Score = your empty territory points** after removals, plus komi to White.
   **Stones do not count and prisoners are ignored.** Higher total wins; an
   equal count is a draw (jigo).

Worked example (Bill Spight, Sensei's Library "Sunjang Baduk Counting"): a
finished 9×9 game counts **Black 29, White 31 — White wins by 2** — this exact
position and its post-removal board are frozen in this package's selftest.

## Komi option

- **0 (default):** traditionally there was no komi, so Black's setup advantage
  stood — and ties are honest draws.
- **4.5:** attested for the mid-20th century (used in the 1937 "last game").

## Implementation notes / interpretations

- **Seki:** the historical rule counts no points in seki. Region
  classification handles shared liberties (they touch both colours), but a
  *one-sided eye inside a seki* is pure-reachability territory here and WILL
  count for its owner — a documented deviation from the strict historical
  ruling, matching this platform's play-it-out (Tromp-Taylor-style) philosophy.
- **Removal determinism:** removals are a greedy fixpoint — repeated row-major
  sweeps (top-to-bottom, left-to-right), deleting each removable stone as it
  is met, until a full sweep removes nothing. This reproduces Sensei's
  Library's worked diagrams exactly.
- **Dead stones:** historically dead stones were removed by agreement before
  counting. Here there is no adjudication step — capture dead stones on the
  board before passing (it costs you nothing under this scoring).
- **Tengen:** Black's first move on tengen is treated as prescribed and
  pre-placed (per Fairbairn and Wikipedia; Sensei's Library says "usually" —
  exhibition games have seen K8/K6 instead, not supported here).
- **Ties:** some regions historically scored a tie as a White win (and a
  1-point Black win as a tie). This implementation uses honest draws.
- The two-pass ending is inherited from the platform's Go core: passes are
  always legal, and two consecutive passes end the game immediately, whatever
  is on the board.

## Sources

- Sensei's Library: [Sunjang Baduk](https://senseis.xmp.net/?SunjangBaduk) and
  [Sunjang Baduk Counting](https://senseis.xmp.net/?SunjangBadukCounting)
  (Bill Spight's worked example — the frozen scoring anchor).
- John Fairbairn, "Historic: Sunjang Go", MSO Worldwide (2000):
  [archived](http://web.archive.org/web/20110608021518/http://www.msoworld.com/mindzine/news/orient/go/history/sunjang.html)
  (rules, counting procedure, the 1937 last game).
- Wikipedia, [Go variants — Sunjang baduk](https://en.wikipedia.org/wiki/Go_variants)
  (setup diagram, prescribed tengen).
