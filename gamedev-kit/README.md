# Abstract Games Platform — Game Dev Kit

Build a game that drops into the Abstract Games Platform and is playable against
other people (correspondence) or the built-in AI — **without needing the
platform's source code**. Everything you need is here.

## What's inside

- `agp/` — the SDK: the game contract, a conformance validator, a generic MCTS
  opponent, and the `agp` command. Pure Python standard library.
- `SPEC.md` — the full authoring contract.
- `AGENTS.md` — a build guide written for an AI coding agent (Claude Code etc.).
- `.claude/skills/build-abstract-game/` — a ready-to-use Claude Code skill; with
  this kit in your project, just ask Claude Code to "build a <game> module".
- `template/` — a complete, working starter game to copy and edit.
- `examples/tic_tac_toe/` — the simplest end-to-end example.

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .

agp validate examples/tic_tac_toe     # → RESULT: OK

cp -r template games/mygame           # start your game
#   ...edit games/mygame/manifest.json and games/mygame/game.py...
agp validate games/mygame             # iterate until: RESULT: OK
agp render   games/mygame --moves 8   # eyeball the board
agp playtest games/mygame --bot       # generic AI self-play
agp pack     games/mygame             # → games/mygame.zip  (upload this)
```

Then upload `games/mygame.zip` through the platform's **Add a game** panel (when
signed in), or send it to the platform owner. The server re-validates and
registers it; no redeploy.

## Building with an AI agent

Open this kit in your editor and tell your coding agent: *"Build a module for
the game X for the Abstract Games Platform — read AGENTS.md and SPEC.md first."*
If you use Claude Code, the bundled skill triggers automatically.

The contract is small and the validator is strict and fast, so the loop is
tight: implement → `agp validate` → fix → repeat until green.
