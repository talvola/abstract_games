# Coverage — how much of the known abstract-games universe have we built?

**Status:** planning doc / open task. The actual measurement has **NOT** been run yet
(deliberately deferred to save time). This captures the sources, their sizes, a
back-of-envelope estimate, and the method to firm it up later.

**Where we are:** **205 games implemented** (see `GAME_STATUS.md` for the live list).

---

## The catalogue sources (and their raw sizes, per Erik 2026-06-25)

| Source | URL | Raw count | What it is / caveats |
|---|---|---|---|
| **Zillions of Games** (submissions) | https://www.zillions-of-games.com/cgi-bin/zilligames/submissions.cgi | **~2,999** | User-submitted `.zrf` implementations. Heavy on variants, puzzles, and multiple submissions of the same game by different authors. We have a `zillions-to-platform` skill to port these. |
| **ChessVariants.com** (main query) | https://www.chessvariants.com/index/mainquery.php | **~7,500** | Chess variants specifically. Enormous long tail of one-off / never-played variants. We have ~45 chess/shogi/xiangqi-family games. |
| **BoardGameGeek** (abstract subdomain) | https://boardgamegeek.com/boardgamesubdomain/4666/abstract-games | **~5,000+** | Board games tagged "abstract." Includes modern commercial games; **many have no free/online rules**; many aren't pure perfect-information abstracts. |
| **Wikipedia** (list of abstract strategy games) | https://en.wikipedia.org/wiki/List_of_abstract_strategy_games | **~a few hundred** | Curated, notability-filtered. The closest thing to a "canonical set of *distinct, notable* abstract games." |

Raw sum ≈ **~15,500 entries**, but with **massive overlap and intra-source duplication** —
the true count of *distinct named games* is far smaller (rough guess **~8,000–12,000**,
with a very long tail of trivial/one-off variants).

---

## Back-of-envelope estimate (UNVERIFIED — to be measured)

The honest answer depends entirely on the denominator:

- **vs the raw catalogued union (~10,000+ distinct names):** roughly **~2%**.
- **vs ChessVariants' long tail alone (~7,500):** our ~45 chess-family games are **<1%**
  of CV — but a *high* share of the *famous* variants.
- **vs Wikipedia's notable list (~few hundred):** likely a **large fraction — order of
  half** — because we already have nearly every universally-famous distinct abstract
  (observed this session: Fanorona, Dou Shou Qi, Bagh-Chal, Lines of Action, Konane, all
  6 GIPF games, the Q-Gigamic set, the full tafl/mancala/morris/draughts families, Hive,
  Tsuro, Pylos, Arimaa, Shobu, …).

**Summary framing:** **~1–3% of the raw catalogued universe, but plausibly ~40–60% of the
"notable / canonical distinct" core.** The library is comprehensive on the *famous* games;
the remaining 98% is a long tail of variants, clones, and obscure/one-off designs.

> The two numbers measure different things. "% of the raw universe" rewards grinding the
> long tail; "% of the notable core" is the more meaningful quality metric. Track both.

---

## How to actually measure it (the open task)

1. **Pull each source's name list.**
   - Zillions: scrape the submissions CGI (paginated) → list of titles + authors.
   - ChessVariants: scrape `mainquery.php` results → titles.
   - BGG: use the BGG XML API2 (`/family` or the abstract subdomain ranked list) → titles + whether rules exist.
   - Wikipedia: parse the list page → titles (this is the cleanest, smallest list — do this first).
2. **Normalize / alias.** Lowercase, strip punctuation, drop "chess"/"shogi" suffix noise,
   apply an alias map (Reversi=Othello, Nine Men's Morris=Mill, Draughts=Checkers, Gomoku=Five-in-a-Row, etc.). This is where most of the work + judgment is.
3. **Match our 205** (uids + `manifest.name` + a hand alias list) against each normalized source list → coverage % **per source**.
4. **Cross-source dedup** → estimate the distinct union; report our coverage vs that union.
5. **Notable-core metric:** coverage vs the Wikipedia list specifically (the most defensible "are we covering the important ones" number).
6. **Output:** a table — source, raw count, distinct-estimate, our matches, coverage % — plus a "famous games we're MISSING" gap list (the actionable part — feeds `GAMES_QUEUE.md` next-wave picks).

### Gotchas to expect
- **Overlap across sources** is huge (Hex/Go/Chess appear in all four) — never sum raw counts as the denominator.
- **Intra-source dupes:** Zillions has many re-implementations of one game; CV has near-identical micro-variants.
- **"Abstract" is fuzzy on BGG** — many tagged games are commercial/luck/hidden-info, not pure abstracts; filter or note.
- **Variant vs distinct game:** our own rule (per `CLAUDE.md`) is that small rule changes are an `option`, not a new package — so we'd "cover" a CV variant family with one game. Matching must account for that (we cover more games than our package count implies).
- **Clones we deliberately declined** (e.g. Sungka≈Congkak) should count as covered, not gaps.

---

## Why this matters / how it feeds the loop
A periodic coverage run gives (a) a headline "% covered" for both denominators, and (b) a
ranked **gap list** of famous-but-missing games to feed the game factory. As of 2026-06-25
the observation is that the *famous distinct* pool is largely drained — so future picks are
Zillions/CV/traditional deep cuts, and the coverage % vs the raw universe is the metric that
will still climb.
