# Game Factory — Queue & Status

On-disk state for the autonomous game-integration loop (the "factory"). The
universe map and capability gaps live in `GAME_BACKLOG.md`; this file is the
*queue* and the *human-escalation digest*.

---

## ⭐ CATCH-UP DIGEST (read this first) — autonomous run of 2026-06-21

**Erik is away ~7h; the factory is running unattended.** This section is kept live
after every batch. Status as of the last update below.

- **Games on `main`:** 37 (session started at 24). Each new game = conformance +
  an independent rule-review, perft-anchored where a published number exists. All
  pushed to `origin/main`; the dev app is running so you can play any of them.
- **Merged this session (13):** King of the Hill, Three-Check, Tablut, Racing
  Kings, Makruk, Shatranj, Capablanca, International Draughts, Turkish Draughts,
  Havannah, Horde Chess, Antichess, Courier Chess. (Batches 1–4, all reviewed +
  merged under the option-1 gate.)
- **Quality signal:** the review caught a real bug in Courier Chess (the shared
  insufficient-material heuristic masking a K+2Manns-vs-K checkmate as a draw) —
  fixed before merge, not shipped. The gate is doing its job.
- **In flight:** batch 5 — Atomic Chess, Hnefatafl (Copenhagen 11×11), Konane.
- **⚠️ NEEDS YOUR DECISION:** _none right now._ Anything requiring a genuine
  ruleset call or a visual/UX check lands in **"Needs human"** below — check there.
- **Parked for you (not attempted unattended, needs UI + your eyes):** the
  capability investments from `GAME_BACKLOG.md` — drops (→ Morris/Crazyhouse/Shogi),
  stacking (→ Tak/DVONN), Go territory scoring, point-and-line boards, >2-seat UI.
  These touch the renderer/server, so I'm leaving them for when you're back.
- **How to review fast:** every game ships a one-page `rules.md` (rules as
  implemented, with any documented simplifications) and a `selftest.py` (its
  correctness anchor). `git log --oneline` shows the per-game merge rationale.

_Last digest update: after batch 4 merge (37 games). Updated again each batch._

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

## Needs human (escalations)

_(none)_

## Blocked on a capability
_(tracked in `GAME_BACKLOG.md` — drops, stacking, territory scoring, point-and-line, >2-seat)_
