#!/usr/bin/env python3
"""Spot-check Push Fight against the COMPLETE SOLUTION of the game.

MANUAL / ONE-TIME (network; not part of the pure-stdlib selftest). Maks Verver
solved Push Fight strongly in 2022 and serves the 86 GB minimized tablebase at
https://styx.verver.ch/pushfight/lookup/perms/<26-char position string>, which
returns the position's status ("T" tie, "W<n>" mover wins in n, "L<n>" mover
loses in n) together with every legal turn grouped by the status it leads to.

The tablebase is indexed with red to move and the anchor on a blue square, so a
position with blue to move is queried with the colours swapped (the rules are
colour-blind, and swapping moves no piece, so turn notation is unchanged).

The solver lists ONE representative move per distinct successor POSITION, not
every move sequence, so per sampled position we check:

  1. every representative move the solver names is a legal turn for us;
  2. our distinct successor positions == the solver's (each obtained by replaying
     its own representative move through our engine) -- this exercises push
     RESOLUTION (where every shoved piece lands, where the anchor ends up), not
     merely legality;
  3. status "W1" <=> our engine has a turn that immediately wins.

(The third case one would like to check -- a "cannot push" stuck-loss, which the
solver reports as "L0" -- appears not to exist in the standard 3+2 game; see
rules.md, "Correctness anchors".)

    python3 _diff_solver.py [n_probes]
"""
from __future__ import annotations

import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir                                   # noqa: E402

BASE = "https://styx.verver.ch/pushfight/lookup/perms/"
SWAP = str.maketrans("oOPxXY", "xXYoOP")
DELAY = 1.0                                     # be polite to a volunteer's server


def cell_of(name):
    """'d2' -> the engine's cell id '3,1'."""
    return f"{ord(name[0]) - ord('a')},{int(name[1:]) - 1}"


def query(perm):
    url = BASE + urllib.parse.quote(perm, safe="")
    with urllib.request.urlopen(url, timeout=60) as fh:
        return json.load(fh)


def turn_set(g, mod, s):
    """All legal turns, and the successor positions split by how the turn ended.

    Returns (turns, ongoing, winning, suicidal): `ongoing` are positions where
    play continues, `winning` where the mover shoved an opponent piece off, and
    `suicidal` where the mover shoved one of their OWN pieces off (legal, but an
    instant loss -- the solver never names those, since they leave its graph).
    """
    turns, ongoing, winning, suicidal = set(), set(), set(), set()

    def walk(st, path):
        for mv in g.legal_moves(st):
            src, dst = mv.split(">")
            leg = f"{mod.alg(src)}-{mod.alg(dst)}"
            nxt = g.apply_move(st, mv)
            if dst in st.board:
                turns.add(",".join(path + [leg]))
                bucket = (ongoing if nxt.winner is None
                          else winning if nxt.winner == s.to_move else suicidal)
                bucket.add(encode(mod, nxt))
            else:
                walk(nxt, path + [leg])

    walk(s, [])
    return turns, ongoing, winning, suicidal


def wins_now(g, s):
    """True if the mover has a turn that ends the game in their favour."""
    def walk(st):
        for mv in g.legal_moves(st):
            nxt = g.apply_move(st, mv)
            src, dst = mv.split(">")
            if dst in st.board:
                if nxt.winner == s.to_move:
                    return True
            elif walk(nxt):
                return True
        return False
    return walk(s)


def encode(mod, s):
    p = mod.perm_string(s.board, s.anchor)
    return p.translate(SWAP) if s.to_move == 1 else p


def main():
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 25
    pkg = Path(__file__).resolve().parent
    man, g = load_from_dir(pkg)
    mod = sys.modules[type(g).__module__]

    live = []
    rng = random.Random(4242)
    while len(live) < want:
        s = g.initial_state(options={"setup": "standard" if len(live) % 2 else "free"})
        while not g.is_terminal(s):
            if not g._placing(s) and s.moves_used == 0 and s.anchor is not None:
                live.append(s)
            s = g.apply_move(s, rng.choice(g.legal_moves(s)))
    live = live[:want]

    ok = bad = 0
    counts = {}
    for s in live:
        data = query(encode(mod, s))
        time.sleep(DELAY)
        reps = set()
        for grp in data["successors"]:
            reps.update(grp["moves"])
        # The solver's successor positions, obtained by replaying its own moves
        # through our engine (so a wrong landing square shows up as a set diff).
        theirs = set()
        for turn in reps:
            st = s
            for leg in turn.split(","):
                a, b = leg.split("-")
                st = g.apply_move(st, f"{cell_of(a)}>{cell_of(b)}")
            theirs.add(encode(mod, st))

        ours, ongoing, winning, suicidal = turn_set(g, mod, s)
        status = data["status"]
        counts[status[:1]] = counts.get(status[:1], 0) + 1
        problems = []
        if not reps <= ours:
            problems.append(f"{len(reps - ours)} solver moves we call illegal")
        expect = ongoing | winning
        if expect != theirs:
            problems.append(f"successors differ (+{len(expect - theirs)} / "
                            f"-{len(theirs - expect)})")
        if (status == "W1") != wins_now(g, s):
            problems.append(f"mate-in-1 disagreement (solver={status})")
        if problems:
            bad += 1
            print(f"MISMATCH {encode(mod, s)} {status}: {'; '.join(problems)}")
        else:
            ok += 1
            print(f"ok {encode(mod, s)} {status:>4}  {len(theirs)} successors "
                  f"({len(winning)} winning), {len(suicidal)} suicidal, "
                  f"{len(ours)} legal turns")

    print(f"\n{ok} ok / {bad} mismatched; status histogram {counts}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
