#!/usr/bin/env python3
"""Differential harness: Attangle vs. the AbstractPlay `gameslib` oracle.

MANUAL / ONE-TIME — this is NOT part of the test suite (it needs a node
toolchain and a checkout of gameslib).  `selftest.py` carries the pure-stdlib
anchors; this script is the evidence behind them.

gameslib (https://github.com/AbstractPlay/gameslib, MIT) is a rule-ENFORCING
reference implementation of Attangle.  It is used here as an ORACLE ONLY: no
code was copied from it.

Usage
-----
    AP_GAMESLIB=/path/to/ap_gameslib \\
    python3 games/attangle/_diff_ap.py [--games 200] [--seed 42] [--variant attangle|grand|both]

What is compared, at EVERY ply of every random game
---------------------------------------------------
  * the cell set and the adjacency (six-neighbour) relation of the board,
    under our axial -> algebraic mapping  [geometry probe, run once]
  * the full set of legal moves, normalised so the two implementations'
    different move STRINGS are comparable:
        placement   -> "P:<cell>"
        capture     -> "C:<attacker>|<attacker>|<target>"   (attackers sorted)
    Comparing SETS catches both missing and spurious moves.
  * the board contents cell by cell, as the exact bottom->top owner sequence
  * both stocks, and the player to move
  * at the end: terminality and the winner

The oracle drives: it plays a seeded random game and logs every position; this
script replays the same chosen moves through our engine.

Grand Attangle note
-------------------
spielstein's Grand Attangle rules say "2 x 27 pieces" and then "the players
place 3 of their pieces" from those 27, so 24 remain in hand (and 27+27 = 54 =
the number of non-void spaces, exactly as 18+18 = 36 does in the base game).
gameslib starts the hand at 27 *in addition to* the 3 placed pieces.  The
driver therefore sets the oracle's hand to 24 (a value assignment on the object,
not a change to its code) so the two are comparable; pass --ap-hand 27 to run
against gameslib's own number instead (expect divergence once a player has
placed 24 pieces).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agp.loader import load_from_dir                              # noqa: E402

HARNESS = r"""
import { GameFactory } from "./src/games";
import { HexTriGraph } from "./src/common/graphs";

function rng(seed: number) {
    let a = seed >>> 0;
    return function () {
        a |= 0; a = (a + 0x6D2B79F5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

const variant = process.argv[2] === "grand" ? "grand" : "base";
const nGames = parseInt(process.argv[3] || "50", 10);
const seed0 = parseInt(process.argv[4] || "1", 10);
const hand = parseInt(process.argv[5] || "24", 10);

function norm(m: string): string {
    if (m.includes("-")) {
        const [from, to] = m.split("-");
        const [f1, f2] = from.split(",");
        const [a, b] = f1 < f2 ? [f1, f2] : [f2, f1];
        return `C:${a}|${b}|${to}`;
    }
    return `P:${m}`;
}

// --- geometry probe -------------------------------------------------------
const gr = variant === "grand" ? new HexTriGraph(5, 9) : new HexTriGraph(4, 7);
const cells = (gr.listCells() as string[]).slice().sort();
const nbrs: any = {};
for (const c of cells) { nbrs[c] = gr.neighbours(c).slice().sort(); }
console.log(JSON.stringify({kind: "geom", variant, cells, nbrs}));

// --- random games ---------------------------------------------------------
for (let gi = 0; gi < nGames; gi++) {
    const rand = rng(seed0 + gi * 7919);
    const g: any = variant === "grand"
        ? GameFactory("attangle", undefined, ["grand"])
        : GameFactory("attangle");
    if (variant === "grand") { g.pieces = [hand, hand]; g.stack[0].pieces = [hand, hand]; }
    const plies: any[] = [];
    let n = 0;
    while (!g.gameover && n < 5000) {
        const ms: string[] = g.moves();
        if (ms.length === 0) { break; }
        const board: any = {};
        for (const [k, v] of g.board.entries()) { board[k] = v.join(""); }
        const chosen = ms[Math.floor(rand() * ms.length)];
        plies.push({p: g.currplayer, board, stock: [...g.pieces],
                    moves: [...new Set(ms.map(norm))].sort(), chosen: norm(chosen)});
        g.move(chosen);
        n++;
    }
    const board: any = {};
    for (const [k, v] of g.board.entries()) { board[k] = v.join(""); }
    console.log(JSON.stringify({kind: "game", game: gi, variant, plies,
        finalBoard: board, finalStock: [...g.pieces], finalP: g.currplayer,
        gameover: g.gameover, winner: g.winner, n}));
}
"""


def run_oracle(root: pathlib.Path, variant: str, games: int, seed: int,
               hand: int) -> list:
    hpath = root / "_attangle_diff_harness.ts"
    hpath.write_text(HARNESS)
    cmd = ["npx", "ts-node", "--transpileOnly",
           "--compilerOptions", '{"module":"commonjs"}',
           hpath.name, variant, str(games), str(seed), str(hand)]
    out = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"oracle failed:\n{out.stderr[-4000:]}")
    return [json.loads(ln) for ln in out.stdout.splitlines() if ln.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--variant", default="both",
                    choices=["attangle", "grand", "both"])
    ap.add_argument("--ap-hand", type=int, default=24)
    ap.add_argument("--gameslib", default=os.environ.get("AP_GAMESLIB", ""))
    args = ap.parse_args()
    if not args.gameslib:
        sys.exit("set AP_GAMESLIB (or --gameslib) to a gameslib checkout")
    root = pathlib.Path(args.gameslib).resolve()

    pkg = pathlib.Path(__file__).resolve().parent
    _man, game = load_from_dir(pkg)
    G = sys.modules[type(game).__module__]

    variants = (["attangle", "grand"] if args.variant == "both"
                else [args.variant])
    bad = 0
    for v in variants:
        tag = "grand" if v == "grand" else "base"
        recs = run_oracle(root, tag, args.games, args.seed, args.ap_hand)
        geom = [r for r in recs if r["kind"] == "geom"][0]
        games = [r for r in recs if r["kind"] == "game"]

        # --- geometry: cell set + adjacency under our alg() mapping ---------
        ours = sorted(G.alg(c, v) for c in G.CELLS[v])
        if ours != geom["cells"]:
            print(f"[{v}] CELL SET MISMATCH")
            bad += 1
        else:
            nb_bad = 0
            for c in G.CELLS[v]:
                mine = sorted(
                    G.alg((c[0] + d[0], c[1] + d[1]), v) for d in G.DIRS
                    if (c[0] + d[0], c[1] + d[1]) in G.CELL_SET[v])
                if mine != geom["nbrs"][G.alg(c, v)]:
                    nb_bad += 1
            if nb_bad:
                print(f"[{v}] ADJACENCY MISMATCH on {nb_bad} cells")
                bad += 1
            else:
                print(f"[{v}] geometry OK: {len(ours)} cells, "
                      f"adjacency identical on every cell")

        plies = 0
        for rec in games:
            s = game.initial_state(options={"variant": v})
            for i, ply in enumerate(rec["plies"]):
                where = f"[{v}] game {rec['game']} ply {i}"
                # board
                mine_b = {G.alg(c, v): "".join(str(o + 1) for o in st)
                          for c, st in s.board.items()}
                if mine_b != ply["board"]:
                    print(f"{where}: BOARD {mine_b} != {ply['board']}")
                    bad += 1
                    break
                if list(s.stock) != ply["stock"]:
                    print(f"{where}: STOCK {list(s.stock)} != {ply['stock']}")
                    bad += 1
                    break
                if s.to_move + 1 != ply["p"]:
                    print(f"{where}: TO-MOVE {s.to_move + 1} != {ply['p']}")
                    bad += 1
                    break
                mine_m = sorted({norm_ours(G, v, m)
                                 for m in game.legal_moves(s)})
                if mine_m != ply["moves"]:
                    only_us = sorted(set(mine_m) - set(ply["moves"]))
                    only_ap = sorted(set(ply["moves"]) - set(mine_m))
                    print(f"{where}: MOVES differ  ours-only={only_us[:6]} "
                          f"ap-only={only_ap[:6]}")
                    bad += 1
                    break
                s = game.apply_move(s, ours_move(G, v, ply["chosen"]))
                plies += 1
            else:
                mine_b = {G.alg(c, v): "".join(str(o + 1) for o in st)
                          for c, st in s.board.items()}
                if mine_b != rec["finalBoard"]:
                    print(f"[{v}] game {rec['game']}: FINAL BOARD differs")
                    bad += 1
                if not game.is_terminal(s):
                    print(f"[{v}] game {rec['game']}: we are NOT terminal "
                          f"but the oracle is")
                    bad += 1
                else:
                    ret = game.returns(s)
                    ours_w = 1 if ret[0] > ret[1] else 2
                    if [ours_w] != rec["winner"]:
                        print(f"[{v}] game {rec['game']}: WINNER {ours_w} "
                              f"!= {rec['winner']}")
                        bad += 1
        print(f"[{v}] {len(games)} games, {plies} positions compared "
              f"(moves + board + stock + side to move)")
    print("MISMATCHES:", bad)
    return 1 if bad else 0


def norm_ours(G, v, m: str) -> str:
    parts = m.split(">")
    if len(parts) == 1:
        return "P:" + G.alg(G._cell(parts[0]), v)
    a, b, t = (G.alg(G._cell(x), v) for x in parts)
    lo, hi = sorted((a, b))
    return f"C:{lo}|{hi}|{t}"


def ours_move(G, v, norm: str) -> str:
    kind, rest = norm.split(":", 1)
    if kind == "P":
        return G._cid(G.from_alg(rest, v))
    a, b, t = rest.split("|")
    return ">".join(G._cid(G.from_alg(x, v)) for x in (a, b, t))


if __name__ == "__main__":
    sys.exit(main())
