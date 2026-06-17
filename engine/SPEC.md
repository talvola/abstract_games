# Authoring a game module (engine_api 1)

This is the contract a Claude Code session generates against. **Goal: make
`agp validate <yourgame>` pass**, then sanity-check with `agp render` / `agp playtest`.

## Package layout

```
yourgame/
  manifest.json     # metadata (required)
  game.py           # one subclass of agp.game.Game (required)
  rules.md          # optional human rules
  assets/           # optional images
```

Distribute as that folder or a `.zip` of it (flat, or a single top-level folder).

## manifest.json

```jsonc
{
  "uid": "yourgame",            // unique, stable, lowercase_snake
  "name": "Your Game",
  "version": "1.0.0",
  "engine_api": "1",            // must match the engine
  "author": "...",
  "players": { "min": 2, "max": 2 },
  "has_randomness": false,      // true if apply_move/initial_state use rng
  "hidden_info": false,         // true if you implement player_view
  "category": "N-in-a-row",     // groups the game in the lobby; see below
  "tags": ["square"],
  "bgg_url": "https://boardgamegeek.com/...",   // optional
  "options": { "size": { "choices": [4,5,6], "default": 5 } },  // optional variants
  "description": "..."
}
```

## The Game interface (`agp.game.Game`)

Implement these. See `games/tic_tac_toe/game.py` (minimal) and `games/oust/game.py`
(captures, multi-placement turns, pass handling, event-based win) as references.

| Method | Contract |
|---|---|
| `num_players` (property) | how many players |
| `initial_state(options=None, rng=None)` | starting state; `options` = variant settings, `rng` = `random.Random` |
| `current_player(state)` | 0-based index to move (or `agp.CHANCE` for a pending random event) |
| `legal_moves(state)` | list of move strings; **non-empty unless terminal** |
| `apply_move(state, move, rng=None)` | return a **new** state; **must not mutate** `state` |
| `is_terminal(state)` | bool |
| `returns(state)` | per-player payoff list at terminal (e.g. `+1/0/-1`), length `num_players` |
| `serialize(state)` | JSON-able dict; **must round-trip** with `deserialize` |
| `deserialize(data)` | inverse of `serialize` |
| `render(state, perspective=None)` | JSON-able RenderSpec (see below); never pixels |
| `move_to_str` / `parse_move` | optional; default to identity on strings |
| `player_view(state, player)` | only for hidden-info games; default = full info |

### Hard invariants (checked by `agp validate`)

1. **Moves are strings** in your own notation (e.g. `"1,2"`).
2. **`apply_move` is pure** — never mutate the input state; return a fresh one.
3. **`serialize` round-trips** — `deserialize(serialize(s))` serializes identically and is JSON-able.
4. **Non-empty `legal_moves`** on every non-terminal state. If the player to move
   has no action, advance past them (a *pass*) inside `apply_move`, don't return `[]`.
5. **The game terminates.** No infinite play under random move selection.
6. **`returns` is well-formed** at terminal: length `num_players`, finite numbers.

### Modelling notes

* **A "turn" can be several moves by the same player.** Just keep
  `current_player` returning the same index until the turn ends (see Oust's
  capture chains). The engine and MCTS handle this automatically.
* **Win as an event, not a board predicate?** Store it in the state (Oust keeps
  a `winner` field) rather than recomputing from the board, when the opening
  position would otherwise look terminal.
* **Randomness** (dice/decks): use the passed `rng` in `apply_move` /
  `initial_state` and set `has_randomness: true`. (Generic MCTS plays these but
  isn't yet specialised for them — ISMCTS is future work.)

## RenderSpec

A JSON-able dict the generic renderer draws. Phase-0 shape:

```jsonc
{
  "board": { "type": "square", "width": 3, "height": 3 }
        // or { "type": "hex", "shape": "hexagon", "size": 7 },
  "pieces":     [ { "cell": "1,2", "owner": 0, "label": "X" } ],
  "highlights": [ { "cell": "0,0", "kind": "last-move" } ],   // optional
  "caption": "Red to move"                                     // optional
}
```

Cell ids are your move-notation cell strings: `"col,row"` for square, `"q,r"`
(axial) for hex. The CLI's ASCII previewer understands `square` and `hex`.

### Move notation & click-to-move

A move is a **`>`-separated path of cell ids** (cell ids use `,`, so they never
clash with `>`). The web UI derives click-to-move from this:

- **Placement** games: a move is a single cell, e.g. `"2,3"` — one click.
- **From–to** games (chess-like): a move is `"from>to"`, e.g. `"2,1>2,3"` — click
  the source, then the destination. The UI offers only legal continuations.
- Multi-step paths (`"a>b>c"`) are supported too (e.g. chained captures).

Use this convention for any game you want clickable. Other notations still
validate and play via the API.

### Categories

`category` groups your game in the lobby. Prefer an existing bucket so games
cluster well; common ones: **"N-in-a-row"**, **"Chess & chess-like"**,
**"Capture / annihilation"**, **"Connection"**. Anything else is fine and is
shown under its own heading (no category → "Other").

## The authoring loop

```
agp validate games/yourgame          # must print RESULT: OK
agp render   games/yourgame --moves 8 # eyeball the board + a few random moves
agp playtest games/yourgame --bot     # MCTS self-play; check results look sane
```
