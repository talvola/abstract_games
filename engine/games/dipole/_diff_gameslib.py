#!/usr/bin/env python3
"""Differential: this Dipole engine vs the AbstractPlay `gameslib` reference.

MANUAL / ONE-TIME -- needs node + a clone of https://github.com/AbstractPlay/gameslib
(MIT).  The reference is used as an ORACLE ONLY; no code is copied from it.
It is env-gated so it never runs inside the pure-stdlib test suite:

    AP_GAMESLIB=/path/to/gameslib python3 games/dipole/_diff_gameslib.py [games]

What is compared, at EVERY ply of every game, in BOTH engines' own notation
(following `games/blokus/_diff_pentobi.py`: compare the SEMANTIC object -- here
the set of (from, to) SQUARE PAIRS -- never the move strings, which differ):

  * the full set of on-board moves, as `{"e1-h4", ...}` algebraic pairs;
  * the set of squares that can bear off;
  * the whole board (square -> owner + stack height);
  * whose turn it is, whether the game is over, and who won.

KNOWN DIVERGENCE (the rulebook wins).  gameslib's move notation is `from-off`,
with no room for a count, and its `move()` always bears off the MINIMUM number
of checkers that reaches an edge.  The rulebook allows any sub-stack whose
destination falls outside the board, so from a 12-stack on e1 there are NINE
distinct legal bear-offs (4..12), not one.  This harness therefore drives both
engines with the minimum-count bear-off only, and compares the SET OF SQUARES
that can bear off rather than the counts.
"""

import json
import os
import random
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir                              # noqa: E402

PKG = Path(__file__).resolve().parent
MAN, G = load_from_dir(PKG)
M = sys.modules[type(G).__module__]

DRIVER = r"""
import { GameFactory } from "./src/games";
const inp = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out: any = { games: [] };
for (const game of inp.games) {
  const g: any = GameFactory("dipole", undefined, inp.variants || undefined);
  const plies: any[] = [];
  const snap = () => {
    const raw: string[] = g.gameover ? [] : g.moves();
    const valid = [...new Set(raw.filter((m: string) => m === "pass" || g.validateMove(m).valid))];
    plies.push({
      currplayer: g.currplayer,
      board: Object.fromEntries([...g.board.entries()]),
      moves: valid.sort(),
      gameover: g.gameover,
      winner: g.winner,
    });
  };
  for (const [who, mv] of game.moves) {
    let guard = 0;
    while (!g.gameover && g.currplayer !== who) {
      if (guard++ > 4) throw new Error("pass loop");
      const ms = g.moves();
      if (ms.length !== 1 || ms[0] !== "pass") throw new Error("expected pass, got " + JSON.stringify(ms));
      g.move("pass");
    }
    snap();
    g.move(mv);
  }
  snap();
  // gameslib's checkEOG only looks at whether the PLAYER WHO JUST MOVED has
  // been wiped out, so a win by capturing the opponent's last stack is only
  // noticed one ply later, after the wiped-out player passes.  Settle it.
  let guard2 = 0;
  while (!g.gameover && guard2++ < 3) {
    const ms = g.moves();
    if (ms.length !== 1 || ms[0] !== "pass") break;
    g.move("pass");
  }
  plies[plies.length - 1].settled = { gameover: g.gameover, winner: g.winner };
  out.games.push({ plies });
}
console.log(JSON.stringify(out));
"""


def ap_moveset(g, s):
    """Our legal moves, expressed the way gameslib expresses them."""
    pairs, offs = set(), set()
    for m in g.legal_moves(s):
        frm, to, _k = g.parse(m)
        if to is None:
            offs.add(M.alg(*frm))
        else:
            pairs.add(f"{M.alg(*frm)}-{M.alg(*to)}")
    return pairs, offs


def ap_board(s):
    return {M.alg(c, r): [o + 1, h] for (c, r), (o, h) in s.board.items()}


def their_moveset(entry):
    """gameslib's move list -> the same two sets."""
    pairs, offs = set(), set()
    for m in entry["moves"]:
        if m == "pass":
            continue
        frm, to = m, ""
        for sep in "-+x":                       # gameslib: move / merge / capture
            if sep in m:
                frm, to = m.split(sep, 1)
                break
        if to == "off":
            offs.add(frm)
        else:
            pairs.add(f"{frm}-{to}")
    return pairs, offs


def min_off(g, s, cell):
    """The bear-off gameslib would execute from `cell`: the smallest count."""
    ks = [g.parse(m)[2] for m in g.legal_moves(s)
          if ">off=" in m and g.parse(m)[0] == cell]
    return min(ks) if ks else None


def main():
    root = os.environ.get("AP_GAMESLIB")
    if not root:
        print("AP_GAMESLIB not set -- skipping (manual/one-time harness).")
        return 0
    ngames = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    root = Path(root)
    drv = root / "_dipole_diff_driver.ts"
    drv.write_text(DRIVER)

    rng = random.Random(20070501)
    totals = {"plies": 0, "moves": 0, "mismatch": 0, "games": 0, "late": 0}
    for variants, size in ((None, 8), (["international"], 10)):
        payload = {"variants": variants, "games": []}
        ours = []
        for _ in range(ngames):
            s = G.initial_state(options={"size": size})
            seq, snaps = [], []
            while not G.is_terminal(s):
                snaps.append(s)
                # Only play moves gameslib can express: on-board moves, and the
                # minimum-count bear-off from each square.
                cand = []
                for m in G.legal_moves(s):
                    frm, to, k = G.parse(m)
                    if to is not None:
                        occ = s.board.get(to)
                        sep = "-" if occ is None else ("+" if occ[0] == s.to_move else "x")
                        cand.append((m, f"{M.alg(*frm)}{sep}{M.alg(*to)}"))
                    elif k == min_off(G, s, frm):
                        cand.append((m, f"{M.alg(*frm)}-off"))
                m, apm = rng.choice(cand)
                seq.append([s.to_move + 1, apm])
                s = G.apply_move(s, m)
            snaps.append(s)
            payload["games"].append({"moves": seq})
            ours.append(snaps)

        res = subprocess.run(
            ["npx", "ts-node", "--transpileOnly", "--compilerOptions",
             '{"module":"commonjs"}', str(drv)],
            cwd=root, input=json.dumps(payload), capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout[-2000:], res.stderr[-3000:])
            return 1
        theirs = json.loads(res.stdout.splitlines()[-1])

        for gi, (snaps, tg) in enumerate(zip(ours, theirs["games"])):
            totals["games"] += 1
            for pi, (s, t) in enumerate(zip(snaps, tg["plies"])):
                totals["plies"] += 1
                op, oo = ap_moveset(G, s)
                tp, to_ = their_moveset(t)
                totals["moves"] += len(op) + len(oo)
                bad = []
                if op != tp:
                    bad.append(f"moves ours-theirs={sorted(op - tp)} theirs-ours={sorted(tp - op)}")
                if oo != to_:
                    bad.append(f"bear-off squares ours={sorted(oo)} theirs={sorted(to_)}")
                if ap_board(s) != {k: list(v) for k, v in t["board"].items()}:
                    bad.append(f"board ours={ap_board(s)} theirs={t['board']}")
                if not s.over and s.to_move + 1 != t["currplayer"]:
                    bad.append(f"to_move ours={s.to_move + 1} theirs={t['currplayer']}")
                # gameslib settles the end of game one ply late when the win
                # comes from capturing the opponent's LAST stack (its checkEOG
                # only inspects the player who just moved), so at a terminal we
                # compare against its SETTLED verdict.
                tover, twin = t["gameover"], t["winner"]
                if "settled" in t and not tover:
                    tover, twin = t["settled"]["gameover"], t["settled"]["winner"]
                    if tover:
                        totals["late"] += 1
                if s.over != tover:
                    bad.append(f"gameover ours={s.over} theirs={tover}")
                if s.over and s.winner is not None and twin != [s.winner + 1]:
                    bad.append(f"winner ours={s.winner + 1} theirs={twin}")
                if bad:
                    totals["mismatch"] += 1
                    print(f"size {size} game {gi} ply {pi}: " + "; ".join(bad))
        print(f"size {size}: {ngames} games compared")

    drv.unlink(missing_ok=True)
    print(f"dipole vs gameslib: {totals['games']} games, {totals['plies']} positions, "
          f"{totals['moves']} moves compared, {totals['mismatch']} mismatches, "
          f"{totals['late']} games where gameslib settled the win one ply late")
    return 1 if totals["mismatch"] else 0


if __name__ == "__main__":
    sys.exit(main())
