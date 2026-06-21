# Game Factory — Queue & Status

On-disk state for the autonomous game-integration loop (the "factory"). The
universe map and capability gaps live in `GAME_BACKLOG.md`; this file is the
*queue* and the *human-escalation digest*.

## The gate (decided with Erik, 2026-06-20)

- **AUTO-MERGE to `main`** — `agp validate` green **AND** an *independent published
  anchor* matches (chess-family **perft**; a solved-game behavioural result). This
  is mostly the chess-variant family.
- **QUEUE for review** — `agp validate` green but correctness rests on an agent's
  reading of the rules (no published anchor), **or** a new board shape/rendering,
  **or** a documented-but-debatable ruleset. Held on a `factory/*` branch + listed
  under *Needs human* below.
- **BLOCKED** — needs a missing platform primitive (stacking, hand/drops, Go
  territory scoring, point-and-line edges, >2-seat UI). Deferred until built; see
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
| Tablut (9×9 tafl) | review | conformance + capture/escape positions; no published number | **review → branch `factory/batch-1`** |

Both auto games were independently re-verified (the verifier recomputed perft to
197281 at depth 4, matching standard chess) and re-checked by me before merge. The
factory's per-package `selftest.py` is run by the suite via `test_package_selftests`.

## Needs human (escalations)

**Tablut** — implemented, conformant, rules faithful, but held for your call on a
genuine ruleset choice (no published anchor to settle it). On branch
`factory/batch-1`; `git checkout factory/batch-1` to try it. Decide:
1. **Does the King help capture?** As built, the King is *not* a capturing anvil
   (a defender can't sandwich an attacker against the King). Many historical
   Tablut readings let the King assist. Pick one; it's a one-line change.
2. **Pass-over-throne:** as built, any piece may *pass over* (not land on) the
   empty throne; some rulesets forbid non-King pieces passing through. Documented.
3. King escape = **any edge square** (Linnaeus edge-escape) — confirm vs. a
   corner-escape variant if you prefer.
Tell me your choices and I'll finalize + merge, or merge as-is.

## Blocked on a capability
_(tracked in `GAME_BACKLOG.md` — drops, stacking, territory scoring, point-and-line, >2-seat)_
