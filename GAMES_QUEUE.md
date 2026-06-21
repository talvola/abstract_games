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
| Tablut (9×9 tafl) | review | conformance + capture/escape positions; no published number | **done → main** (king-assist resolved from Cyningstan) |

Both auto games were independently re-verified (the verifier recomputed perft to
197281 at depth 4, matching standard chess) and re-checked by me before merge. The
factory's per-package `selftest.py` is run by the suite via `test_package_selftests`.

## Batch 2 — chess-variant pack (2026-06-20)
| Game | Lane | Anchor | Status |
|---|---|---|---|
| Racing Kings | auto | shakmaty perft 21/421/11264 + 31,920 python-chess differential positions, 0 mismatches | **done(auto) → main** |
| Makruk (Thai chess) | review | conformance + rule positions; no published number | review → branch `factory/batch-2` |
| Shatranj (medieval) | review | conformance + rule positions; no published number | review → branch `factory/batch-2` |
| Capablanca (10×8) | review | conformance + rule positions; no published number | review → branch `factory/batch-2` |

## Needs human (escalations)

**Batch-2 review (low effort — no decisions, just a bless).** Makruk, Shatranj,
and Capablanca are on branch `factory/batch-2`. All three were independently
re-verified rules-faithful (the reviewer re-derived every piece move + win
condition, found no faults) and are conformant — they're queued **only** because
no published numeric anchor exists to machine-confirm them (unlike Racing Kings,
where `python-chess` gave a 32k-position cross-check). `git checkout factory/batch-2`
to try them. Documented simplifications: Makruk drops native counting rules
(insufficient-material + ply-cap draws); Shatranj uses stalemate-as-win + bare-king.
Say "merge batch-2" and I'll bring them to main, or flag any you want changed.

> Throughput note: this is the expected long-tail shape — the auto lane is mostly
> chess-family with a published perft (KotH, Three-Check, Racing Kings); most
> traditional games land here as "verified-faithful, awaiting a bless". If you'd
> rather raise the bar so a clean independent rule-review auto-merges without a
> numeric anchor, say so and I'll adjust the gate.

## Blocked on a capability
_(tracked in `GAME_BACKLOG.md` — drops, stacking, territory scoring, point-and-line, >2-seat)_
