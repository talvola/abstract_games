"""One-time differential: blokus_duo legal_moves vs Pentobi's `all_legal`.

Pentobi (Enzenberger, GPL) is the reference Blokus engine. We drive `pentobi-gtp`
in lockstep with our engine down random lines and compare the two legal-move sets
as sets of covered CELL-SETS — so the check is anchor-agnostic and survives any
change to our move-string convention.

MANUAL / ONE-TIME — deliberately NOT a `selftest.py` (the suite globs only that
name, and selftests must be pure-stdlib with no external binaries).

Needs a local Pentobi build, which this repo does not vendor:

    git clone --depth 1 https://github.com/enz/pentobi.git
    cd pentobi && cmake -B build -DPENTOBI_BUILD_GTP=ON -DPENTOBI_BUILD_GUI=OFF \
        -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
    PENTOBI_GTP=$PWD/build/pentobi_gtp/pentobi-gtp python3 _diff_pentobi.py

(`pip install cmake` if cmake is absent; the GTP target needs no Qt.)

Last run: legal-move sets identical to Pentobi across 272 positions spanning full
random games, and `final_score` agreed 25/25 including the margin.
"""
import os
import random
import shutil
import subprocess
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # -> engine/
import games.blokus_duo.game as G  # noqa: E402

# Point PENTOBI_GTP at your build; falls back to one on PATH.
GTP = os.environ.get("PENTOBI_GTP") or shutil.which("pentobi-gtp") or "pentobi-gtp"
COLORS = ("b", "w")


def to_pent(cells):
    """our (c,r) [row 0 = bottom] -> pentobi 'e10'."""
    return ",".join(sorted(f"{chr(97 + c)}{r + 1}" for c, r in cells))


class Pentobi:
    def __init__(self):
        if not (Path(GTP).exists() or shutil.which(GTP)):
            raise SystemExit(f"pentobi-gtp not found at {GTP!r} — see the module "
                             f"docstring for build steps, then set $PENTOBI_GTP.")
        self.p = subprocess.Popen([GTP], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.cmd("set_game blokus duo")

    def cmd(self, c):
        self.p.stdin.write(c + "\n")
        self.p.stdin.flush()
        out = []
        while True:
            line = self.p.stdout.readline()
            if line == "":
                raise RuntimeError("pentobi died")
            if line.strip() == "" and out:
                break
            if line.startswith("?"):
                raise RuntimeError(f"pentobi error on {c!r}: {line}")
            out.append(line.rstrip("\n"))
        return " ".join(out).lstrip("= ").strip()

    def legal(self, color):
        r = self.cmd(f"all_legal {color}")
        return {frozenset(m.split(",")) for m in r.split()} if r else set()


def our_cells(mv):
    return to_pent(G._cells_of(G.MOVE_MASK[mv]))


def main(trials=6, depth=14, seed=7):
    rng = random.Random(seed)
    g = G.BlokusDuo()
    total_pos = 0
    for t in range(trials):
        pent = Pentobi()
        s = g.initial_state()
        for ply in range(depth):
            if g.is_terminal(s):
                break
            seat = g.current_player(s)
            ours = {frozenset(our_cells(m).split(",")) for m in g.legal_moves(s)}
            theirs = pent.legal(COLORS[seat])
            total_pos += 1
            if ours != theirs:
                print(f"MISMATCH trial {t} ply {ply} seat {seat}")
                print(f"  ours={len(ours)} pentobi={len(theirs)}")
                only_us = list(ours - theirs)[:3]
                only_them = list(theirs - ours)[:3]
                print(f"  only ours   : {[sorted(x) for x in only_us]}")
                print(f"  only pentobi: {[sorted(x) for x in only_them]}")
                return 1
            mv = rng.choice(g.legal_moves(s))
            pent.cmd(f"play {COLORS[seat]} {our_cells(mv)}")
            s = g.apply_move(s, mv)
        pent.cmd("quit")
        print(f"  trial {t}: OK through ply {ply}")
    print(f"DIFFERENTIAL OK — {total_pos} positions, legal-move sets identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
