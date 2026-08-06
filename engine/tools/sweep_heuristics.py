"""Sweep: does any game's heuristic() RAISE, or return a mis-shaped payoff vector?

`agp/mcts.py::_evaluate` used to wrap `heuristic()` in `except Exception: pass`
and fall back to `[0.0] * num_players`, so a heuristic that THROWS scored every
rollout cutoff as a perfect draw -- byte-for-byte indistinguishable from shipping
no heuristic at all, while `validate`, conformance and every functional test
passed. Found in wave 21 by a QA agent measuring a heuristic through that path.

The warning added to `_evaluate` makes the failure visible from now on; this
sweep answers the retrospective question: is it shipped anywhere in the library?

For every game exposing a `heuristic`, under the default options AND each
single-axis option variation, play random plies and at every ply require:
  * heuristic() does not raise, and
  * its return is None (documented "no opinion") or a well-formed payoff vector
    -- a list/tuple of num_players finite numbers, the `returns()` convention.

Note the shape check is the same `agp.mcts.check_payoffs` MCTS now enforces, so a
game that passes here cannot fail at a live rollout cutoff either.

Run from engine/:  PYTHONPATH=. python3 tools/sweep_heuristics.py [uid ...]
"""
import random
import sys
import traceback
from pathlib import Path

from agp.loader import load_from_dir
from agp.mcts import check_payoffs

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sweep_render_bounds import option_settings          # noqa: E402

GAMES = Path("games")
PLIES = 60
SEED = 20260805


def check(game, options, rng):
    """Play random plies calling heuristic() at each; return a failure string."""
    try:
        s = game.initial_state(options) if options else game.initial_state()
    except TypeError:
        s = game.initial_state()
    calls = 0
    for ply in range(PLIES):
        try:
            val = game.heuristic(s)
        except Exception:
            return (f"ply {ply}: heuristic() RAISED -- every rollout cutoff is "
                    f"silently scored as a draw\n"
                    + traceback.format_exc(limit=4)), calls
        calls += 1
        if val is not None:
            try:
                check_payoffs(game, val)
            except TypeError as e:
                return f"ply {ply}: {e}", calls
        if game.is_terminal(s):
            return None, calls
        moves = game.legal_moves(s)
        if not moves:
            return None, calls
        s = game.apply_move(s, rng.choice(moves))
    return None, calls


def main(argv):
    want = set(argv[1:])
    uids = sorted(p.name for p in GAMES.iterdir() if (p / "manifest.json").exists())
    if want:
        uids = [u for u in uids if u in want]
    bad, skipped, combos, calls, with_h = [], 0, 0, 0, 0
    for uid in uids:
        try:
            man, game = load_from_dir(GAMES / uid)
        except Exception as e:                             # noqa: BLE001
            skipped += 1
            print(f"  SKIP {uid}: load failed: {e}", flush=True)
            continue
        if getattr(game, "heuristic", None) is None:
            continue
        with_h += 1
        for options in option_settings(man):
            rng = random.Random(SEED)
            try:
                fail, n = check(game, options, rng)
            except Exception:                              # noqa: BLE001
                fail, n = "EXCEPTION in the sweep itself\n" + traceback.format_exc(limit=3), 0
            combos += 1
            calls += n
            if fail:
                bad.append((uid, options, fail))
                print(f"!! {uid} options={options}\n   {fail}", flush=True)
    print(f"\n{with_h} of {len(uids)} games expose a heuristic; checked {combos} "
          f"(uid, options) combinations / {calls} heuristic calls; "
          f"{skipped} load failures; {len(bad)} FAILURES")
    for uid, options, fail in bad:
        print(f"  - {uid} {options}: {fail.splitlines()[0]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
