"""One-time differential: blokus legal_moves vs Pentobi's `all_legal`.

Pentobi (Enzenberger, GPL) is the reference Blokus engine. We drive `pentobi-gtp`
in lockstep with our engine down random lines and compare the two legal-move sets
as sets of covered CELL-SETS — so the check is anchor-agnostic and survives any
change to our move-string convention.

Adapted from games/blokus_duo/_diff_pentobi.py. Two differences for the classic
4-player game: the game name is `blokus` (not `blokus duo`), and the colours are
`1`/`2`/`3`/`4` (the `b`/`w` names are duo-only).

MANUAL / ONE-TIME — deliberately NOT a `selftest.py` (the suite globs only that
name, and selftests must be pure-stdlib with no external binaries).

Needs a local Pentobi build, which this repo does not vendor:

    git clone --depth 1 https://github.com/enz/pentobi.git
    cd pentobi && cmake -B build -DPENTOBI_BUILD_GTP=ON -DPENTOBI_BUILD_GUI=OFF \
        -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
    PENTOBI_GTP=$PWD/build/pentobi_gtp/pentobi-gtp python3 _diff_pentobi.py

(`pip install cmake` if cmake is absent; the GTP target needs no Qt.)

Last run: legal-move sets identical to Pentobi across 367 positions spanning six
complete random games (each played out to a real terminal, 58-64 plies),
including the 58-move opening for all four seats; `final_score` agreed on every
seat of all 6 finished games (modulo the fixed score-origin offset documented at
the score check below).
"""
import os
import random
import shutil
import subprocess
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # -> engine/
import games.blokus.game as G  # noqa: E402

# Point PENTOBI_GTP at your build; falls back to one on PATH.
GTP = os.environ.get("PENTOBI_GTP") or shutil.which("pentobi-gtp") or "pentobi-gtp"
# Classic Blokus colours in play order: blue, yellow, red, green = our seats 0..3.
COLORS = ("1", "2", "3", "4")
# Unit squares in one colour's 21 pieces (1+2+3+3+5*4+12*5) — the constant offset
# between Pentobi's score origin and the rulebook's (see the score check below).
TOTAL_SQUARES = sum(G.SIZES[k] for k in G.PIECES)


def to_pent(cells):
    """our (c,r) [row 0 = bottom] -> pentobi 'a20'."""
    return ",".join(sorted(f"{chr(97 + c)}{r + 1}" for c, r in cells))


class Pentobi:
    def __init__(self):
        if not (Path(GTP).exists() or shutil.which(GTP)):
            raise SystemExit(f"pentobi-gtp not found at {GTP!r} — see the module "
                             f"docstring for build steps, then set $PENTOBI_GTP.")
        self.p = subprocess.Popen([GTP], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        # The FULL game name; "classic" is not accepted.
        self.cmd("set_game blokus")

    def cmd(self, c):
        """Send one GTP command, read the whole (possibly MULTI-LINE) response.

        `all_legal` answers with many lines terminated by a blank one — reading a
        single line would silently under-report the move list.
        """
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

    def score(self):
        return self.cmd("final_score")


def our_cells(mv):
    return to_pent(G._cells_of(G.MOVE_MASK[mv]))


def main(trials=6, depth=90, seed=7):
    # depth 90 > 4*21 pieces, so every trial plays out to a real terminal and
    # its final scores get cross-checked too.
    rng = random.Random(seed)
    g = G.Blokus()
    total_pos = 0
    scored = 0
    for t in range(trials):
        pent = Pentobi()
        s = g.initial_state()
        ply = 0
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

        # Cross-check the SCORES too, whenever the line ran to a real terminal.
        #
        # CONVENTION: Pentobi's `final_score` counts the squares a colour has
        # PLACED (plus the same +15/+5 bonuses), while the R1983 rulebook — and
        # therefore we — count -1 per REMAINING unit square. The two origins
        # differ by exactly TOTAL_SQUARES (89) for every colour, so they induce
        # the identical ranking; the rulebook's own worked example (+20 / -8 /
        # -24 / -20) confirms our origin is the published one. Comparing with the
        # offset still checks the remaining-square count AND both bonuses.
        if g.is_terminal(s):
            ours_sc = [g.score(s, p) for p in range(4)]
            theirs_sc = [int(x) for x in pent.score().split()]
            if [x + TOTAL_SQUARES for x in ours_sc] != theirs_sc:
                print(f"SCORE MISMATCH trial {t}: ours={ours_sc} "
                      f"(+{TOTAL_SQUARES} = {[x + TOTAL_SQUARES for x in ours_sc]}) "
                      f"pentobi={theirs_sc}")
                return 1
            scored += 1
            print(f"  trial {t}: OK through ply {ply} (terminal), score {ours_sc} agrees")
        else:
            print(f"  trial {t}: OK through ply {ply}")
        pent.cmd("quit")
    print(f"DIFFERENTIAL OK — {total_pos} positions, legal-move sets identical; "
          f"{scored} final scores agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
