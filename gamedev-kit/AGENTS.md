# Building an Abstract Games Platform module — agent guide

You are building a **game module** for the Abstract Games Platform. You do **not**
need the platform's source code. Everything required is in this kit: the `agp`
SDK, the contract (`SPEC.md`), a working `template/`, and a worked `examples/`.

**Definition of done:** `agp validate <your-package>` prints `RESULT: OK`. That
single command checks every rule the platform enforces. Build toward it.

## Setup (once)

```bash
cd <this-kit>
python3 -m venv .venv && . .venv/bin/activate
pip install -e .          # installs the `agp` command (no other dependencies)
agp validate examples/tic_tac_toe   # sanity check: should print RESULT: OK
```

## Workflow

1. **Copy the template** to a new folder named for your game's uid:
   `cp -r template games/<uid>` (lowercase_snake_case uid).
2. **Edit `games/<uid>/manifest.json`** — set `uid`, `name`, `description`,
   player count, tags, any `options` (e.g. board size), and `bgg_url` (a link to
   the official/source rules, if any). Keep `engine_api` as given.
   Then **rewrite `games/<uid>/rules.md`** — a one-page writeup of the rules *as
   you implement them* (the platform shows it in a "Rules" dialog, with `bgg_url`
   as an "official source" link). Note any choice where sources disagree.
3. **Implement `games/<uid>/game.py`** — replace the template logic with your
   rules. Read `SPEC.md` for the full contract; the short version is below.
4. **Validate often:** `agp validate games/<uid>`. Fix what it reports.
5. **Eyeball it:** `agp render games/<uid> --moves 8` (draws the board + a few
   random moves as ASCII). `agp playtest games/<uid> --bot` runs the platform's
   generic AI against itself — check the results look sane.
6. **Package it:** `agp pack games/<uid>` produces `games/<uid>.zip`.
7. **Submit it:** upload the `.zip` via the platform's "Add a game" panel (when
   signed in), or hand the `.zip` to the platform owner. On the server it is
   re-validated and registered; then it is immediately playable — against people
   (correspondence) or the built-in AI — with no further code.

## The contract (short form)

Your `game.py` defines one subclass of `agp.game.Game`. The engine treats your
*state* object as opaque and only touches it through these methods:

| Method | Must do |
|---|---|
| `num_players` (property) | how many players |
| `initial_state(options=None, rng=None)` | return the starting state |
| `current_player(state)` | index (0-based) of the player to move |
| `legal_moves(state)` | list of move strings; **non-empty unless terminal** |
| `apply_move(state, move, rng=None)` | return a **new** state; **never mutate the input** |
| `is_terminal(state)` | bool |
| `returns(state)` | payoff list at terminal, e.g. `[1.0, -1.0]`; length = `num_players` |
| `serialize(state)` / `deserialize(d)` | JSON-able snapshot that **round-trips** |
| `render(state, perspective=None)` | a JSON RenderSpec (a board *description*, never pixels) |

### Five rules `agp validate` enforces

1. **Moves are short strings** in your own notation (e.g. `"1,2"`).
2. **`apply_move` is pure** — copy the state, mutate the copy, return it.
3. **`serialize` round-trips** and is JSON-able.
4. **`legal_moves` is never empty on a non-terminal state.** If the player to
   move has no action, advance past them (a *pass*) inside `apply_move`.
5. **The game always terminates** (no infinite play under random moves).

### Modelling tips

- **A turn can be several moves by one player** — just keep `current_player`
  returning the same index until the turn ends. The engine handles it.
- **If the opening position would look terminal** (e.g. a capture game where
  "0 stones" is also the start), store the result as a field set during
  `apply_move` instead of inferring it from the board.
- **Randomness** (dice/shuffles): use the passed `rng` and set
  `"has_randomness": true` in the manifest.

## RenderSpec (so the platform can draw your game)

`render()` returns a plain dict. The platform draws it with one generic
renderer, so you never write UI. Supported boards today: `square` and `hex`.

```jsonc
{
  "board": { "type": "square", "width": 3, "height": 3 },   // or
  "board": { "type": "hex", "shape": "hexagon", "size": 7 },
  "pieces":     [ { "cell": "1,2", "owner": 0, "label": "X" } ],
  "highlights": [ { "cell": "0,0", "kind": "last-move" } ],   // optional
  "caption": "Red to move"                                    // optional
}
```

Cell ids must equal the cell strings you use in moves: `"col,row"` (0-based) for
square, `"q,r"` (axial) for hex. For click-to-move, a move is a **`>`-separated
path of cell ids**:

- placement → a single cell, e.g. `"2,3"` (one click);
- from–to (chess-like) → `"from>to"`, e.g. `"2,1>2,3"` (click source, then target);
- needs a choice (e.g. promotion) → append `"=CHOICE"`, e.g. `"2,4>2,5=Q"`; the
  UI shows a picker when a destination has several such options.

(Other move notations still validate and play via the API, just not clickable.)

Read `SPEC.md` for the complete reference, and `examples/tic_tac_toe/game.py`
for the simplest end-to-end example.
