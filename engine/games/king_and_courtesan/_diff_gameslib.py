#!/usr/bin/env python3
"""Differential test of King & Courtesan against AbstractPlay's `gameslib`.

`gameslib` (github.com/AbstractPlay/gameslib) ships a *rule-enforcing* second
implementation of this game as `src/games/courtesan.ts`. It is **AGPL — used
here as an ORACLE ONLY; no code is copied.** Where it and Mark Steere's
rulebook disagree, the rulebook wins.

This script is **not** part of the test suite: it needs `node` + a checkout of
`gameslib` with `node_modules` installed, so it is env-gated and manual.

    AP_GAMESLIB=/path/to/gameslib \
      python3 engine/games/king_and_courtesan/_diff_gameslib.py --games 40

What it compares, at EVERY ply of every game:

* the full set of legal moves, normalised to `(from, to)` CELL PAIRS in our
  own `"c,r"` ids — never move strings, whose notation differs between the two
  engines (AP writes `a1-b1` / `a1xb1` / `a1/b1`, we write `0,0>1,0`);
* the resulting board — owner + king/courtesan for every occupied cell;
* game-over status and the winner.

It drives from BOTH sides: even-numbered games let OUR engine pick the move,
odd-numbered games let AP's list pick it, so neither engine's move ordering can
hide a missing move in the other.

AP exposes only two board sizes (its default 8, and the `size-6` variant), so
the comparison runs on 6 and 8; our 7x7 has no oracle.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402

DRIVER = r"""
import { GameFactory } from "./src/games";
import * as readline from "readline";

let g: any = null;

function validated(): string[] {
  // The raw generator can over-report; AP's own gate is validateMove().
  return g.moves().filter((m: string) => {
    const r = g.validateMove(m);
    return r.valid === true && r.complete === 1;
  });
}

function boardDump(): any {
  const out: any = {};
  for (const [cell, v] of g.board.entries()) out[cell] = `${v[0]}${v[1]}`;
  return out;
}

const rl = readline.createInterface({ input: process.stdin });
rl.on("line", (line: string) => {
  const cmd = JSON.parse(line);
  try {
    if (cmd.cmd === "new") {
      const variants = cmd.size === 6 ? ["size-6"] : [];
      g = GameFactory("courtesan", undefined, variants);
      console.log(JSON.stringify({ ok: true }));
    } else if (cmd.cmd === "moves") {
      console.log(JSON.stringify({ ok: true, moves: validated(), raw: g.moves().length }));
    } else if (cmd.cmd === "move") {
      g.move(cmd.m);
      console.log(JSON.stringify({ ok: true }));
    } else if (cmd.cmd === "status") {
      console.log(JSON.stringify({
        ok: true, gameover: g.gameover, winner: g.winner,
        currplayer: g.currplayer, board: boardDump(),
      }));
    } else {
      console.log(JSON.stringify({ ok: false, err: "bad cmd" }));
    }
  } catch (e: any) {
    console.log(JSON.stringify({ ok: false, err: String(e).slice(0, 300) }));
  }
});
"""


class AP:
    """A persistent ts-node process speaking one JSON command per line."""

    def __init__(self, root: Path):
        drv = root / "_kc_diff_driver.ts"
        drv.write_text(DRIVER)
        self.p = subprocess.Popen(
            ["npx", "ts-node", "--transpileOnly",
             "--compilerOptions", '{"module":"commonjs"}', str(drv)],
            cwd=str(root), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, bufsize=1,
        )

    def call(self, **cmd):
        self.p.stdin.write(json.dumps(cmd) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("gameslib driver died")
        r = json.loads(line)
        if not r.get("ok"):
            raise RuntimeError(f"gameslib error on {cmd}: {r.get('err')}")
        return r

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()


def ap_to_cell(alg: str) -> str:
    """AP algebraic ('a1') -> our cell id ('0,0').

    AP builds algebraic with `coords2algebraic(x, y, height)` = file letter for
    x, rank `height - y`; its player 1 starts on `a1`, ours (seat 0) on `0,0`,
    so column `x` is our `c` and rank `y+1` is our `r+1`.
    """
    return f"{ord(alg[0]) - 97},{int(alg[1:]) - 1}"


def ap_pairs(moves) -> set:
    out = set()
    for m in moves:
        for op in ("-", "x", "/"):
            if op in m:
                a, b = m.split(op)
                out.add((ap_to_cell(a), ap_to_cell(b)))
                break
    return out


def our_pairs(moves) -> set:
    return {tuple(m.split(">")) for m in moves}


def our_move_string(pair) -> str:
    return f"{pair[0]}>{pair[1]}"


def ap_move_string(pair, ap_moves) -> str:
    for m in ap_moves:
        for op in ("-", "x", "/"):
            if op in m:
                a, b = m.split(op)
                if (ap_to_cell(a), ap_to_cell(b)) == pair:
                    return m
    raise KeyError(pair)


def board_ours(g, s) -> dict:
    return {f"{c},{r}": f"{o}{k}" for (c, r), (o, k) in s.board.items()}


def board_ap(dump: dict) -> dict:
    # AP keys are algebraic, values already "<player><piece>"; renumber the
    # player to our 0-based seats.
    return {ap_to_cell(k): f"{int(v[0]) - 1}{v[1]}" for k, v in dump.items()}


def main() -> int:
    ap_arg = argparse.ArgumentParser()
    ap_arg.add_argument("--games", type=int, default=20)
    ap_arg.add_argument("--sizes", default="6,8")
    ap_arg.add_argument("--seed", type=int, default=20220528)
    args = ap_arg.parse_args()

    root = os.environ.get("AP_GAMESLIB")
    if not root:
        print("set AP_GAMESLIB=/path/to/gameslib (with node_modules installed)")
        return 2
    man, g = load_from_dir(Path(__file__).resolve().parent)
    ap = AP(Path(root))
    rng = random.Random(args.seed)
    positions = moves_compared = 0
    try:
        for size in [int(x) for x in args.sizes.split(",")]:
            for game_i in range(args.games):
                drive_ours = (game_i % 2 == 0)
                ap.call(cmd="new", size=size)
                s = g.initial_state({"size": size})
                while True:
                    st = ap.call(cmd="status")
                    ours_over = g.is_terminal(s)
                    if ours_over != st["gameover"]:
                        print(f"MISMATCH terminal size={size} game={game_i} "
                              f"ply={s.ply}: ours={ours_over} ap={st['gameover']}")
                        return 1
                    if board_ours(g, s) != board_ap(st["board"]):
                        print(f"MISMATCH board size={size} game={game_i} ply={s.ply}")
                        print(" ours:", sorted(board_ours(g, s).items()))
                        print(" ap  :", sorted(board_ap(st["board"]).items()))
                        return 1
                    if ours_over:
                        ours_w = None if s.winner is None else [s.winner + 1]
                        if sorted(st["winner"]) != sorted(ours_w or []):
                            print(f"MISMATCH winner size={size} game={game_i}: "
                                  f"ours={ours_w} ap={st['winner']}")
                            return 1
                        break
                    if st["currplayer"] - 1 != s.to_move:
                        print(f"MISMATCH to_move size={size} game={game_i} ply={s.ply}")
                        return 1

                    mv = ap.call(cmd="moves")
                    theirs, ours = ap_pairs(mv["moves"]), our_pairs(g.legal_moves(s))
                    positions += 1
                    moves_compared += len(ours)
                    if theirs != ours:
                        print(f"MISMATCH moves size={size} game={game_i} ply={s.ply}")
                        print("  only ours:", sorted(ours - theirs))
                        print("  only ap  :", sorted(theirs - ours))
                        print("  board:", sorted(board_ours(g, s).items()))
                        return 1
                    if len(mv["moves"]) != mv["raw"]:
                        print(f"  note: AP validateMove filtered "
                              f"{mv['raw'] - len(mv['moves'])} raw moves at ply {s.ply}")

                    pool = sorted(ours if drive_ours else theirs)
                    pick = pool[rng.randrange(len(pool))]
                    s = g.apply_move(s, our_move_string(pick))
                    ap.call(cmd="move", m=ap_move_string(pick, mv["moves"]))
    finally:
        ap.close()
    print(f"OK — no divergence. positions={positions} moves_compared={moves_compared} "
          f"sizes={args.sizes} games_per_size={args.games} (half driven by each engine)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
