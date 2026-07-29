"""Sweep: does any game's render() declare a board that does not CONTAIN its own pieces?

Board.jsx builds its clickable cell set from board.width/height (square), size/shape/
cells (hex), or board.cells (polygons), then joins pieces by cell id. A piece whose
cell is outside the declared set is silently DROPPED -- no crash, no warning, the
stone just isn't there. That is invisible to validate/selftest.

Found in wave 14 by the taiji QA agent (a mutant hard-coding 9x9 survived its
selftest, which would have swallowed the outer files/ranks of the 11x11 board).
This sweep asks whether it is shipped anywhere, especially in games with a
board-SIZE option, where the default size hides the bug.

Run from engine/:  PYTHONPATH=. python3 <this>
"""
import itertools
import random
import sys
import traceback
from pathlib import Path

from agp.loader import load_from_dir

GAMES = Path("games")
PLIES = 40
SEED = 20260729


def declared_cells(board):
    """The set of cell ids Board.jsx will create for this board spec, or None if
    the shape is one we cannot enumerate cheaply (then we skip)."""
    t = board.get("type", "square")
    if t == "square":
        w, h = board.get("width"), board.get("height")
        if not isinstance(w, int) or not isinstance(h, int):
            return None
        return {f"{c},{r}" for c in range(w) for r in range(h)}
    if t == "polygons":
        cells = board.get("cells")
        if not isinstance(cells, list):
            return None
        return {c["id"] for c in cells if isinstance(c, dict) and "id" in c}
    if t == "hex":
        if isinstance(board.get("cells"), list):          # explicit axial list
            return set(board["cells"])
        shape = board.get("shape")
        if shape == "hexagon" and isinstance(board.get("size"), int):
            n = board["size"] - 1
            return {f"{q},{r}" for q in range(-n, n + 1)
                    for r in range(max(-n, -q - n), min(n, -q + n) + 1)}
        if shape == "rhombus":
            w, h = board.get("width"), board.get("height")
            if not isinstance(w, int) or not isinstance(h, int):
                return None
            return {f"{q},{r}" for q in range(w) for r in range(h)}
        return None
    return None


def option_settings(manifest):
    """Default options, plus one setting per non-default value of each option
    (single-axis variation, not the cross product)."""
    opts = manifest.get("options") or {}
    if isinstance(opts, list):
        opts = {o.get("key"): o for o in opts if isinstance(o, dict)}
    base = {}
    axes = []
    for key, spec in (opts.items() if isinstance(opts, dict) else []):
        vals = None
        if isinstance(spec, dict):
            vals = spec.get("values") or spec.get("choices") or spec.get("enum")
            dflt = spec.get("default")
        if not isinstance(vals, list) or not vals:
            continue
        dflt = dflt if dflt in vals else vals[0]
        base[key] = dflt
        for v in vals:
            if v != dflt:
                axes.append((key, v))
    settings = [dict(base)]
    for key, v in axes:
        s = dict(base)
        s[key] = v
        settings.append(s)
    return settings


def check(game, options, rng):
    """Play random plies; return a failure string on the first containment breach."""
    try:
        s = game.initial_state(options) if options else game.initial_state()
    except TypeError:
        s = game.initial_state()
    for ply in range(PLIES):
        spec = game.render(s)
        board = spec.get("board") or {}
        cells = declared_cells(board)
        if cells is None:
            return None                                  # shape we don't model
        for p in spec.get("pieces") or []:
            cid = p.get("cell")
            if cid is not None and cid not in cells:
                return (f"ply {ply}: piece at {cid!r} is OUTSIDE the declared "
                        f"{board.get('type','square')} board "
                        f"({ {k: v for k, v in board.items() if k in ('width','height','size','shape')} })")
        if game.is_terminal(s):
            return None
        moves = game.legal_moves(s)
        if not moves:
            return None
        s = game.apply_move(s, rng.choice(moves))
    return None


def main():
    uids = sorted(p.name for p in GAMES.iterdir() if (p / "manifest.json").exists())
    bad, skipped, checked = [], 0, 0
    for uid in uids:
        try:
            man, game = load_from_dir(GAMES / uid)
        except Exception as e:
            skipped += 1
            print(f"  SKIP {uid}: load failed: {e}", flush=True)
            continue
        for options in option_settings(man):
            rng = random.Random(SEED)
            try:
                fail = check(game, options, rng)
            except Exception:
                fail = "EXCEPTION\n" + traceback.format_exc(limit=3)
            checked += 1
            if fail:
                bad.append((uid, options, fail))
                print(f"!! {uid} options={options}\n   {fail}", flush=True)
    print(f"\nchecked {checked} (uid, options) combinations over {len(uids)} games; "
          f"{skipped} load failures; {len(bad)} CONTAINMENT FAILURES")
    for uid, options, fail in bad:
        print(f"  - {uid} {options}: {fail.splitlines()[0]}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
