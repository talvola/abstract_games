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

## Batch 16 — clean square-grid abstracts (2026-06-22)
_All three auto, certain geometry, no renderer change._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Ataxx | review→auto | 7×7 expansion/infection; grow(clone, dist-1) vs jump(relocate, dist-2), 8-way infect-on-land, most-pieces win; reviewer confirmed the end-and-count vs award-empties fork never diverges in 300 games. Browser-verified | **done → main** |
| Teeko | review→auto | Scarne 5×5; drop-4-then-slide, win = line-of-4 OR 2×2 square (44 win shapes, all re-derived). Browser-verified | **done → main** |
| Squava | review→auto | 5×5 misère hybrid (placement only): four-in-a-row WINS, three-in-a-row LOSES, four-takes-precedence, full-board draw. Browser-verified | **done → main** |

## Batch 17 — custodial + knight-race + linear draughts (2026-06-22)
_All three auto, certain geometry, no renderer change._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Mak-yek | review→auto | Thai/Cambodian (Apit-sodok) 8×8; rook move + BOTH active capture modes — custodial flanking AND intervention (land between two enemies takes both); annihilation win; first/third-rank setup. Browser-verified | **done → main** |
| Jeson Mor | review→auto | Mongolian 9×9 all-knights; (1,2) leaper, capture-by-landing, win by occupy-then-VACATE the centre (4,4) (tinted); implemented directly (not ChessLike — no king/check). Browser-verified (knights + center tint + move) | **done → main** |
| Dameo | review→auto | Freeling 8×8 all-squares draughts; the build agent cross-checked mindsports.nl and correctly implemented the faithful LINEAR move = a connected file shifts exactly ONE square (I'd mis-specified "any distance"), forward man-steps, mandatory+maximal+chained orthogonal capture w/ end-of-move removal, flying kings; canonical triangular 18-man wedge setup. Browser-verified (wedge + linear move) | **done → main** |

## Batch 18 — Conway jump-game + pro-Gomoku + hex escort (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Phutball (Philosopher's Football) | review→auto | Conway's jump-to-goal: neutral shared men + one ball, place-a-man-OR-ball-jump-chain, jumps remove the leapt men, win by the ball reaching/crossing your goal line. Build agent modeled the unbounded chain as repeated single hops + a "stop" action (Oust-style multi-action turn) to avoid combinatorial blowup — rule-equivalent. 15×19 board, goal tints, ball glyph 'O'. Browser-verified | **done → main** |
| Renju | review→**fix**→auto | pro-Gomoku 15×15 with Black handicap (exact-five only for Black incl. no-overline, double-three/double-four/overline forbidden losses, White unrestricted). **Review REJECTED a game-breaking bug** — a STRAIGHT FOUR was miscounted as an open three, so Black's key 'four-three' winning tesuji was wrongly ruled a forbidden double-three loss; a fix-agent corrected `is_open_three_in_dir` (exclude run≥4 + require the dev point to extend THIS three) + added a four-three regression test. Deeply-nested RIF open-three recursion remains a documented approximation. Browser-verified | **done → main** |
| Agon (Queen's Guard) | review→auto | Victorian hex escort on a hex-of-hexes (side 6, 91 cells); inward/sideways-only movement, custodial send-to-outer-ring capture, win = Queen on the throne ringed by all 6 own guards; re-derived vs Wikipedia. New board shape — browser-verified (throne tint + Q glyphs + inward move) | **done → main** |

## Batch 19 — mancala + two race games (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Toguz Kumalak | review→**fix**→auto | Kazakh 2×9 sowing mancala; leave-one-behind, even-count capture, the full tuzdik (sacred-hole) rule + its 3 restrictions, >81 win. **Review caught an end-game bug** — remaining board balls weren't swept to each side's kazan at game end (could flip the winner); fix-agent added the own-side sweep + regression test. Browser-verified (capture fired: 10–10). Reuses the Kalah/Oware pit render | **done → main** |
| Gygès | review→auto | Leroy's ownerless 6×6 height-race; pieces (height 1/2/3, no owner) move exactly their height in steps, bounce/replace on landing, win by reaching your goal cell; re-derived vs the official Leroy PDF. Reuses Lasca height glyph. Browser-verified | **done → main** |
| Conspirateurs | review→**fix**→auto | French Halma-style step-and-jump race, 17×17. **My spec was WRONG** (I said queen-move/no-adjacent) — the build agent verified 4 sources and built the REAL game (step + jump, no capture, shelter all your men in the perimeter sanctuaries). Review then caught MEN=21 (should be 20 in play; 21 cones = 1 spare) — fixed to 20. Sanctuary map is a documented 40-cell reconstruction (exact published coords unrecoverable). Browser-verified (0/20 + sanctuary tints) | **done → main** |

## Batch 20 — render-primitive investments (rings/markers → YINSH) (2026-06-22)
_Erik asked to build the 3 deferred render primitives in order: **rings/markers → YINSH** (this), then nesting → Gobblet, then shrinking board → ZÈRTZ._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) ring/marker glyphs** | — | generic `piece.shape` = `ring` (hollow, +optional `inner` marker + `label`) / `marker` (small disc) in the RenderSpec; documented in SPEC.md; all 97 prior games render byte-identical | **done → main** |
| YINSH | review→auto | GIPF #5; 85-point hex lattice (cols 4-7-8-9-10-9-10-9-8-7-4, 3 line families) — geometry verified vs the sharkdp/yinsh reference + gipf.com; 5 rings/side, place-marker-then-slide-ring with jump-and-flip, ring-blocking, row-of-5 removes 5 markers + 1 ring, win = remove 3 rings. First consumer of the ring/marker primitive. Browser-verified (85-pt board + hollow ring glyph render). NOTE: MCTS bot is slow on the 85-pt board (generic large-board perf, not a bug) | **done → main** |

## Batch 21 — render-primitive 2 (nesting → Gobblet) (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) piece.size nesting** | — | generic `piece.size` (disc scaled by size; emit only the top cup) + DROP_RE widened to accept a digit reserve key (`4@c,r`) so the reserve-chip drop flow works for sizes; documented in SPEC.md; backward-compatible (Crazyhouse letters still match) | **done → main** |
| Gobblet | review→auto | Denoual/Blue Orange; 4×4, 3 off-board nested stacks of cups (sizes 1-4), strictly-larger gobble, off-board-gobble-only-on-a-3-line restriction, uncovering reveals the cup beneath, win = 4 same-colour tops in a line (incl. uncover-loss); + a 3×3 'Gobblet Gobblers' `size` option. Verified vs the Blue Orange rulebook. First consumer of the nesting primitive. Browser-verified (sized cups render + reserve-tray drop + nested stacks update) | **done → main** |

## Batch 22 — render-primitive 3 (shrinking board → ZÈRTZ) · 100 GAMES (2026-06-22)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) shrinking board + marble fill** | — | `board.extent` pins the viewBox so a board can shed cells without rescaling; `piece.fill`/`piece.stroke` give a piece an explicit (non-seat) colour. Documented in SPEC.md; backward-compatible | **done → main** |
| ZÈRTZ | review→**fix**→auto | GIPF #2; 37-ring hexagon that SHRINKS (rendered as `polygons` so removed rings vanish + `board.extent` keeps it stable — the hex renderer ignores a cell list), shared 6W/8G/10B neutral marble pool (`piece.fill`), place-marble-then-remove-free-ring, mandatory chained jump-capture into your reserve, isolation capture, win = 3-of-each / 4W / 5G / 6B. **Review caught a real bug** — isolation only fired on ring-removal, not when a placement fills an isolated group's last vacancy with no free ring removable; fix-agent added the placement-path isolation (with a `prev` guard so pre-existing islands aren't re-swept) + regression test. **Also a render-only UX fix:** exposed the shared pool as the mover's armable reserve tray (placement was unplayable — the pool had no clickable source), captured marbles → caption. Browser-verified (board shrinks with gaps, 3-colour marbles, pool placement + ring removal) | **done → main** |

_All three deferred render primitives (rings/markers, nesting, shrinking-board) now shipped — 100 games._

## Batch 23 — distinct drop-ins on existing primitives (2026-06-23) · 103 games
_Built under a sustained Anthropic API 529-overload — handled by hand (see note)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Quixo | hand-built→auto | Gigamic 5×5 take-a-border-cube-stamp-and-slide; win = five of your symbol, opponent-completion hands them the win. I WROTE this package by hand (the build agent kept 529-ing); slide/win baked in selftest. Browser-verified (slide picker via `=CHOICE`, slide renders). Fixed U/D picker labels for the renderer's y-flip | **done → main** |
| Kamisado | agent-build→**self-verified**→auto | Burley 8×8 colour-chain race; Latin-square colour board (`board.tints`) + 8 colour towers (`piece.fill`), forward-only slide, colour dictates the opponent's next tower, official deadlock rule, reach-far-row win. Verify agent died on 529 → I did the independent adversarial review myself. Browser-verified (colour board + colour-chain). **Renderer fix:** a piece with both `fill`+`label` (a tower on its own-colour cell) was invisible (label-only in the fill colour) → now drawn as a disc + contrasting-outline label | **done → main** |
| Battle Sheep | agent-build→**self-verified**→auto | Blue Orange split-and-slide on a fixed 32-hex board; split a stack (leave ≥1), slide as far as possible, most-hexes win (tie-break largest herd). Verify agent died on 529 → self-reviewed. Reuses `piece.stack`. Browser-verified (hex stacks + split via count picker) | **done → main** |

_Note: a multi-hour Anthropic API 529 overload killed build/verify subagents repeatedly. I backed off + resumed (cached builds), wrote Quixo by hand, and did the independent rule-review for Kamisado/Battle Sheep myself (a valid second reviewer) — all 3 also browser-verified._

## Batch 24 — the GIPF namesakes (2026-06-23) · 105 games
_Completes the realistically-addable GIPF project (DVONN, TZAAR, YINSH, ZÈRTZ already in). TAMSK is real-time sand-timers → not implementable in a turn-based engine (skipped). "Potentials" (the cross-game meta-layer) deliberately NOT done — it couples games and breaks the independent-module design; each GIPF game ships standalone._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| GIPF | review→auto | the namesake (basic game): radius-3 hex of 37 spots + 24 entry dots, introduce-from-reserve-and-shove inward, 4-in-a-line removal (own pieces → reserve, opponent's captured out), lose on empty reserve. Geometry + rules verified vs gipf.com/Rio Grande. Reserve tray + hex board.lines. Browser-verified (board + shove). GIPF-pieces/doubles variant documented out-of-scope | **done → main** |
| PÜNCT | review→auto | GIPF #6 connection+stacking: 211-field side-9 hexagon, 18 triomino pieces (straight/angular/triangular) placed flat or stacked (bridging/support rules), connect a pair of opposite edges (Hex-style BFS over top colour). Rules verified vs gipf.com/UltraBoardGames. Rendered PER-FIELD (a 3-field piece = 3 same-colour discs + height label) — no multi-cell-piece primitive. Browser-verified (211-hex board + triomino placement). **Documented base-game limitations:** placement is offered as an action-button LIST (the P/A/B move notation isn't cell-clickable) — a future click-to-place-triomino + shape-outline UI would improve it; rotate-in-place omitted (PÜNCT must slide ≥1); shapes tracked as a count not a 6/6/6 split; standard PÜNCT-marker/central-control out of scope | **done → main** |

## Batch 25 — stacking-draughts + 2 modern abstracts (2026-06-23) · 108 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Emergo | review→auto | Freeling stacking draughts on the 41 dark squares of 9×9; off-board ENTRY phase (drop men, then all-remaining-as-one-column), no kings, omnidirectional single-step, mandatory+maximum chained capture with the jumped TOP man tucked UNDER the mover (Lasca model), capture-all win. rules.md documents how it differs from Lasca/Bashni (entry phase, kingless, max-capture, capture-all). Browser-verified (entry drop). | **done → main** |
| Trike | review→auto | Erickson 2020, side-11 triangular hex board, ONE shared neutral pawn; move the pawn in a straight line over empty cells + drop your stone on the landing; ends when the pawn is trapped; winner = majority of stones on the pawn's cell + its neighbours (pie/swap supported). Verified vs the Kanare/Erickson rulebook. Reuses triangular polygons. Browser-verified | **done → main** |
| Tumbleweed | review→**fix**→auto | Zapawa modern hex influence game (side-8 hexhex); place a stack of height = your line-of-sight count, strictly greater than the target. **Review caught a scoring bug** — it counted only OCCUPIED hexes, but Tumbleweed scores 'owned + controlled' (every empty cell goes to the player with strictly-greater LOS) — wrong winner in ~every game; fix-agent rewrote `_control_counts` to the owned+controlled territory score + a winner-flip regression test. Browser-verified (territory score updates live: 27-27 → 42-23 after a placement). | **done → main** |

## Batch 26 — modern hex abstracts (2026-06-23) · 111 games
_All three on a side-5 hex-of-hexes, reusing the hex renderer + line/Go-liberty/group machinery; all auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Yavalath | review→auto | Cameron Browne / LUDI 2007 — the hex analogue of Squava: place stones, 4-in-a-row WINS, exactly-3 LOSES, four-takes-precedence; full board = draw. Optional pie/swap. Browser-verified | **done → main** |
| Pentalath | review→auto | Browne (Ndengrod): 5-in-a-row on a hexhex WITH Go-style group capture (zero-liberty enemy groups removed, no suicide, edge gives no liberty — verified vs cambolbro.com); reuses the Go liberty core. Browser-verified | **done → main** |
| Catchup | review→auto | Nick Bentley: place 1 (first move) then 2, or 3 when catching up (opponent's last turn grew/tied the largest group AND is ≥ yours); fill the board, score = largest connected group (tie-break next-largest…). Browser-verified | **done → main** |

## Batch 27 — custodial + connection + dice (2026-06-23) · 114 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Seega | review→auto | Egyptian custodial-capture; 5×5 (5/7/9 option), 2-stones-per-turn placement w/ empty centre, then orthogonal single-step movement, active custodial capture, safe centre, reduce-opponent-below-2 / blockade win. Three source-ambiguities (first mover, single-move, blockade=loss) flagged in rules.md. Browser-verified (placement + marked centre) | **done → main** |
| Slither | review→**doc-fix**→auto | Clark 2010 connection, 8×8 (size option). **Build agent caught that my brief INVERTED the rules** and built the REAL published game (no-bare-diagonal restriction + ORTHOGONAL connection win + optional king-step slide then place). Review QUEUED on an undocumented termination deviation (real Slither passes on no-move + can't draw; we use no-move=loss + ply-cap-draw to guarantee termination) — I documented it in rules.md as a flagged platform termination choice → auto. Browser-verified | **done → main** |
| Cephalopod | review→**fix**→auto | Steere dice-capture majority, 5×5; place a die, must-capture an adjacent set summing ≤6 (die shows the sum) else a "1", board fills, dice majority wins. **Review caught a termination bug** — the ply cap (4·cells) fired BEFORE the board filled (a capture frees cells, so filling needs ~165 plies on 5×5), scoring a partial board in ~100% of games; fix-agent set is_terminal=board-full + a safe high backstop + a full-game regression. Browser-verified (dice pips render, games now fill: avg 136 moves) | **done → main** |

## Batch 28 — CGT classics + a hunt (2026-06-23) · 117 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Domineering | review→auto | Berlekamp-Conway-Guy domino game; 8×8 (size option), Vertical vs Horizontal dominoes, last-to-place wins. Anchored by small-board CGT outcomes (full-search-verified: 1×1/2×1 mover loses, 2×2/3×3/4×4 first-player wins; both reviewer + build independently minimaxed). Browser-verified (V/H dominoes render distinctly) | **done → main** |
| Col | review→auto | Vout's map-colouring game; 5×5 (size option), place your colour not orthogonally adjacent to your OWN colour, last-to-move wins. Reviewer cross-checked legal-move gen over 3000 self-play games. Browser-verified | **done → main** |
| Hare and Hounds | review→**fix**→auto | Soldier's Game on the 11-point board (3×3 + L/R apexes, central-X diagonals); 3 hounds (no-retreat) vs 1 hare; hounds trap-win, hare escape/stall win. **Review caught the stalling rule was DEAD CODE** (the counter reset on every hare move, so it could never reach the threshold in alternating play); fix-agent made it count consecutive non-advancing HOUND moves not reset by the hare + a real alternating-play regression. Browser-verified (no-retreat hound move) | **done → main** |

## Batch 29 — CGT pair + a mancala (2026-06-23) · 120 games
_All auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Snort | review→auto | Norton's CGT game, the exact dual of Col (place not-adjacent-to-OPPONENT's-colour, last-to-move wins); differentially checked vs the col package. Browser-verified | **done → main** |
| Cram | review→auto | impartial domino game (both orientations, either player), last-to-place wins; build agent corrected my wrong parity-anchor (only both-even→2nd-player holds; 3×3 is a 2nd-player win) and baked full-search small-board outcomes (both build + reviewer minimaxed). Browser-verified | **done → main** |
| Congkak | review→auto | Malay mancala (2×7 + 2 stores, 98 seeds); sow incl. own store/skip opponent's, relay-on-occupied continuation, extra-turn-on-store, own-empty-hole capture; distinct from Kalah/Oware/Toguz (relay + end condition). Browser-verified (sow + store + extra turn) | **done → main** |

## Batch 30 — African capture + connection + attribute-matching (2026-06-23) · 123 games
_All auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Dara | review→auto | West African (Derrah) 2-phase: place 12 each (no scoring threes), then orthogonal slide; form EXACTLY-3 (4+ forbidden) to remove an enemy; anti-shuffle (no immediate re-form); win = opponent below 3. 6×5 default + 6×6/7×6 options (board-size source-ambiguity flagged). Reuses morris place+line+capture. Browser-verified | **done → main** |
| Bridg-It | review→auto | Gale / Shannon switching game; two interleaved 5×6/6×5 dot lattices, draw a unit edge between your dots, no crossing the opponent's edge, connect your two sides (BFS); no draws (verified 2000+ games). Edges rendered via `board.overlay`, dots via `piece.fill`. Browser-verified (edge segments draw correctly) | **done → main** |
| Quarto | review→auto | Gigamic attribute game; 16 pieces × 4 binary attributes (code e.g. SDQF), the signature place-the-piece-your-opponent-gave-you-then-give-one turn (first move give-only); win = a line of 4 sharing any attribute. Win-detection exhaustively checked vs brute-force oracle (0/1820 mismatch). Neutral pieces shown by code label + in-hand piece in reserve tray. Browser-verified | **done → main** |

## Batch 31 — unusual-board traditionals (2026-06-23) · 126 games
_All auto._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Kaooa | review→auto | Indian "vultures & crows" hunt on a 10-point PENTAGRAM ({5/2} star — adjacency derived geometrically); 1 vulture vs 7 crows, crows place then slide, vulture steps/jumps (draughts-style, active during placement), vulture wins at 4 captures / crows win by trapping. Browser-verified (star board + crow placement) | **done → main** |
| Achi | review→auto | Ghanaian 3×3 alignment with 8 lines; FOUR pieces each (vs Tapatan's 3), place all 8 then slide to the single empty point, three-in-a-row wins. Reuses morris place+line. Browser-verified | **done → main** |
| Pah Tum | review→auto | ancient grid run-scoring; 7×7 (9×9 option) with a fixed symmetric set of BLOCKED cells, place until full, score escalating runs of ≥3 (3→3,4→10,5→25,6→56,7→88), most points wins. Blocked cells via `board.tints`, running score in caption. Browser-verified | **done → main** |

## Batch 32 — CGT + medieval + Kenyan alignment (2026-06-23) · 129 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Clobber | review→auto | Albert/Grossman/Nowakowski CGT game; checkerboard-filled grid (5×6 default), move onto an orthogonally-adjacent ENEMY (clobber it), last-to-move wins. Small-board outcomes independently minimaxed (1×2/1×3/2×2/3×3 P1-win, 2×3 P2-win). Browser-verified (`0,0x0,1`) | **done → main** |
| Camelot | review→**fix**→auto | Parker Bros medieval on the 160-square cross board + 2 castles; 4 knights+10 men/side, PLAIN/CANTER/JUMP + Knight's Charge, win by 2-men-into-enemy-castle or annihilation. Build agent fixed my brief (jumping is COMPULSORY per WCF, not optional). **Review caught jump-continuation not enforced** (premature-stop jumps offered as legal) → fixed to emit only continuation-maximal chains (branching preserved) + regression. Browser-verified (cross board + castles render, `C6-C5`) | **done → main** |
| Shisima | review→auto | Kenyan octagon (8 rim + centre, rim ring + 4 diameters); 3 pieces each, slide to adjacent empty point, three-in-a-row THROUGH THE CENTRE wins. Reuses tapatan slide+line on the octagon graph. Browser-verified (octagon board, `point 2->point 3`) | **done → main** |

## Batch 33 — Korean/Asian traditionals (2026-06-23) · 132 games
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Four Field Kono | review→**fix**→auto | Korean 4×4 (full board start); capture by jumping over your OWN piece onto an enemy beyond. **Review caught my spec was over-restrictive** (capture-only degenerated to ~6 moves) → fix-agent added the standard non-capturing orthogonal slide-to-empty; now avg 126.9 moves, win = no jump AND no slide. Browser-verified (`a1xa3`) | **done → main** |
| Five Field Kono | review→auto | Korean 5×5 race; 7 pieces each (back row + 2 outer second-row), move one step DIAGONALLY to empty, first to occupy the enemy's home set wins. Browser-verified (`0,0→1,1`) | **done → main** |
| Pong Hau K'i | review→auto | Chinese/Korean 5-point blocking game; canonical 5-node/7-edge graph (centre↔4 corners, bottom edge, NO top edge), 2 pieces each, slide to the single empty point, no-move loss; perfect-play DRAW value confirmed. Board via points+`board.lines`. Browser-verified (`tl->c`) | **done → main** |

## Batch 34 — fighting-serpents + Othello-Go + circular (2026-06-23) · 135 games
_Two render-format bugs caught only in-browser (validate/selftest can't see the JS renderer) → SPEC.md now documents the exact `polygons` cells format._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Awithlaknannai Mosona | review→auto→**render-fix** | Zuni "fighting serpents" — 25-point elongated serpent lattice, 12v12, slide or mandatory chained jump-capture (Alquerque-style), capture-all win. Auto on logic; **browser-verify caught the render crash** (cells used key `polygon` not `points`) + a cosmetic describe_move mislabel — both fixed. Browser-verified (serpent board, `7,2-8,1` step / `9,0x7,2` capture) | **done → main** |
| Sygo | review→auto | Freeling's Othello/Go hybrid — build agent corrected my premise (it's GO with "othelloanian capture": a group losing its last liberty FLIPS to the captor's colour, not removed); empty board, no-suicide, territory majority. Single-stone-per-turn simplification (vs the grow-all turn) flagged. Browser-verified (`W:E15`) | **done → main** |
| Pretwa | review→**fix**→auto→**render-fix** | Indian concentric-circle board (3 rings × 6 spokes + centre = 19 pts), 9v9, step/chained-jump-capture. **Review caught win/draw logic** (win at opp≤3 not ≤2; no-move resolves by piece-majority not auto-loss) → fixed. **Browser-verify caught the render crash** (cells emitted as a dict not a list) → fixed. Browser-verified (concentric board, `1,0-0,0`) | **done → main** |

## Focused build — Gess (2026-06-23) · 136 games
_First post-roadmap "distinct focused build" (Camelot-style: one build agent + one independent rule-verify agent + browser-verify) — Erik's pick over continued incremental mining. No new render primitive._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Gess | build→independent-verify(**MERGE**)→browser→doc-fix | The Archimedeans (Cambridge, 1994) Go+chess hybrid: 3×3 "footprint" pieces of your own stones on the 18×18 inside a 20×20 grid; outer cells set move directions (corner=diagonal/edge=orthogonal), center sets range (filled=unlimited/empty=max-3); rigid slide stops at the first stone & captures the whole destination 3×3 (self-capture incl.); border = kill-zone; win = make opponent ringless (ring = 8 stones around an empty center; **multi-ring** rule, mutual-ringless→mover loses). `square` 20×20 (no new primitive), border tinted; move = center→center `cx,cy>dx,dy` into the two-click UI (empty ring-center is a clickable source). Independent verifier (different agent) confirmed every contested rule vs Wikipedia / red-bean SGF spec / Archimedeans (incl. center-must-stay-inner, resolving the jpneto ambiguity for us) + pure apply_move + serialize round-trip; **verdict MERGE**, only a cosmetic "180°"→vertical-mirror doc nit (fixed). Browser-verified end-to-end (board renders, empty ring-center selects, footprint move applies, ring caption `B 1 / W 1`, move logged `l3-l5`). Anchor: pure-stdlib baked-rule selftest (no perft exists for Gess). House-rule draw caps (60-ply no-capture / 400-ply) added for termination, flagged non-original in rules.md | **done → main** |

## Deeper Gess testing + Ataxx hardening + Hexxagon (2026-06-23) · 137 games
_Erik asked for deeper Gess gameplay testing (he hasn't played, so can't eyeball rule bugs) and to add Ataxx (already shipped as #86) + Hexxagon. The deeper testing CAUGHT A REAL BUG._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Gess (bug fix) | gameplay-research→probe→**fix**→independent-re-verify(**CLEAN**) | A research agent pulled the original Archimedeans article's two worked example moves + the chess-piece opening move-sets; probing them found a **slide-through bug** — move-gen exempted the carried stones' PROJECTED cells from the collision check, so a leading carried stone could mask a blocker and the piece slid THROUGH it (illegal jump-over moves; opening inflated 735→ true **416**). Fix: exempt only the carried stones' SOURCE cells (`lifted`). A fresh independent agent re-verified **CLEAN** (no slide-through in any of 8 dirs for enemy/own blockers, single+multi-stone; path-walker confirmed no move passes its footprint over a stone). Selftest hardened: occupied-center masking regression + authoritative-opening chess-piece move-set anchors (rook=orth / bishop=diag / queen+king=all-8 / empty-center range-3 cap / pawn-pusher) + bishop-unlimited. **The first MERGE review missed it by sidestepping the masking case** — lesson: collision tests must use an OCCUPIED-center (unlimited-range) piece so the empty-center cap can't hide a slide-through | **done → main** |
| Ataxx (hardening) | verify-vs-canonical→**add auto-fill** | Existing #86 confirmed faithful to Wikipedia-canonical Ataxx (7×7, opposite-corner setup, grow=dist1/jump=dist2 Chebyshev, 8-nbr infection, pass-and-stop). Added the **arcade/video-game auto-fill-on-elimination** (a move wiping the opponent fills the board for the survivor) — outcome-identical on the holeless 7×7 but instant, and required for Hexxagon's hole board. Guarded on "opponent had pieces before" so synthetic one-colour test positions don't trip it | **done → main** |
| Hexxagon | build→independent-probe-verify→browser | Hex Ataxx: side-5 hexhex (61 cells, axial q,r) − 3 central holes (3-fold-symmetric default (1,0)/(-1,1)/(0,-1); option holes=standard\|none) = 58 playable; 2 players × 3 pieces on alternating corners (each opposite an enemy); grow=hex-dist-1 (6 nbrs)/jump=hex-dist-2 (12-ring), 6-nbr infection, holes never targetable, auto-fill-on-elimination, most-pieces win (tie possible, 58 even). Reuses Ataxx logic + Havannah hex render (`type hex`/`shape hexagon`/`size 5`) + Pah-Tum-style tints for holes. Orchestrator did the independent probe-review (28 checks: geometry, distances, corners, mechanics, holes, auto-fill all pass). **Browser-verified** (hexhex + dark holes render — the untested hex+tints combo works — grow move applies, count 3→4, `R:grow 3,0`). Pure-stdlib selftest | **done → main** |

## Santorini (2026-06-23) · 138 games — NEW render primitive
_Erik's overnight queue item #1. Needed a new generic render primitive first (per-cell build height = two-things-per-cell)._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| **(primitive) board.levels height** | — | generic `board.levels = {cellId: 1..4}` in Board.jsx — per-cell build height drawn as stacked wedding-cake tiers (1-3) + a blue dome cap at 4 + a height badge, *under* the worker piece (two-things-per-cell). Documented in SPEC.md; opt-in, all 137 prior games byte-identical | **done → main** |
| Santorini | build→independent-verify(**MERGE**)→browser | Roxley base game (no god powers). 5×5, 2 workers/side, placement [0,0,1,1], turn = MOVE (≤1 up / any down, not onto worker/dome) THEN BUILD (+1 level, L3→dome) with the same worker; win = MOVE up onto a level-3 building (2-cell climb, no build) or opponent stuck. Move = `wfrom>wto>build` 3-cell path (winning climbs are 2-cell). First consumer of `board.levels`. Independent verify MERGE (placement, ≤1-up, mandatory-build, climb-only-by-moving, stuck-loss, 300 random games terminate). **Browser-verified** end-to-end: placement, the 3-click move→build flow, and all four height visuals (tier-1 badge → 3 nested tiers → dome). New "Build & climb" category. Pure-stdlib selftest | **done → main** |

## Hexxagon 3-player (2026-06-23) · 139 games
_Erik's overnight queue item #2._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Hexxagon (3-player) | build→independent-probe-verify→browser | Separate package `hexxagon3` (num_players fixed=3). Same side-5 hexhex − 3 holes; 6 corners owned P0,P1,P2,P0,P1,P2 (each player 2 opposite corners, 2-2-2 start). Grow/jump/holes identical; infection flips ANY adjacent opponent (either other colour); turn cycles 0→1→2 skipping eliminated/stuck; last survivor auto-fills+wins; returns = 3-vector matched to Rolit (sole leader +1, others −1, lead-tie=0). Reuses hexxagon geometry + Rolit multi-seat returns/cycling. Probe-verified (corner alternation, 3-way infection, skip-eliminated, last-survivor [1,−1,−1]). **Browser-verified** (3 distinct seat colours Red/Blue/Green, alternating corners, grow → turn advances Red→Blue, 3-2-2). Pure-stdlib selftest | **done → main** |

## Batch 35 — GAME_BACKLOG mining, famous Tier-0 (2026-06-24) · 141 games
_Erik's overnight queue item #4: work through GAME_BACKLOG.md with the same gate. Targeting famous/distinct unbuilt Tier-0 games._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Abalone | build→independent-verify(**MERGE**)→browser | The 1987 marble-pusher. Side-5 hexhex (61 cells), 14 marbles/side STANDARD start (5+6+3 wedge, point-symmetric — not Belgian Daisy). In-line 1/2/3 group slides + SUMITO push (2v1/3v1/3v2, empty/off-board behind → edge ejection) + 2/3 broadside; win = eject 6. ANCHOR: **opening = 44 moves** (published branching factor). Independent verify MERGE (sumito + edge-eject + illegal-pushes-absent + group-integrity + broadside + win-at-6 all probed). Browser-verified (standard position on the hexhex, single-marble move). KNOWN UX: 2/3-marble GROUP moves have a clunky multi-cell click path (documented, like PÜNCT/Tsoro). Reuses Havannah hex render; no new primitive | **done → main** |
| Chess960 (Fischer Random) | build→probe-verify→browser | Randomized back rank (Scharnagl id→rank, stored in C9State.homes, has_randomness) with bishops-opposite / king-between-rooks / mirrored; new Chess960Castling (by king/rook FINAL squares, KING-CAPTURES-OWN-ROOK input). ANCHOR: std chess = #518 → perft 20/400/8902/197281 (move-gen unchanged); build agent's differential test = same reachable positions as `chess` over 60×45 incl. castling. Probe-verified 200-seed constraints + castling on non-standard ranks. Browser-verified (randomized board renders + plays; castling headless-verified). On agp.chesslike | **done → main** |
| Martian Chess | build→probe-verify→browser | Looney Pyramids zone-ownership chess. 4×8 board, canal splits two 4×4 zones; Pawn(diag-1)/Drone(ortho-1/2)/Queen(any-line); ownership = zone a piece is currently in (a piece crossing the canal becomes the opponent's); capture scores Q3/D2/P1 to mover; field-merge + no-take-back + tie-break; zone-empty end, most-points win. Probe-verified (zone-ownership, cross-canal scoring, zone-empty end; opening=5 hand-checked). Browser-verified (4×8 + 2 tinted zones + P/D/Q labels; drone crosses canal red→blue). Pure-stdlib selftest | **done → main** |
| Knightmate | build→**brief-corrected**→probe→browser | Bruce Zimov's royal-knight chess on agp.chesslike. King→Royal Knight (knight moves, IS royal); knights→Commoners (king moves, non-royal/capturable); back rank R·C·B·Q·K·B·C·R. Royalty wired by letter (K=royal knight, C=commoner). **Build agent corrected my brief** (Knightmate DOES castle — royal knight + rook; added KnightmateCastling disambiguating same-rank castle from the knight's 2-file rank-changing leap). Promote to Q/R/B/Commoner. ANCHOR perft 18/324/6765/139774. Probe-verified (royal-knight royal, perft d2=324). Browser-verified (setup renders). On agp.chesslike | **done → main** |
| Crossway | build→probe→browser + **renderer fix** | Mark Steere connection game (official PDF read). N×N (size 9/11/13/19, default 13); Black top↔bottom, White left↔right. The "no-crossing" rule is a PLACEMENT restriction (never complete the 2×2 BW/WB checkerboard) → no two opposite-colour diagonals cross; connectivity = plain 8-adjacency; can't draw (verified 60 games → always exactly one connector). Pie via "swap". Probe-verified. **RENDERER: extended the coloured goal-edge frame to SQUARE boards** (was hex-rhombus-only) → Crossway + the existing Gonnect now show goal sides; browser-verified both, no regression | **done → main** |
| Symple | build→**P-corrected**→probe→browser | Freeling/Rosenau group game. Odd square (19 default/13). Turn = place a NEW group (not adj to own) OR GROW all growable groups by 1 (bridging stone merges groups; no double-grow; surrounded skip); 2nd-player balancing grow+place. Score = stones − P·groups (**P = even const 4..12 default 8, corrected from my P=N guess** per mindsports.nl). Grow = multi-step same-player turn (action button → one cell/group → auto-end). Probe-verified (single+multi-group grow, merge). Browser-verified (score caption, the grow→cell→end flow, group grew −7→−6) | **done → main** |
| Irensei | build→**brief-corrected**→probe→browser | 囲連星 Go/Gomoku hybrid (19×19). Build agent corrected my brief: it's **SEVEN** in a row (not 5) in the central 15×15 (outer 2 lines excluded), Black exact-7 (overline-8 loses) / White ≥7; full Go captures + ko/superko + suicide-illegal-unless-winning; reuses the Go liberty core. Edge frame tinted (136 cells). Probe-verified (inner-7 wins, edge-7 doesn't). Browser-verified (19×19 + tinted edge). NOTE: validate slow (~2.5min, Go legality) but passes; suite uses fast frozen selftest | **done → main** |
| Meridians | build→**designer-corrected**→probe→browser | Kanare Kato 2021 (NOT Steere — agent found the real PDF). Centerless triangle-tessellated hexagon (2 short+4 long sides, **114 pts**; 80/154 size options). Turn = remove opp dead groups then place a stone in LINE OF SIGHT of a friendly (turn 2+); a group is alive iff a clear all-empty line reaches a DIFFERENT friendly group; annihilation win. ANCHOR 114 opening moves (AiAi). Render polygons (matched nine_mens_morris, cells=LIST of {id,points}). Probe-verified (114 moves, polygons format correct). Browser-verified (asymmetric-hexagon triangular board renders, no white-screen) | **done → main** |
| Entropy | build→probe→browser | Eric Solomon order-vs-chaos (7×7, 49 chips/7 colours). CHAOS draws a random chip (stored as next_tile, EinStein has_randomness pattern) + places; ORDER slides a chip ortho through empties (no jump) or passes; board fills → Order scores all length-≥2 palindromic runs (=length, overlaps count, RRR=2+2+3). Single-game adaptation of the 2-round match: Order wins if score>PAR=30 (documented). Tiles via piece.fill+label (not seat-owned). Probe-verified (next_tile, alternation, termination). Browser-verified (purple "F" chip renders, Chaos F@3,3, Order pass/slide turn) | **done → main** |
| Starweb | build→probe→browser | Christian Freeling 2017. Six-fold "web" board (hexhex-7 + a 15-cell triangular bump/side = **217 cells**, **18 stars** = 12 outward tips + 6 inward notches). Place/pass; group with n stars scores triangular n(n+1)/2; most points, DRAWLESS (tie→2nd). Pie/swap. Board geometry reconstructed from the official diagram + verified cell-for-cell vs a generative construction. Render polygons (matched battle_sheep), stars gold-tinted. Probe-verified (217 cells, 18 tints, drawless). Browser-verified (web board + six bumps + gold stars render) | **done → main** |
| Unlur | build→probe→browser | Jorge Gómez Arrausi 2001 asymmetric hex connection. Hexhex (6 default). BLACK wins by a chain touching 3 NON-ADJACENT sides (Y), WHITE by 2 OPPOSITE sides (line); SELF-LOSS = making the opponent's shape → DRAWLESS. The "contract" opening: both play black/pass; passer becomes Black, other White & moves first. Pie OFF. Render Havannah-style + board.tints alternating the 6 sides. Probe-verified (30 tints, contract→White, drawless). Browser-verified (alternating side tints + "Contract phase" caption render) | **done → main** |
| Storisende | build→probe→**QA-fix**→browser | Freeling 2018 territory/stacking (hexhex base 4). Stacks move/split by height (jump), merge/capture-by-replacement; vacating a virgin cell CRYSTALLISES it green (territory) or dark Wall; control a territory iff only you have men in it; most controlled cells wins. Render matches tumbleweed (stacks) + kamisado (tints). **DEEP-QA CAUGHT A REAL BUG:** literal "3-fold repetition = draw" made EVERY random/bot game a draw (a 16-0 board scored "Draw" — stacks shuffle, leader denied the pass-win) → fixed to resolve repetition/cap BY SCORE (tie still draws), flagged deviation; active play 0/40→40/40 decisive. Browser-verified (setup renders) | **done → main** |

## Batch 36 — Chess Variant Pages pool (2026-06-24) · 153 games
_Famous-distinct backlog drained; now mining CVP chess variants (reliable, perft-anchorable) + distinct abstracts._
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Maharajah and the Sepoys | build→probe→browser | Asymmetric: seat 0 = a lone AMAZON "M" (Queen+Knight, royal) on e1 vs seat 1 = a full Sepoy army with NO pawn promotion; sepoys move first. Both sides royal (overrode ChessLike `_royal_sq`: "M" for White, "K" for Black). Win = checkmate the enemy royal. ANCHOR opening 20. Probe-verified (Amazon = 8 knight jumps + queen rays, 1v16, two royals). Browser-verified (lone M vs full army renders). On agp.chesslike | **done → main** |
| Extinction Chess | build→probe→browser | Schmittberger "Survival of the Species". Standard chess BUT king not royal (no check/mate; moving into check legal); WIN by capturing ALL of any one enemy piece-type {K,Q,R,B,N,P}. On ChessLike: overrode `_legal` to drop king-safety, NoCheckCastling, promote-to-Q/R/B/N/K, extinction win as event. ANCHOR perft 20/400/8902/**197742** (d4 diverges from chess's 197281 → proves royalty filter off). Probe-verified (perft, last-knight-capture wins, into-check legal). Browser-verified (chess setup renders) | **done → main** |
| Almost Chess | build→probe→browser | Betza: queens → CHANCELLORS ("M"=R+N, reused from Grand Chess's Marshall) on d1/d8, else standard. ANCHOR perft **22**/484/11895/290522 (d1=22 not 20 — build agent caught that the Chancellor's knight leaps give 2 extra opening moves). Promote M/R/B/N. Probe-verified (no queen, Chancellor=rook∪knight no diagonals). Browser-verified (R·N·B·M·K·B·N·R renders). On agp.chesslike | **done → main** |
| Star | build→probe→browser | Schensted 1983 drawless connection-scoring. Hexagon with ALTERNATING-length sides (A5/B6 → 106 playing cells; odd perimeter → drawless) + 39 non-playable "partial hexagon" border cells (corner touches 3 / edge 2 / interior 0). Group touching ≥3 borders scores (borders−2); most points wins. Render polygons (145 cells, gold border tints). Probe-verified (106 cells, drawless 8/8). Browser-verified (alternating-side star board + gold border render). GOTCHA: search "Star" substring-matches "starts" in many descs → filter by Connection category to surface the right card | **done → main** |
| Andernach Chess | build→probe→browser | A CAPTURING piece changes to the opponent's colour (kings exempt); en passant flips; pawn-capture-to-last-rank promotes then flips. On ChessLike: one `_resolve` does move+capture+promo+flip, routed through BOTH `_legal` and apply (king-safety tested on the POST-FLIP board). ANCHOR perft 20/400/8902/197410 (d4≠197281). Probe-verified (capture flips W→B, king-cap doesn't, quiet doesn't). **Browser-verified the signature** (Pe4xd5 → the capturing White pawn became a BLACK pawn). On agp.chesslike | **done → main** |
| Poly-Y | build→probe→browser + **renderer fix** | Schensted/Titus polygonal Y. Pentagon of hexes (mudcrack-pie, 101 cells; 5 corners → DRAWLESS); corner owned via the Y connection-test (corner's 2 sides + any other side); majority of 5 wins. Verified every corner always resolves (25k random). Render polygons (5 gold corners). **RENDERER FIX (Board.jsx):** cell-move detection now keys off the real board cell-id SET (not the numeric "c,r" regex) → irregular polygons boards with LABELLED ids (Poly-Y "c"/"f,0,1,1", **Tsoro "0".."6"**) are click-to-place not a 101-button list. Browser-verified BOTH (Poly-Y click-to-place; Berolina/chess click-to-move still works = no regression) | **done → main** |
| Dunsany's Chess | build→**brief-corrected×2**→probe→browser | Lord Dunsany asymmetric: Black = full army (ranks 7-8), White = 32 pawns (ranks 1-4, no king). Agent corrected my brief twice (BLACK/pieces move FIRST; only Black's pawns double-step). White wins by mate, Black by capturing all 32 pawns (annihilation via returns, Horde-style). ANCHOR perft 20/166/3550/33601. Probe-verified (32 pawns, no White king, Black-first, white single-step-only, annihilation=[-1,1]). Browser-verified (32-pawn wall vs full army). On agp.chesslike | **done → main** |
| Cylinder Chess | build→probe→browser | The a/h files join into a vertical cylinder — sliders/knights/pawn-captures wrap (file mod 8); ranks don't wrap. On ChessLike: file-mod-8 geometry, rays capped at WIDTH-1 (no self-loop) + stop at first blocker + per-piece dedup; wrapped check; CylinderPawn diagonal-capture wrap; standard castling. ANCHOR perft 20/392/9162 (d1=20 — full back rank blocks wraps at start, agent corrected my d1>20; d2/d3 diverge). Probe-verified (rook/knight/bishop all wrap a→h, no loop). Browser-verified (8×8 renders). On agp.chesslike | **done → main** |
| Checkless Chess | build→probe→browser | Giving check is ILLEGAL unless it's checkmate. On ChessLike: after own-king-safety, remove any move leaving the opponent in check-but-not-mate (mate tested via the ordinary-chess reply gen → no recursion; mate = ordinary mate, documented). ANCHOR perft 20/400/**8890** (=8902−12, the 12 removed = non-mating depth-3 checks, verified). Probe-verified (non-mating check absent, mating check legal+wins). Browser/API-verified (32 pieces render). On agp.chesslike | **done → main** |
| ConHex | agent(session-limited)→orchestrator-verified→browser | Antonow 2002 two-layer connection. 41 cells (squares/pentagons/4 diamond corners) on 69 placement points; place a peg, own a majority of a cell's points → claim it; connect your two sides with a chain of owned cells (corners belong to both sides); drawless, pie. Render polygons (110 = 41 cells + 69 point markers); place-on-point click via the labelled-id renderer fix. **Agent completed but a session-limit cut its report → orchestrator verified** (validate OK, selftest OK, probe: polygons format/69 points/drawless 8-0, suite green). Browser-verified (concentric-ring board + points render) | **done → main** |
| Pocket Knight Chess | build→probe→browser | Standard chess + each side has ONE extra knight in pocket, droppable on any empty square once (may check/mate). On ChessLike: PocketKnightDrops(DropRules) — enabled, initial_hands {N:1}/side, captured_to_hand=None (no Crazyhouse banking → one-time). Reuses the reserve tray + "N@c,r". ANCHOR opening 52 (20+32 drops). Probe-verified (1 knight/side, drop empties hand, capture doesn't bank). Browser-verified (both reserve trays show the pocket knight). On agp.chesslike | **done → main** |
| Legan Chess | build→**setup-corrected**→probe→browser | Legan 1913 corner-to-corner chess. Armies in opposite corners (K h1/a8) behind diagonal pawn walls; LEGAN PAWN moves diagonally toward the enemy corner, captures orthogonally; promote at the corner edges; no castling/ep. Agent used the consistent Wikipedia point-symmetric setup (gambiter's was garbled). ANCHOR perft 8/64/724 (hand-verified d1=8). Probe-verified (corner kings, pawn diagonal-move/orthogonal-capture). Browser-verified (diagonal corner armies + pawn walls render). On agp.chesslike | **done → main** |

## Needs human (escalations)

_(none)_

## Blocked on a capability
_(tracked in `GAME_BACKLOG.md` — drops, stacking, territory scoring, point-and-line, >2-seat)_
