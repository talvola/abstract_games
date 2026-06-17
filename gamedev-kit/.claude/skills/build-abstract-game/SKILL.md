---
name: build-abstract-game
description: Build a game module for the Abstract Games Platform. Use when the user wants to implement an abstract board game (e.g. "build an Oust module", "add the game Hex", "make a game for the platform") so it can be uploaded and played. Works entirely from this kit — no platform source needed.
---

# Build an Abstract Games Platform module

This kit lets you implement an abstract board game that drops into the Abstract
Games Platform and is playable against people or the built-in AI.

## Do this

1. **Read `AGENTS.md`** (kit root) and **`SPEC.md`** (the full contract). They
   are short and authoritative — follow them over any assumption.
2. **Set up** (once):
   ```bash
   python3 -m venv .venv && . .venv/bin/activate
   pip install -e .
   ```
3. **Scaffold:** `cp -r template games/<uid>` (lowercase_snake uid), then edit
   `games/<uid>/manifest.json` and `games/<uid>/game.py`.
4. **Iterate to green** — the definition of done is:
   ```bash
   agp validate games/<uid>      # must print: RESULT: OK
   ```
   Also use `agp render games/<uid> --moves 8` and
   `agp playtest games/<uid> --bot` to sanity-check.
5. **Package:** `agp pack games/<uid>` → `games/<uid>.zip`.
6. Tell the user the `.zip` path and that they upload it via the platform's
   "Add a game" panel (signed in) or send it to the platform owner.

## Keep these straight (the common mistakes)

- Moves are **strings** in your own notation; for click-to-move in the web UI a
  move should be a **cell id** (`"col,row"` square, `"q,r"` hex).
- `apply_move` must be **pure** (copy state, never mutate the input).
- `serialize`/`deserialize` must **round-trip** and be JSON-able.
- `legal_moves` is **never empty** on a non-terminal state — model a pass inside
  `apply_move` instead.
- The game must **terminate** under random play.
- `render` returns a **RenderSpec dict** (board description), never pixels.

Reference implementations: `examples/tic_tac_toe/` (minimal) and the
shipped `template/` (k-in-a-row).
