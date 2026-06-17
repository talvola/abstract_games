"""``agp`` command-line tool: the local authoring loop.

    agp validate  <package>            run the conformance harness
    agp playtest  <package> [--bot]    self-play; report results & lengths
    agp render    <package>            print the opening board (+ optional play)
    agp pack      <package> [-o out]   zip a package for upload to the platform

Designed so a Claude Code session can iterate on a new game with a crisp goal:
"make ``agp validate`` pass", then eyeball ``agp render`` / ``agp playtest``.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from . import render_ascii
from .conformance import check
from .loader import PackageError, load
from .mcts import MCTSBot, RandomBot, play_match


def _load(path: str):
    try:
        return load(Path(path))
    except PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


def cmd_validate(args) -> int:
    manifest, game = _load(args.package)
    report = check(game, manifest, games=args.games, seed=args.seed)
    print(f"== validate {manifest['uid']} v{manifest['version']} ==")
    print(report.summary())
    print("\nRESULT:", "OK" if report.ok else "FAILED")
    return 0 if report.ok else 1


def cmd_playtest(args) -> int:
    manifest, game = _load(args.package)
    rng = random.Random(args.seed)
    options = {"size": args.size} if args.size else None

    def make_agent():
        return MCTSBot(rng, iterations=args.iterations) if args.bot else RandomBot(rng)

    kind = f"MCTS({args.iterations})" if args.bot else "random"
    wins = [0] * game.num_players
    others = {"draw": 0, "move-cap": 0}
    lengths = []
    print(f"== playtest {manifest['uid']}: {args.games} games, {kind} agents ==")
    if args.bot:
        print("  (MCTS self-play can be slow; progress shown per game)")
    for g in range(args.games):
        res = play_match(game, [make_agent() for _ in range(game.num_players)],
                         rng, options=options)
        if res["result"] != "terminal":
            others["move-cap"] += 1
            tag = "move-cap"
        else:
            lengths.append(res["moves"])
            ret = res["returns"]
            best = max(ret)
            winners = [i for i, v in enumerate(ret) if v == best]
            if len(winners) == 1 and best > 0:
                wins[winners[0]] += 1
                tag = f"P{winners[0]} ({res['moves']} mv)"
            else:
                others["draw"] += 1
                tag = "draw"
        print(f"  game {g + 1}/{args.games}: {tag}", flush=True)

    print("  --- summary ---")
    for i in range(game.num_players):
        print(f"  player {i} wins: {wins[i]}")
    print(f"  draws: {others['draw']}   move-cap: {others['move-cap']}")
    if lengths:
        print(f"  game length: avg {sum(lengths)/len(lengths):.1f}, "
              f"min {min(lengths)}, max {max(lengths)}")
    return 0


def cmd_render(args) -> int:
    manifest, game = _load(args.package)
    rng = random.Random(args.seed)
    options = {"size": args.size} if args.size else None
    state = game.initial_state(options=options, rng=rng)

    for step in range(args.moves + 1):
        print(f"\n--- {manifest['name']}  (move {step}) ---")
        print(render_ascii.render(game.render(state)))
        if game.is_terminal(state) or step == args.moves:
            break
        moves = game.legal_moves(state)
        state = game.apply_move(state, rng.choice(moves), rng=rng)
    return 0


def cmd_pack(args) -> int:
    import zipfile

    pkg = Path(args.package).resolve()
    manifest, _ = _load(str(pkg))
    out = Path(args.output) if args.output else pkg.parent / f"{manifest['uid']}.zip"
    skip = {"__pycache__", ".git", ".agp_meta.json"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(pkg.rglob("*")):
            if f.is_dir() or any(part in skip for part in f.parts):
                continue
            zf.write(f, f.relative_to(pkg))  # manifest.json at archive root
    print(f"packed {manifest['uid']} -> {out}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agp", description="Abstract Games Platform CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="run the conformance harness")
    v.add_argument("package")
    v.add_argument("--games", type=int, default=40)
    v.add_argument("--seed", type=int, default=0)
    v.set_defaults(func=cmd_validate)

    pt = sub.add_parser("playtest", help="self-play and report results")
    pt.add_argument("package")
    pt.add_argument("--games", type=int, default=20)
    pt.add_argument("--bot", action="store_true", help="use MCTS instead of random")
    pt.add_argument("--iterations", type=int, default=400)
    pt.add_argument("--size", type=int, default=None, help="board-size option, if supported")
    pt.add_argument("--seed", type=int, default=0)
    pt.set_defaults(func=cmd_playtest)

    rd = sub.add_parser("render", help="print the board (optionally play random moves)")
    rd.add_argument("package")
    rd.add_argument("--moves", type=int, default=0, help="random moves to play and show")
    rd.add_argument("--size", type=int, default=None)
    rd.add_argument("--seed", type=int, default=0)
    rd.set_defaults(func=cmd_render)

    pk = sub.add_parser("pack", help="zip a package for upload")
    pk.add_argument("package")
    pk.add_argument("-o", "--output", default=None, help="output .zip path")
    pk.set_defaults(func=cmd_pack)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
