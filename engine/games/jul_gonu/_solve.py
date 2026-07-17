"""One-time exhaustive solver for Jul-Gonu (NOT run by the test suite).

What it solves
--------------
The full reachable position graph of Jul-Gonu over states (board, side-to-move),
i.e. the game WITHOUT the positional-superko repetition ban, with retrograde
(backward-induction) win/loss propagation; positions not resolved by the
fixpoint are cycle-bound DRAWs of the ban-free game.

Why that solves the implemented (superko) game when the root resolves:
if the root is a WIN for the mover in the ban-free graph, define dist(s) as the
forced-win depth (WIN: 1 + min over the chosen child; LOSS: 1 + max over all
children). Along any game in which the winner always plays a minimal-dist move,
dist strictly decreases EVERY ply (all successors of a LOSS state are WIN
states of strictly smaller dist) — so no position can ever repeat, the ban
never binds on the winning line, and the opponent only ever has a SUBSET of
ban-free options (possibly becoming stalemated early, which is also a loss).
Hence a resolved WIN/LOSS root value would transfer exactly to the superko
game, with the win forced in <= dist(root) plies. A DRAW root leaves the
superko value undetermined by this method: within the draw region the outcome
genuinely depends on the set of positions already visited (the game is
path-dependent), so memoized/retrograde methods cannot value it, and a naive
path-set DFS over a 1.3M-state draw region is intractable.

The same argument DOES still value every resolved non-root state under superko
play whose history stayed inside the draw region: draw-region positions carry
no dist, so a min-dist winning line (which visits only resolved states of
strictly decreasing dist) can never collide with them — the ban never binds
and the ban-free value holds exactly.

Method: bitboard move generation (differentially checked against game.py's
generator on random positions first), forward BFS from the initial position to
enumerate every reachable state, then queue-based retrograde propagation over
the reversed edge lists.

Result (frozen 2026-07-17, this machine, CPython 3.10, ~4.5 min pure Python):
    reachable states  = 3,412,738   (move edges = 21,039,712)
    state values      = 1,315,354 WIN / 807,911 LOSS / 1,289,473 DRAW
                        (WIN/LOSS from the side-to-move's perspective)
    ROOT              = DRAW (cycle-bound) in the ban-free game
    root successors   = all four opening moves lead to ban-free DRAW positions
So: Jul-Gonu WITHOUT the repetition ban (infinite play scored as a draw) is a
DRAW — neither side can force a win against repetition-shuffling. The superko
ban (and, as a backstop, the caps) is precisely what makes real play decisive;
its exact game value is path-dependent and remains open. This matches the
Zillions implementer's note (via jpneto) that Jul-Gonu "is all about parity and
forced retreat" — the anti-repetition rule, not the capture, is the essence.

Usage:  cd engine && PYTHONPATH=. python3 games/jul_gonu/_solve.py
"""

from __future__ import annotations

import random
import sys
import time
from array import array
from collections import deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # engine/ on path

N = 4
CELLS = N * N
FULL = (1 << CELLS) - 1


def idx(c, r):
    return r * N + c


NEIGH = []      # NEIGH[i] = list of neighbour cell indices
RAYS = []       # RAYS[i]  = list of rays, each an ordered list of cell indices outward
for r in range(N):
    for c in range(N):
        nb, rays = [], []
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cc, rr = c + dc, r + dr
            if 0 <= cc < N and 0 <= rr < N:
                nb.append(idx(cc, rr))
            ray = []
            while 0 <= cc < N and 0 <= rr < N:
                ray.append(idx(cc, rr))
                cc += dc
                rr += dr
            if ray:
                rays.append(ray)
        NEIGH.append(nb)
        RAYS.append(rays)


def successors(own, opp):
    """All (new_own, new_opp) after one slide (+ active custodial capture) by
    the side owning `own`.  Returned with the MOVER's bitboards (caller flips)."""
    out = []
    occ = own | opp
    pieces = own
    while pieces:
        p = pieces & -pieces
        pieces ^= p
        pi = p.bit_length() - 1
        for e in NEIGH[pi]:
            eb = 1 << e
            if occ & eb:
                continue
            no = (own ^ p) | eb
            cap = 0
            for ray in RAYS[e]:
                run = 0
                closed = False
                for cell in ray:
                    cb = 1 << cell
                    if opp & cb:
                        run |= cb
                    elif no & cb:
                        closed = run != 0
                        break
                    else:
                        break
                if closed:
                    cap |= run
            out.append((no, opp ^ cap))
    return out


# ---------------------------------------------------------------------------
# Differential: bitboard generator vs game.py's generator (ban disabled)
# ---------------------------------------------------------------------------

def differential(n_positions=400, seed=7):
    from games.jul_gonu.game import JulGonu, JGState

    g = JulGonu()
    rng = random.Random(seed)

    def to_bb(board):
        b = w = 0
        for (c, r), o in board.items():
            if o == 0:
                b |= 1 << idx(c, r)
            else:
                w |= 1 << idx(c, r)
        return b, w

    def from_succ(own, opp, mover):
        # normalise successor to (black_bb, white_bb)
        return (own, opp) if mover == 0 else (opp, own)

    checked = 0
    s = g.initial_state()
    while checked < n_positions:
        s = JGState(board=dict(s.board), to_move=s.to_move)   # strip history: ban off
        b, w = to_bb(s.board)
        own, opp = (b, w) if s.to_move == 0 else (w, b)
        bb_succ = {from_succ(no, np_, s.to_move) for no, np_ in successors(own, opp)}
        gp_succ = set()
        for mv in g.legal_moves(s):
            s2 = g.apply_move(s, mv)
            gp_succ.add(to_bb(s2.board))
        assert bb_succ == gp_succ, f"MISMATCH at {g.serialize(s)}"
        checked += 1
        moves = g.legal_moves(s)
        if not moves or g.is_terminal(s):
            s = g.initial_state()
            continue
        s = g.apply_move(s, rng.choice(moves))
    print(f"differential OK: bitboard == game.py successors on {checked} positions")


# ---------------------------------------------------------------------------
# Forward BFS + retrograde solve
# ---------------------------------------------------------------------------

def solve():
    t0 = time.time()
    # state key = black | white<<16 | to_move<<32
    init_b = 0b1111                      # row 0
    init_w = 0b1111 << 12                # row 3
    root = init_b | (init_w << 16) | (0 << 32)

    idx_of = {root: 0}
    keys = [root]
    term = bytearray([0])                # 1 => terminal, LOSS for side to move
    succ_flat = array("i")
    succ_start = array("l", [0])

    i = 0
    while i < len(keys):
        k = keys[i]
        b, w, tm = k & FULL, (k >> 16) & FULL, k >> 32
        own, opp = (b, w) if tm == 0 else (w, b)
        if own.bit_count() <= 1:         # reduced to one -> lost
            term[i] = 1
            succ_start.append(len(succ_flat))
        else:
            succs = successors(own, opp)
            if not succs:                # board stalemate -> lost
                term[i] = 1
                succ_start.append(len(succ_flat))
            else:
                ntm = 1 - tm
                for no, np_ in succs:
                    nb, nw = (no, np_) if tm == 0 else (np_, no)
                    nk = nb | (nw << 16) | (ntm << 32)
                    j = idx_of.get(nk)
                    if j is None:
                        j = len(keys)
                        idx_of[nk] = j
                        keys.append(nk)
                        term.append(0)
                    succ_flat.append(j)
                succ_start.append(len(succ_flat))
        i += 1
        if i % 100000 == 0:
            print(f"  BFS {i:>9,} expanded / {len(keys):,} discovered "
                  f"({time.time()-t0:.0f}s)", flush=True)

    n = len(keys)
    n_edges = len(succ_flat)
    print(f"reachable states = {n:,}   edges = {n_edges:,}   "
          f"({time.time()-t0:.0f}s)", flush=True)

    # reversed edges
    pcnt = array("i", bytes(4 * n))
    for j in succ_flat:
        pcnt[j] += 1
    pstart = array("l", [0] * (n + 1))
    for x in range(n):
        pstart[x + 1] = pstart[x] + pcnt[x]
    pflat = array("i", bytes(4 * n_edges))
    cursor = array("l", pstart[:n])
    for v in range(n):
        for e in range(succ_start[v], succ_start[v + 1]):
            j = succ_flat[e]
            pflat[cursor[j]] = v
            cursor[j] += 1
    print(f"reverse edges built ({time.time()-t0:.0f}s)", flush=True)

    # retrograde: val 0=unknown 1=WIN(to move) 2=LOSS(to move)
    val = bytearray(n)
    dist = array("i", bytes(4 * n))
    maxd = array("i", bytes(4 * n))
    deg = array("i", bytes(4 * n))
    for v in range(n):
        deg[v] = succ_start[v + 1] - succ_start[v]
    q = deque()
    for v in range(n):
        if term[v]:
            val[v] = 2
            q.append(v)
    while q:
        v = q.popleft()
        dv, vv = dist[v], val[v]
        if vv == 2:                      # LOSS for its mover -> preds are WIN
            for e in range(pstart[v], pstart[v + 1]):
                p = pflat[e]
                if not val[p]:
                    val[p] = 1
                    dist[p] = dv + 1
                    q.append(p)
        else:                            # WIN for its mover -> preds lose an out
            for e in range(pstart[v], pstart[v + 1]):
                p = pflat[e]
                if not val[p]:
                    if dv > maxd[p]:
                        maxd[p] = dv
                    deg[p] -= 1
                    if deg[p] == 0:
                        val[p] = 2
                        dist[p] = maxd[p] + 1
                        q.append(p)

    wins = sum(1 for v in val if v == 1)
    losses = sum(1 for v in val if v == 2)
    draws = n - wins - losses
    print(f"values: WIN(to-move) {wins:,} / LOSS {losses:,} / DRAW(ban-free) {draws:,}")
    vname = {0: "DRAW", 1: "WIN for White (mover)", 2: "LOSS for White (mover)"}
    labels = ["0,0>0,1", "1,0>1,1", "2,0>2,1", "3,0>3,1"]  # successors() gen order
    for lab, e in zip(labels, range(succ_start[0], succ_start[1])):
        print(f"  opening {lab} -> {vname[val[succ_flat[e]]]}"
              f" (dist {dist[succ_flat[e]]})" if val[succ_flat[e]] else
              f"  opening {lab} -> DRAW (ban-free)")
    rv = val[0]
    name = {0: "DRAW (cycle-bound, ban-free)", 1: "WIN for the mover (Black)",
            2: "LOSS for the mover (Black)"}[rv]
    print(f"ROOT: {name}" + (f", dist = {dist[0]} plies" if rv else ""))
    if rv:
        print("=> transfers exactly to the implemented superko game "
              "(see module docstring for the argument).")
    else:
        print("=> superko value NOT determined by this method (path-dependent).")
    print(f"total runtime {time.time()-t0:.0f}s")
    return rv, dist[0], n


if __name__ == "__main__":
    differential()
    solve()
