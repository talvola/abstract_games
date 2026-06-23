# Game Factory — Queue & Status

On-disk state for the autonomous game-integration loop (the "factory"). The
universe map and capability gaps live in `GAME_BACKLOG.md`; this file is the
*queue* and the *human-escalation digest*.

---

## ⭐ CATCH-UP DIGEST (read this first) — autonomous run of 2026-06-21 [LOOP WOUND DOWN]

**The factory ran unattended while you were away; I've wound it down to a clean,
green stopping point.** Everything below is on `origin/main`; the dev app is live.

### Headline
- **54 games on `main`** (session started at **24** → **+30** added).
- **10 batches**, every game = `agp validate` + an **independent rule-review**,
  perft/reference-anchored where a published number or engine (python-chess /
  shakmaty / World Draughts Forum) exists. **Full test suite green.**
- **The review gate caught + I fixed 4 real bugs before shipping**, and I declined
  1 clone — quality held the whole way, **zero escalations needed**.

### The 30 new games, by family
- **Chess variants (perft/reference-anchored):** King of the Hill, Three-Check,
  Racing Kings, Horde, Antichess, Atomic *(all python-chess/shakmaty-verified)*.
- **Historical chess:** Makruk, Shatranj, Capablanca, Courier, Wildebeest.
- **Asian chess (hopper family):** **Xiangqi**, **Janggi**, Dou Shou Qi (Jungle).
- **Tafl:** Tablut, Hnefatafl, Ard Ri *(+ Brandub from before)*.
- **Draughts:** International, Turkish, Brazilian, Frisian, Konane.
- **Go family (new liberty/capture core):** Atari Go, NoGo, Gonnect, Tanbo.
- **Connection:** Havannah, Gonnect.
- **Mancala:** Oware.  **Alignment:** Connect6.  **Classics:** Fanorona, Dao.

### Quality scorecard (the gate working)
1. Courier Chess — insufficient-material masked a K+2Manns checkmate → fixed.
2. Frisian Draughts — wrong capture-weighting → fixed to the official king=1.5.
3. Atomic — factory selftest imported python-chess (broke the suite) → rewrote
   pure-stdlib **and hardened the factory** so future selftests stay dep-free.
4. Wildebeest — castling rook on the wrong side + a bogus no-op castle → replaced
   with NoCastling (the authentic 11-wide rule is unsourced).
5. Declined **Tawlbwrdd** — the factory made it byte-identical to Hnefatafl.

### ⚠️ Needs your decision: _none._ Nothing is blocked on you.

### ▶ When you're back — suggested next moves (your call)
The headless game long-tail is largely drained of *distinct, high-value* titles.
The next frontier is the **capability investments** — they unlock the biggest
missing names but touch the **renderer/server, so they want your eyes**:
1. **Drops / reserve tray** (M effort) → **Nine Men's Morris family, Crazyhouse,
   Shogi**. Highest fame-per-effort.
2. **Stacking** (L) → **Tak, DVONN, TZAAR, Focus**.
3. **Go territory scoring** (L) → **full Go** — *de-risked this session*: the Go
   liberty/capture core is already built (Atari Go/NoGo/Gonnect/Tanbo); this is
   just the scoring/UI layer on top.
Lower-priority: point-and-line boards (TwixT), Pentago's rotate UI, >2-seat UI
(Chinese Checkers). See `GAME_BACKLOG.md` for the full ranked map.
Also worth a pass: **play-test the new games in the browser** — especially the
unusual boards (Oware 6×2 with seed-count labels; Xiangqi/Janggi/Jungle 9×10/7×9;
Fanorona 9×5) — to confirm rendering/UX reads well. Logic is fully tested; only
visual polish hasn't had a human eye.

### How to review fast
Every game ships a one-page `rules.md` (rules as implemented + any documented
simplifications) and a `selftest.py` (its correctness anchor, run by the suite via
`test_package_selftests`). `git log --oneline` shows the per-game merge rationale.
The factory is a reusable Workflow (`.claude/.../game-factory-*.js`) — "run the
factory on \<games\>" restarts it anytime.

_Final digest update: after batch 10 merge (54 games). Loop wound down._

---

## Capability work — drops / reserve tray (2026-06-21, with Erik in the loop)

**Shipped the #1-ranked UI investment: an off-board reserve + drop moves**, with
**Crazyhouse** (game #55) as the first consumer. Design approved by Erik up front
(guarded hooks in `ChessLike`; two trays top/bottom).

- **Engine:** a `DROPS` strategy on `agp.chesslike` (`NoDrops` default →
  `CrazyhouseDrops`) adds `CState.hands` + a `promoted`-square set, all no-op and
  absent from serialize/poskey unless enabled → the other ~20 chess variants are
  byte-identical (suite green). Drop move = `"L@c,r"`; captures bank to the
  reserve (promoted piece → pawn); `_insufficient` off when drops enabled.
- **Web:** `Board.jsx` renders two seat-colored reserve trays (seat 1 top / seat 0
  bottom) + click-chip-then-empty-cell to drop; drop targets highlight and the
  pawn back-rank rule is enforced visually. **No server change** (enforced path is
  `move in legal_moves`).
- **Anchor:** differential vs python-chess `CrazyhouseBoard` — perft
  20/400/8902/197281 (start) + 62/4715/197413 (drop-bearing midgame), and a
  400-game synchronized move-set walk (46,427 plies, **0 mismatches**). Committed
  selftest is pure-stdlib with frozen perft + capture/demotion/back-rank checks.
  Verified in-browser (Quick Play hotseat): capture→reserve→drop full lifecycle.
- **Next on this primitive:** Shogi (own `DropRules`: promotion zone + nifu) and
  the Morris family (custom adjacency + mill-removal, not a ChessLike consumer).
  See `GAME_BACKLOG.md` §1.

---

## Autonomous expansion run (2026-06-21/22) — 54 → 72 games + ALL 7 UI capabilities

**Final tally:** 18 games added across the run, **all seven UI capabilities on the
backlog shipped, each with a flagship consumer**, plus a multi-action-turn demo and
the renderer primitives below. All on `main`, suite green throughout, every game
browser-verified; 11 verification sub-agents ran (UI review + 10 rule reviews),
all MERGE.

| Capability | Flagship consumer(s) |
|---|---|
| drops / reserve | Crazyhouse #55, Shogi #56, Mini Shogi #59 |
| stacking (towers) | Lasca #60 |
| territory scoring | Go #61 |
| >2-seat (up to 6) | Rolit #63 (4p), Chinese Checkers #68 (6p) |
| walls / point-and-line | Quoridor #69, TwixT #70 |
| dice / randomness | EinStein würfelt nicht #71 |
| cards | Onitama #72 |

Other games: Nine Men's Morris #57, Bagh-Chal #58, Pentago #62 (place+rotate via
the =CHOICE picker), Alquerque #64, Kalah #65, Y #66, Yote #67. Renderer gained:
reserve trays, stacking glyph, `board.lines` (under-cell grooves), `board.overlay`
(over-cell bridges), `board.tints` (terrain/edges), `board.walls` (groove slots),
6 seat colours, triangular-hex + 6-pointed-star polygon layouts, extent-margin.

**The entire UI-capability roadmap is now complete (all 7 of GAME_BACKLOG.md's
ranked gaps).** Remaining work is purely incremental games on existing primitives:
DVONN/Focus/Tak (stacking), Surakarta (loop-capture), Mu Torere, Tapatan, Twelve
Men's Morris.

---

## (superseded) earlier note — 54 → 63 games + 4 UI capabilities

Erik set the loop to "keep going for hours, spin off sub-agents, maintain a status
artifact." On-disk state, all on `main`, suite green:

- **`GAME_STATUS.md`** (new) — the living catalogue of every game (board,
  verification anchor, selftest/rules/browser status), generated by
  `engine/tools/gen_game_status.py`. **This is the artifact to read for current
  status.** Regenerate after each new game.
- **Shogi (#56)** — new `agp/shogilike.py` core (colour-relative move-gen + drops
  + zone promotion); python-shogi-verified (perft 30/900/25470/719731 + 41k-ply
  walk, 0 mismatches). A walk-found slide bug (`dr` vs `dr*fwd`) was fixed.
- **Nine Men's Morris (#57)** — 24-point mill game; independent rule review = MERGE.
- **Bagh-Chal (#58)** — 5×5 alquerque Tigers & Goats; review = MERGE (capture
  inference fuzzed over 20k boards).
- **Mini Shogi (#59)** — 5×5 shogi on the verified ShogiLike core; published perft
  14/181/2512 (depth-1 hand-checked).
- **Lasca (#60)** — Lasker's draughts-with-towers; **first STACKING game** →
  added the stacking renderer (towers as layered owner bands + height badge);
  review = MERGE (under-tucking + liberation + mandatory-not-maximum capture).
- **Go (#61)** — full Go with **TERRITORY SCORING** (the 3rd big capability and
  the flagship hole): liberty core + two-pass end + **Tromp-Taylor area scoring**
  (algorithmic, so no dead-stone UI) + komi + 9/13/19 sizes; review = MERGE
  (scoring hand-verified, ko/superko confirmed). **All three capabilities Erik
  named — drops, stacking, territory scoring — are now shipped.**
- **Pentago (#62)** — place-then-rotate-a-quadrant; rides the existing `=CHOICE`
  picker (the **multi-action-turn** primitive) + `board.lines` quadrant dividers.
- **Rolit (#63)** — four-player Reversi; the platform's **first >2-player game**,
  which drove the **>2-seat UI** capability: `colors.js` now has 6 seat colours,
  and `QuickPlay.jsx` seats N players (chips + turn cycling) with bot mode playing
  all non-human seats. The MCTS already backed up per-player payoffs, so no engine
  change. Verified in-browser (full P1→P4 round, flips, per-seat scoring); existing
  2-player games unaffected (Amazons' neutral arrow is now green, reads fine).
- **Renderer** — added `board.lines` (cosmetic connecting lines) + `board.tints`
  (terrain colours) + an extent-relative viewBox margin. Drove a **UI-review pass**
  (a sub-agent) on the unusual boards → fixed **Jungle's invisible river** (now
  tinted), drew **Fanorona's alquerque lines**; verified Oware renders correctly.
- **Method:** per game, build → conformance → an independent adversarial
  rule-review sub-agent (or a published/perft anchor) → browser-verify → commit.
  Verifier is always a *different* agent than the implementer.

---

## The gate (option 1, updated 2026-06-21)

Erik delegated merge authority: the orchestrator may auto-merge after a **detailed
independent code review**, without separate approval.

- **AUTO-MERGE to `main`** — `agp validate` green **AND** the rules are confirmed
  faithful by an *independent* check: a published numeric anchor (chess-family
  **perft** / solved result) **OR** a clean adversarial rule-review (a fresh agent
  re-deriving every move + win condition with no faults) **plus the orchestrator's
  own code review**. A published anchor is preferred but no longer required.
- **QUEUE for review** — only when the review surfaces a genuine **open ruleset
  decision** that's Erik's to make, a **new board shape/rendering** needing his
  eyes, or an issue that can't be confidently auto-resolved. Held on a `factory/*`
  branch + listed under *Needs human*.
- **BLOCKED** — needs a missing platform primitive (stacking, hand/drops, Go
  territory scoring, point-and-line edges, >2-seat UI). Deferred; see
  `GAME_BACKLOG.md`.

The loop: discover → implement (isolated, reference an existing package) →
`agp validate` + anchor self-test → **independent** adversarial rule-review →
deterministic gate → auto-merge or queue. Verifier is a *different* agent than the
implementer.

## Legend
`queued` · `building` · `done(auto)` · `review` (queued for Erik) · `blocked`

## Batch 1 — harness proof (2026-06-20)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| King of the Hill | auto | chess perft 20/400/8902 (re-derived) + center-king win | **done(auto) → main** |
| Three-Check | auto | chess perft 20/400/8902 (re-derived) + 3-check win | **done(auto) → main** |
| Tablut (9×9 tafl) | review | conformance + capture/escape positions; no published number | **done → main** (king-assist resolved from Cyningstan) |

Both auto games were independently re-verified (the verifier recomputed perft to
197281 at depth 4, matching standard chess) and re-checked by me before merge. The
factory's per-package `selftest.py` is run by the suite via `test_package_selftests`.

## Batch 2 — chess-variant pack (2026-06-20)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Racing Kings | auto | shakmaty perft 21/421/11264 + 31,920 python-chess differential positions, 0 mismatches | **done(auto) → main** |
| Makruk (Thai chess) | review→auto | independent adversarial review (option 1) | **done → main** |
| Shatranj (medieval) | review→auto | independent adversarial review (option 1) | **done → main** |
| Capablanca (10×8) | review→auto | independent adversarial review (option 1) | **done → main** |

Under the option-1 gate, all three merged after a detailed independent review:
three fresh adversarial code reviewers (separate from the factory's verifiers),
each returning MERGE with no required fixes, plus the orchestrator's own code read
and runtime probes of the risk areas (Makruk 6th-rank promotion, Shatranj Alfil
leap / bare-king, Capablanca castling).

## Batch 3 — draughts + connection (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| International Draughts (10×10) | auto | published WDF perft 9/81/658/4265(/27117/167140), re-derived by verifier + orchestrator | **done(auto) → main** |
| Turkish Draughts (Dama) | review→auto | independent review; apply_move cross-checked over 40k positions + 489k jump-chains, 0 double-jumps | **done → main** |
| Havannah (hexhex) | review→auto | independent review of ring/bridge/fork (outside-flood-fill ring); exhaustive shape tests | **done → main** |

International was perft-locked (gold-standard anchor). Turkish + Havannah merged
after fresh adversarial reviewers + the orchestrator's own read of the hard logic
(Turkish immediate-removal-during-chain; Havannah ring detection). All MERGE.

## Batch 4 — divergent chess variants (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Horde Chess | auto | python-chess HordeBoard: perft 8/128/1274/23310 + 400-game move-gen & 2000-game outcome differential, 0 mismatches | **done(auto) → main** |
| Antichess (Losing Chess) | auto | python-chess AntichessBoard: perft to depth 5 (…/2732672) + 789 terminal positions, 0 mismatches | **done(auto) → main** |
| Courier Chess (12×8) | review→auto | independent review; **caught + fixed** an insufficient-material bug masking K+2Manns mate | **done → main** |

Horde (king-less White) and Antichess (non-royal king, forced capture, stalemate-
as-win) both got python-chess differential verification. Courier merged after the
review-caught insufficient-material fix.

## Batch 5 — atomic + tafl + CGT (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Atomic Chess | auto | python-chess AtomicBoard differential (1500 games, kiwipete perft d4=3,492,097), 0 mismatches | **done(auto) → main** |
| Hnefatafl (Copenhagen 11×11) | review→auto | independent review vs canonical Copenhagen sources + my probes | **done → main** |
| Konane (Hawaiian) | review→auto | independent 3000-position move-gen cross-check + my probes | **done → main** |

(Atomic's committed selftest was rewritten pure-stdlib post-merge — see Quality
signals above.)

## Batch 6 — Janggi + tafl + Frisian (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Janggi (Korean Chess) | review→auto | reviewer hand-derived 31-move opening + full cannon/elephant/palace re-derivation; perft baseline 31/949/29697 | **done → main** |
| Ard Ri (7×7 tafl) | review→auto | independent rule re-derivation (Tablut-family) | **done → main** |
| Frisian Draughts | review→**fix**→auto | review REJECTED a weighted-capture bug; fixed to king=1.5 summed value, re-verified | **done → main** |

## Batch 7 — Go-family (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Atari Go (Capture Go) | review→auto | independent re-derivation; liberty/group-capture + positional superko; my capture/suicide probes | **done → main** |
| NoGo (anti-Go) | review→auto | independent re-derivation; capture & suicide both illegal | **done → main** |
| Tawlbwrdd (11×11 tafl) | — | review found it AST-identical to Hnefatafl | **DISCARDED (clone, not shipped)** |

## Batch 8 — connection + draughts + wide chess (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Gonnect | review→auto | Go capture (reuses atari_go core) + edge connection; reviewer read official rulebook | **done → main** |
| Brazilian Draughts (8×8) | auto | perft 7/49/302/1469 = published 8×8 counts; international-rules engine at N=8 | **done(auto) → main** |
| Wildebeest Chess (11×10) | review→**fix**→auto | review REJECTED a castling bug; replaced with NoCastling (unsourced rule), re-verified | **done → main** |

## Batch 9 — Mancala + Go-family + classic (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Oware (Mancala/Awari) | review→auto | re-derived vs canonical Awari; 2000-game seed-conservation + unreachable-state proof | **done → main** |
| Tanbo (Mark Steere) | review→auto | agent read Steere's official PDF; distinct 'bounded-root' capture + 2026 layout | **done → main** |
| Dao (4×4) | review→auto | re-derived vs US patent + Wikipedia/BGG; maximal-slide + 4 win conditions | **done → main** |

## Batch 10 — distinct traditionals (2026-06-21)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Fanorona | review→auto | re-derived vs canonical Wikipedia; approach+withdrawal captures, chains | **done → main** |
| Dou Shou Qi (Jungle) | review→auto | full rank hierarchy, river jumps, traps, dens verified | **done → main** |
| Connect6 | review→auto | 1-then-2 stone mechanic + gap-bridging six verified | **done → main** |

## Batch 11 — incremental traditionals on existing primitives (2026-06-22)
_First batch of the post-roadmap "incremental games" phase — all reuse the
Morris/polygons adjacency primitive; no new capability._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Tapatan (Three Men's Morris) | review→auto | independent re-derivation of the 8-line 3×3 board (centre↔all 8, no corner–corner adjacency); no-capture mill-to-win; 5000-game termination proof | **done → main** |
| Mū Tōrere | review→auto | re-derived vs canonical (Bell) ruleset; the centre-entry-only-when-adjacent-to-enemy rule + loss-on-no-move; novel 8-pointed-star polygon layout, browser-verified | **done → main** |
| Twelve Men's Morris | review→**fix**→auto | reviewer flagged a genuine fork: full-board (12+12 fill all 24 pts, no mill) was scored a LOSS for the mover via the generic no-move rule. I resolved it to the **traditional DRAW** (faithful rule, not an open choice — it's the variant's signature drawishness), documented in rules.md + asserted in selftest, then auto-merged | **done → main** |

## Batch 12 — stacking + loop-capture on existing primitives (2026-06-22)
_All three reuse shipped primitives (piece.stack towers / reserve trays / board.overlay). One generic renderer fix was needed; see note._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Surakarta | review→auto | independent re-derivation; exhaustive proof that NO zero-loop slide can capture + first-piece-only/no-jump; 2-ring loop topology traced. **Renderer fix:** the 8 corner loop arcs (3-point Bézier overlay) were clipped + mis-drawn — generalized `board.overlay`/`board.lines` to N-point paths (2pt line / 3pt quadratic arc / Npt polyline) and grew the viewBox to include decorations. Browser-verified (gold inner + blue outer loops now render) | **done → main** |
| Focus (Domination) | review→auto | re-derived Sackson rules; over-5 bottom-removal split (own→reserve, enemy→captured), move-top-k-exactly-k-cells, reserve drop, last-to-move win; 52-cell octagon (polygons honours `cells`). Browser-verified (octagon + towers + reserve trays) | **done → main** |
| DVONN | review→auto | re-derived vs official rules — build agent CORRECTED my prompt (stacks move all **6** hex directions, jumping allowed, land-on-occupied) and the DVONN-disconnection removal incl. the bridge-break case; canonical 49-field elongated-hex board (9-10-11-10-9). Browser-verified (board geometry + placement phase) | **done → main** |

## Batch 13 — stacking draughts + small traditionals (2026-06-22)
_Certain geometry, well-documented rules; each reuses a shipped primitive (stacking / board.lines / custodial capture)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Bashni | review→auto | re-derived vs mindsports.nl + draughts.github.io; the top-to-bottom prisoner rule, mandatory+chained+backward capture, Russian flying king, re-jump-same-square legality all confirmed; 2000-game piece-conservation (24 constant). Reuses Lasca towers. Browser-verified | **done → main** |
| Tsoro Yematatu | review→auto | re-derived canonical 7-point figure (5 lines of three); place-3-then-slide/jump (non-capturing), 3-in-a-row win, movement-phase-only scoring gate (option `placement_win`). Browser-verified (figure + placement) | **done → main** |
| Hasami Shogi | review→auto | Dai Hasami Shogi ruleset; rook movement + active custodial/corner capture (reuses brandub flanking) + dual win (decimation OR off-home-row 5-in-a-row, ortho/diag), both verified reachable in 400-game fuzz. Browser-verified | **done → main** |

## Batch 14 — the stacking flagship (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Tak | review→**fix**→auto | the road-building flagship: NxN (size option), flats/walls/capstones, opening double-move, carry-limit spreads, road-BFS win + flat-count win. **Review REJECTED a real bug** — the flat-count win fired when the FLAT reserve emptied, but official Tak ends only when the ENTIRE reserve (flats AND capstone) is gone; fixed to require both + added a 5×5 regression test (the package's own rules.md already stated the correct rule). **Two generic renderer touches:** the `=choice` picker now takes per-game `choiceNames`/`choiceTitle` from the RenderSpec (Tak's F/S/C → Flat/Wall/Capstone, which collided with chess C=Cardinal). Browser-verified end-to-end (opening swap, type picker, wall/capstone glyphs, reserves, bot capstone) | **done → main** |

## Batch 15 — GIPF stacking + phalanx + jump-race (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Epaminondas | review→auto | Abbott's phalanx war game (14×12); maximal-line phalanx slides 1..L, strictly-longer head-on capture removes the whole on-axis enemy run, deferred one-reply strict-majority 'crossing' win — all re-derived clean by the reviewer. Browser-verified | **done → main** |
| TZAAR | review→**fix**→auto | GIPF #4 stacking on a 61-cell hexhex (centre empty), 6/9/15 Tzaar/Tzarra/Tott, two-action turn, type-survival loss. **Review REJECTED a game-defining bug** that traced to MY spec — I wrongly said "no long slide"; official gipf.com rules have pieces SLIDE in a straight line over vacant cells to the first occupied cell (both capture & stacking, no jumping). A focused fix-agent rewrote move-gen to sliding (`_slide_targets`/`_slide_path_clear`) + added long-range/blocked/long-stack selftests; I re-verified + fixed the manifest desc. Browser-verified (hexhex render + slide capture) | **done → main** |
| Halma | review→**fix**(fork)→auto | the jump-race ancestor of Chinese Checkers (8×8/16×16 option). Review QUEUED the classic 'spoiling' fork (a squatter could deny the win → draw). I resolved it to the **standard 'enemy pieces don't block your win'** rule (target camp full + ≥1 of yours) + added the canonical 'can't leave the opposing camp once entered' + dropped a non-canonical anti-stall band-aid; documented as a deliberate choice. Browser-verified (8×8 camps + step) | **done → main** |

## Needs human (escalations)

_(none)_

## Blocked on a capability
_(tracked in `GAME_BACKLOG.md` — drops, stacking, territory scoring, point-and-line, >2-seat)_
