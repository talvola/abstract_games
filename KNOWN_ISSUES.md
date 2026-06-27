# Known issues

## ✅ FIXED (2026-06-26) — Bot (MCTS) was unusably slow for heavy games — esp. Chess
**Was:** Chess vs computer sat at "Computer to move (thinking…)" for 15+ minutes
(reported 2026-06-25 on the hosted instance).

**Fix shipped** (the ranked fixes 1+2 below, plus a heuristic eval):
- `MCTSBot` now takes a **`max_time`** wall-clock budget — `select` returns the
  best move so far once exceeded, so move time is bounded regardless of CPU/game.
  The server passes `AGP_BOT_MAX_TIME` (default **3.0 s**) at every call site
  (`server/games.py::advance_bots`, the `/api/games/{uid}/bot` endpoint).
- **`max_rollout` default cut 400 → 50**; at the cutoff the position is scored by
  an optional **`game.heuristic(state)`** hook instead of drifting ~400 random
  plies to a draw. `ChessLike.heuristic` = tanh-squashed material balance (incl.
  drop reserves); games without the hook fall back to a draw (unchanged behaviour).
- Measured: a chess opening move went from **minutes/hours → ~3 s** (the budget);
  MCTS now beats RandomBot on material and never loses TTT. Verify with the repro
  below (should print ~`3.0s`).

Possible future work (not needed for launch): async `/advance` (return "pending" +
poll) so even a long think never *looks* hung; a capture-biased rollout policy;
per-category iteration tuning.

<details><summary>Original diagnosis (kept for reference)</summary>

### Root cause (measured, not guessed)
- The bot is `agp.MCTSBot` (`engine/agp/mcts.py`). Each MCTS *iteration* runs a
  **full random rollout to terminal**. A random Chess game wanders **~360–470 plies**
  before ending (random play almost never checkmates — it drifts to a 50-move /
  insufficient-material draw). Measured **~1.5 s per rollout** on a fast dev machine
  (`legal_moves` ≈ 1.2 ms each × ~400 plies).
- The server (`server/games.py::advance_bots`) runs **300 iterations** (match default
  `bot_iterations=300` in `server/app.py`). 300 × ~1.5 s ≈ **~7.5 min per move on a
  fast box**; on Render's free **0.1-CPU** instance that's **well over an hour**.
- The move is computed **synchronously inside the `/advance` HTTP request**, so it
  blocks and exceeds the proxy/HTTP timeout → the client never gets the reply → the UI
  is stuck at "thinking…" (the "hung" symptom; it isn't actually deadlocked).
- `MCTSBot.select` has **no wall-clock limit** (`for _ in range(self.iterations)`), and
  the `max_rollout=400` cap is set too high to help (chess rollouts already end ≈ 400).
- Affects all heavy games (chess-family worst). Small/short-rollout games are fine.

### Fixes (ranked — all small, local to `engine/agp/mcts.py` + the server)
1. **Time-bounded search (biggest correctness win):** add a `max_time` budget to
   `MCTSBot.select` — break the loop when wall-clock exceeds it, return best-move-so-far.
   Have the server pass e.g. 2–4 s. Caps move time regardless of CPU or game.
2. **Cheap, shallow rollouts (biggest speed win — the rollout is the cost):** cut
   `max_rollout` to ~40–60 and evaluate a **heuristic** (e.g. material/position) at the
   cutoff instead of playing ~400 random plies to a draw. ~6–10× faster rollouts.
3. **Lower default iterations** (300 → ~80–150), ideally per-game/per-category, as a stopgap.
4. **Async bot compute:** make `/advance` kick off the move in a background task and
   return "pending"; the UI polls. Decouples "appears hung" from "slow".
5. Free-tier CPU multiplies all of the above; a paid Render instance helps, but the
   software fixes (1 + 2) are the real solution and benefit local play too.

### How to verify a fix
Time one move from the opening — target **< a few seconds**:
```bash
cd engine && PYTHONPATH=. python3 -c "
import time, random; from agp import MCTSBot; import games.chess.game as m
g=[getattr(m,n) for n in dir(m) if isinstance(getattr(m,n),type) and getattr(getattr(m,n),'uid','')=='chess'][0]()
s=g.initial_state(); t=time.time(); mv=MCTSBot(random.Random(1), iterations=300).select(g,s)
print(f'{time.time()-t:.1f}s -> {mv}')"
```
Today this prints minutes (often killed before finishing); a fixed bot should print seconds.
