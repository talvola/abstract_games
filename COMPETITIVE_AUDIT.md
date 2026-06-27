# Competitive Feature Audit & Prioritized Roadmap

_Prepared 2026-06-26. Goal: a successful public launch of the best abstract-games platform for BOTH single-player-vs-computer AND player-vs-player, with breadth (205 games) as the headline differentiator._

This document (1) inventories our current feature set from the code, (2) compares against the major competitors, and (3) gives a prioritized, effort-estimated gap analysis tailored to our stack (FastAPI + SQLAlchemy/Postgres + React/Vite + generic MCTS engine).

---

## Recommended build order (the TL;DR)

Launch model recommendation: **async-first** (correspondence + a fast bot). Do NOT block launch on real-time/WebSockets — async is the proven model for abstract games (Yucata, ItsYourTurn, Little Golem) and avoids the infra cost of live play on free-tier Render. Add live play later.

| # | Feature | Tier | Effort | One-line rationale |
|---|---------|------|--------|--------------------|
| 1 | **Per-game ratings (Glicko-2)** | P0 | M (~2–3 d) | Universal table stake; gives PvP stakes & a retention loop. We already detect win/draw/finish. |
| 2 | **Usable single-player bot** (fix MCTS slowness + real difficulty tiers + generic heuristic) | P0 | M (~3–4 d) | Vs-computer is half the product and is currently broken for heavy games (UI "hangs"). |
| 3 | **Async game expiry / auto-forfeit + in-app "your turn" dashboard** | P0 | M (~2–3 d) | Without per-move deadlines, correspondence games rot and the lobby fills with dead matches. |
| 4 | **Player profiles + replay viewer + leaderboards** | P0 | M-L (~2–3 d) | Identity & progression; we already persist every match + move — just expose it. |
| 5 | **In-game chat / per-move comments** | P1 | L (~1–2 d) | Social glue; correspondence is inherently social and we already poll the match. |
| 6 | Spectating + public/live game index | P1 | L (~1–2 d) | Discovery + "the place is alive"; `get_match` already serves non-players. |
| 7 | Matchmaking: quick-pair & seek-by-rating | P1 | L-M | Liquidity; builds directly on the existing seek system + new ratings. |
| 8 | Anti-abandonment karma/reputation | P1 | M | Protects async quality once human volume grows (pairs with #3). |
| 9 | Real-time (live) play via WebSockets | P2 | H | Casual liquidity & "finish in one sitting"; significant infra lift, defer past launch. |
| 10 | Tournaments (Arena / Swiss) | P2 | H | Strong engagement driver but heavy; needs pairing + scheduling worker. |
| 11 | Daily puzzles across all games | P2 | H / research | Huge differentiator but hard to auto-generate for arbitrary abstracts (see caveat). |
| 12 | Bot personalities, PWA/mobile, premium tier | P2 | varies | Polish & monetization; post-launch. |

**Do first (the launch bundle): #1–#4.** They convert "a tech demo with 205 games" into "a platform you keep coming back to," and each leverages data/logic we already have.

---

## STEP 1 — What we HAVE vs. what we LACK (from the code)

### We HAVE
- **Accounts & auth** — email/password registration, hashed passwords, session cookie (`server/auth.py`, `/api/auth/*`).
- **Async correspondence matches** — server-authoritative, full state + move history persisted (`Match`, `MoveRecord` in `server/models.py`); polling-based refresh (3 s in `MatchPlay.jsx`, 6 s in `Lobby.jsx`).
- **Open challenges (seeks)** — post/accept/cancel an open challenge with seat preference (`Seek` model, `/api/seeks`).
- **Vs-bot** — generic MCTS (`engine/agp/mcts.py`) with a wall-clock budget (`AGP_BOT_MAX_TIME=3.0`) and **3 difficulty levels** exposed in the UI (Easy/Medium/Hard = 80/300/1200 iterations).
- **Anonymous quick-play** — stateless hotseat or vs-bot, state held client-side (`QuickPlay.jsx`, `/api/games/{uid}/new|move|bot`).
- **Move history / move log** — `build_history` replays the match for labelled notation; shown via `MoveLog`.
- **Resign**; **draws** via freeform action tokens; **freeform/honor-system** game mode.
- **"Your turn" email notifications** (`server/notify.py`, fired as a background task).
- **205 games**, category-grouped searchable picker, per-game `rules.md` modals, BGG/source links.
- **In-process game upload** (admin-gated, validated in a subprocess) — content pipeline.
- **Single-origin deploy** on Render + Neon Postgres (serves API + built SPA).

### We LACK (confirmed absent in code)
- **Ratings / ELO / Glicko** — none. No competitive stakes, no skill tracking.
- **Leaderboards / rankings** — none.
- **Player profiles / stats / win-loss records** — none (no profile endpoint or screen).
- **Replay viewer** — history is stored but there is no step-through replay UI for finished games.
- **Real-time / live play** — none; only HTTP polling. No WebSockets.
- **Matchmaking** beyond a flat manual seek list — no quick-pair, no rating-range filtering, no direct invite-by-username.
- **Chat / kibbitzing / per-move comments** — none.
- **Spectating / public game browser** — `get_match` works for non-players, but there is no public match list or "watch" UI.
- **Time controls / clocks / move deadlines** — none. Async games can stall forever (no auto-forfeit).
- **Anti-abandonment (karma/reputation)** — none.
- **Tournaments** — none.
- **Puzzles / daily tactics / training** — none.
- **Takeback/undo, hints, analysis** — none (history exists; no analysis tooling).
- **Friends/social graph, direct messaging** — none.
- **Bot personalities / flavor** — only raw iteration counts.
- **Mobile apps / PWA** — responsive web only (untested for mobile here).

> Note: `PLATFORM_PLAN.md` already anticipates most of these (Phase 4 = "Ratings/Elo, move clocks/timeouts, spectating, replay viewer"; §8 mines Game Courier for time controls, per-game ratings, kibbitzing). This audit prioritizes that backlog against competitors.

---

## STEP 2 — Competitor feature scan (engagement/retention)

| Platform | Model | Standout retention features |
|---|---|---|
| **Lichess** | Free, open, chess+8 variants | Glicko-2 (per variant & speed); open seek lobby + quick-pair; **live AND correspondence**; **puzzles** (Streak/Storm/Racer, own rating) — biggest daily driver; Stockfish levels 1–8 + bot API; **unlimited Arena & Swiss tournaments**; analysis/Studies; TV/spectate, teams, leaderboards, mobile apps. 100% free (donation only). |
| **Chess.com** | Freemium, retention-optimized | Glicko ratings; **100k+ puzzles**, Puzzle Rush/Battle; **20+ named personality bots**; lessons; player **clubs** hosting events; tournaments; gamified "game review" (brilliant/blunder); aggressive metered freemium (Gold/Platinum/Diamond). |
| **BoardGameArena** | 1,300+ games — the "many games, one platform" template | **Real-time AND turn-based** per table; **per-game Elo** + **Arena seasons** (3-mo champions); **karma/reputation** anti-abandonment (critical for async); tournaments + leagues; universal server-enforced rules, chat, spectate, replays; Premium (~€2–4/mo) with viral "one premium benefits the whole table." Notably **no AI bots** for most games. |
| **Ludii** | Academic general game system, 1,000+ games | Ludeme DSL; bundled general-game-playing **MCTS AI** + open AI API (closest analog to our generic bot). Player-facing retention is minimal — value is breadth + AI + design tooling, not a social site. |
| **igGameCenter** | 100+ abstract/connection games — closest genre competitor | Real-time play, ratings, rooms/lobby, configurable board sizes. Dated UI, thin on puzzles/tournaments — shows the gap a polished abstract platform can fill. |
| **PlayOK / ItsYourTurn / Yucata** | Classic many-game communities | Elo + rooms/rankings, tournaments, replays, messaging (PlayOK, mostly real-time); **pure async + ladders/rankings** (ItsYourTurn); **async Euro games + Elo + themed rank ladder** (Yucata). Demonstrate that **async + ratings + ladders** is a durable retention loop for a small community. |
| **Tabletopia** | 2,400+ games, sandbox | No rules enforcement, no AI — opposite philosophy; less relevant. |

### Table stakes (almost everyone has them)
Accounts + profiles + stats/replays · **per-game rating (Elo/Glicko)** · lobby with open seeks + invites (matched by rating) · **both real-time and async** · in-game chat + spectating · leaderboards · friends + your-turn notifications · mobile access.

### High-value differentiators
- **Puzzles with their own rating + streak modes** (Lichess/Chess.com's #1 daily driver) — almost nobody offers this **across many abstract games**: a wide-open niche for a 205-game library, but technically hard (see P2 caveat).
- **Graded + personality bots** — we already have the MCTS engine; cheap to extend.
- **Auto-run tournaments** (Arena + Swiss).
- **Anti-abandonment karma** (BGA) — essential once async human volume exists.
- **Seasonal competitive mode + themed progression ladders** (BGA Arena, Yucata ranks) — long-term goals beyond raw Elo.
- **Freemium with viral table-level upsell** (BGA/Chess.com).

---

## STEP 3 — Prioritized gap analysis (tailored to us)

### P0 — Must-have for a credible public launch

**1. Per-game rating system (Glicko-2).**
- _What:_ A rating per (user, game), updated when a human-vs-human match finishes. Glicko-2 (not plain Elo) handles sparse play and rating deviation — right for a 205-game library where any one game sees few games per player. Show rating on profile, match screen, and seek rows.
- _Why:_ The single most universal table stake. It is what turns isolated games into a competitive ladder and is the core PvP retention loop. Cheap relative to its impact.
- _Effort (our stack):_ **Medium.** New `Rating` table (user_id, game_uid, rating, rd, vol, games) or a JSON column on `User`. ~150 lines of stdlib Glicko-2. Hook into `_commit_position`/`resign_match` (we already compute `winner`/draw). New `/api/leaderboard/{game_uid}` + include rating in `match_view`/profile. Frontend: show numbers. Skip ratings for bot games (or rate them provisionally).

**2. Usable single-player bot (fix MCTS + real difficulty + generic heuristic).**
- _What:_ Make the bot responsive and meaningfully tiered across light AND heavy games. The wall-clock budget (`AGP_BOT_MAX_TIME`) already exists; add a **generic fallback heuristic** at the rollout cutoff (material/mobility/piece-count so heavy games don't rely on random rollouts that never terminate), and map difficulty to a **time budget**, not just iteration count, so "Hard" is actually stronger and "Easy" is fast.
- _Why:_ Vs-computer is half the value proposition and the instant on-ramp (no account, no opponent needed). It is currently a **🔴 known issue** — unusably slow for Chess/heavy games, UI looks hung (see `KNOWN_ISSUES.md`). A broken bot undermines the single-player half of the pitch on day one.
- _Effort:_ **Medium.** `mcts.py` already has `max_time` + `max_rollout` + a `heuristic` hook. Work is: ship a generic material/mobility heuristic usable by any `Game` lacking its own; lower default `max_rollout`; tune difficulty→(time, iterations) mapping; verify across a sample of light/medium/heavy games. Per-game heuristics can come later.

**3. Async game expiry / auto-forfeit + in-app "your turn" dashboard.**
- _What:_ A per-move deadline (e.g. configurable "days per move", default ~3–7 days) with **auto-forfeit** when it lapses, plus a "Your turn (N)" count and a clear dashboard ordering (we already sort by active/my-turn). We have email notifications; add the in-app badge.
- _Why:_ Without deadlines, correspondence games **rot** — an opponent who stops moving locks a game forever, the lobby fills with zombies, and ratings can't settle. This is the #1 failure mode of async platforms and a real launch risk for PvP. Game Courier's two-axis Grace/Reserve model (`PLATFORM_PLAN.md §8`) is the reference.
- _Effort:_ **Medium.** Add `deadline`/`days_per_move` to `Match`; a lightweight background sweeper (FastAPI startup asyncio task or a Render cron) that finds `status=active` matches past deadline and forfeits the side to move. We have **no worker today**, so this is the first piece of scheduled infra — keep it minimal.

**4. Player profiles + replay viewer + leaderboards.**
- _What:_ A public profile (display name, per-game ratings, W/L/D, recent games), a **step-through replay** of any finished match, and per-game leaderboards.
- _Why:_ Identity + progression + the "watch how it ended" payoff. Strong retention with low marginal cost because **we already persist every match and every move** (`MoveRecord`) and already build labelled history.
- _Effort:_ **Medium-low.** Mostly read endpoints over existing data: `/api/users/{id}` (profile + match list), reuse `build_history` for replay, `/api/leaderboard`. Frontend: a profile screen + a replay component that steps `render(state-at-ply)` (replay by re-applying moves, which `build_history` already does).

### P1 — Strong (fast-follow after launch)

**5. In-game chat / per-move comments (kibbitzing).** _What:_ a message thread per match. _Why:_ correspondence is social; cheap engagement lever (`PLATFORM_PLAN.md` flags it as high-value). _Effort:_ **Low.** New `Message(match_id, user_id, body, ts)`; poll alongside the match (we already poll). Per-move annotation is a natural extension.

**6. Spectating + public/live game index.** _What:_ a browsable list of in-progress and recent public matches; anyone can watch. _Why:_ discovery and social proof ("the place is active"). _Effort:_ **Low.** `get_match` already serves non-players (`optional_user`); add `/api/matches/public` and a browse/watch UI; the existing 3 s poll gives near-live spectating.

**7. Matchmaking — quick-pair & seek-by-rating.** _What:_ "Play now" that auto-matches an open seek for a game, and rating-range filtering on seeks. _Why:_ liquidity — the flat manual seek list doesn't scale. _Effort:_ **Low-Medium**, builds on the seek system + new ratings.

**8. Anti-abandonment karma/reputation.** _What:_ BGA-style score penalizing players who let games time out / abandon. _Why:_ protects async quality as human volume grows; pairs with #3. _Effort:_ **Medium** (a counter on `User`, decremented on forfeit-by-timeout, surfaced in matchmaking).

### P2 — Nice-to-have / later

**9. Real-time (live) play via WebSockets.** _What:_ live games with a shared clock, instant move push. _Why:_ casual liquidity + "finish in one sitting"; what many casual users expect. _Effort:_ **High** — FastAPI WebSocket endpoints, broadcast-on-move, and at scale a pub/sub (Redis) for multi-worker fan-out. **Free-tier Render spins down after ~15 min idle**, which is hostile to persistent sockets. **Recommendation: defer past launch** — our 3 s polling is "good enough" near-real-time for turn-based abstracts, and async is the genre-appropriate default. Revisit when concurrency justifies the infra.

**10. Tournaments (Arena / Swiss), auto-run.** _What:_ scheduled events with automated pairing + brackets. _Why:_ a proven engagement spike (Lichess/BGA). _Effort:_ **High** — pairing algorithms, scheduling, a worker; depends on ratings (#1) and a healthy player base first.

**11. Daily puzzles across all 205 games.** _What:_ a daily tactic per game with its own rating/streak modes. _Why:_ the single biggest daily-engagement driver on chess sites, and **nobody offers it across many abstracts** — a standout differentiator. _Effort:_ **High / research.** Caveat: there is no generic notion of a "puzzle" for an arbitrary abstract game without a strong solver — you can't auto-mine tactics the way Lichess does from engine eval swings. Feasible paths: use the (improved) bot to find forced wins in N plies from sampled positions, or curate positions per game. Treat as an R&D project, not a quick win.

**12. Bot personalities, PWA/mobile, freemium premium tier.** _What:_ named/flavored bots (cheap given the engine), installable mobile web, and a BGA/Chess.com-style premium tier with viral table-level upsell. _Why:_ polish, reach, and monetization. _Effort:_ varies; post-launch.

---

## Opinionated bottom line

We have the hard part — a generic engine, 205 games, accounts, async matches, seeks, and a bot framework. What's missing is the **retention layer**, and almost all of it leverages data we already store. Ship **ratings, a working bot, async deadlines, and profiles/replays/leaderboards** as the launch bundle; that alone makes us competitive with the niche abstract platforms (igGameCenter, ItsYourTurn, Yucata) while our 205-game breadth out-classes them. **Stay async-first** — skip WebSockets and tournaments until player volume earns them. The long-game differentiator, once the basics are solid, is **cross-game puzzles + graded/personality bots**: a strong single-player loop across 205 games is a niche no competitor occupies.
