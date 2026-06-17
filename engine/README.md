# AGP Engine (Phase 0)

The core of the Abstract Games Platform: a language-neutral **game contract**, a
**package loader**, a **conformance harness**, and a **generic MCTS opponent**
that plays any conforming game. No dependencies beyond the Python standard
library (Python ≥ 3.10).

This phase is deliberately local-only — no server, no accounts, no web UI. It
exists to prove the game abstraction against real games before any
infrastructure is built. See `../PLATFORM_PLAN.md` for the full roadmap and
`SPEC.md` for how to author a game module.

## Layout

```
engine/
  agp/                 # the engine package
    game.py            # the Game contract (the key interface)
    types.py           # Move / State / RenderSpec / CHANCE
    loader.py          # load a package dir or .zip -> (manifest, Game)
    conformance.py     # the validate harness
    mcts.py            # RandomBot, MCTSBot (generic UCT), play_match
    render_ascii.py    # text preview of a RenderSpec
    cli.py             # the `agp` command
  games/
    tic_tac_toe/       # minimal reference module
    oust/              # Mark Steere's Oust — captures, chained turns, hex board
  tests/
  SPEC.md              # authoring guide (the Claude Code target)
```

## Use

```bash
cd engine
# either install it…
pip install -e .
# …or just put it on the path:
export PYTHONPATH=.

agp validate games/oust                 # conformance: must print RESULT: OK
agp render   games/oust --size 4 --moves 8
agp playtest games/oust --bot --size 4  # MCTS self-play summary
agp validate games/tic_tac_toe
```

## What a game is

A game is a package: `manifest.json` + a `game.py` defining one `agp.game.Game`
subclass. Moves are strings; states are opaque to the engine; rendering returns
a JSON board *description* (RenderSpec), never pixels — so one renderer can draw
every game. Full contract and invariants: **`SPEC.md`**.

## Status / next

Phase 0 is done when the abstraction holds for ≥1 trivial and ≥1 real game — it
does (Tic-Tac-Toe, Oust). Next (per `../PLATFORM_PLAN.md`): Phase 1 = a web
frontend with a generic SVG renderer driven by RenderSpec, playing hotseat / vs
the MCTS bot.
