"""One-time full solve of Hobak Gonu (both invasion variants).

Graph: 11 points ("c,r" on a virtual 5x5 grid), 14 edges (Ludii Ho-Bag Gonu.lud,
confirmed against the nol2i figures).

Rules (consensus reconstruction, see rules.md):
  - step to adjacent empty point along a line
  - no move may end on a home-row ENDPOINT (endpoints are exit-only)
  - own home MIDDLE may only be entered from own endpoints (funnel)
  - circle: free movement
  - enemy home row:
      closed: never enterable (namu/lflank)
      trap:   middle enterable from the circle; once inside the enemy row a
              piece may move within it (middle<->endpoints) but never leave
              (nol2i rule 4 / Ludii)
  - player to move with no legal move loses
  - cycle-bound positions = draw (in-game rule: first positional repetition)
"""
from collections import deque

# point ids
H0 = [(0, 4), (2, 4), (4, 4)]   # seat 0 home (bottom): end, mid, end
H1 = [(0, 0), (2, 0), (4, 0)]   # seat 1 home (top)
MID = {0: (2, 4), 1: (2, 0)}
ENDS = {0: {(0, 4), (4, 4)}, 1: {(0, 0), (4, 0)}}
HOME = {0: set(H0), 1: set(H1)}
CIRCLE = {(2, 3), (1, 2), (2, 2), (3, 2), (2, 1)}
POINTS = H0 + [(2, 3), (1, 2), (2, 2), (3, 2), (2, 1)] + H1
IDX = {p: i for i, p in enumerate(POINTS)}

EDGES = [
    ((0, 4), (2, 4)), ((2, 4), (4, 4)),            # bottom home row
    ((0, 0), (2, 0)), ((2, 0), (4, 0)),            # top home row
    ((2, 4), (2, 3)), ((2, 0), (2, 1)),            # connectors
    ((2, 3), (1, 2)), ((1, 2), (2, 1)),            # ring arcs
    ((2, 1), (3, 2)), ((3, 2), (2, 3)),
    ((2, 2), (2, 3)), ((2, 2), (1, 2)),            # spokes
    ((2, 2), (3, 2)), ((2, 2), (2, 1)),
]
ADJ = {p: [] for p in POINTS}
for a, b in EDGES:
    ADJ[a].append(b)
    ADJ[b].append(a)


def legal_dst(p, src, dst, variant):
    """May player p move a piece from src to dst (dst known empty+adjacent)?"""
    opp = 1 - p
    if dst in CIRCLE:
        return src not in HOME[opp]          # trap: no exit from enemy row
    if dst == MID[p]:
        return src in ENDS[p]                # funnel: own mid only from own ends
    if dst in ENDS[p]:
        return False                         # own endpoints exit-only
    # dst in enemy row
    if variant == "closed":
        return False
    # trap variant
    if src in HOME[opp]:
        return True                          # move within enemy row
    return dst == MID[opp] and src in CIRCLE  # enter at the middle only


def moves(state, variant):
    occ, tm = state
    out = []
    for i, owner in enumerate(occ):
        if owner != tm:
            continue
        src = POINTS[i]
        for dst in ADJ[src]:
            if occ[IDX[dst]] is None and legal_dst(tm, src, dst, variant):
                out.append((i, IDX[dst]))
    return out


def apply(state, mv):
    occ, tm = state
    occ = list(occ)
    occ[mv[1]] = occ[mv[0]]
    occ[mv[0]] = None
    return (tuple(occ), 1 - tm)


def initial():
    occ = [None] * 11
    for pt in H0:
        occ[IDX[pt]] = 0
    for pt in H1:
        occ[IDX[pt]] = 1
    return (tuple(occ), 0)


def solve(variant):
    root = initial()
    # forward BFS
    succs = {}
    q = deque([root])
    succs[root] = None
    order = []
    n_edges = 0
    while q:
        s = q.popleft()
        ms = [apply(s, m) for m in moves(s, variant)]
        succs[s] = ms
        n_edges += len(ms)
        order.append(s)
        for t in ms:
            if t not in succs:
                succs[t] = None
                q.append(t)
    # predecessors + degrees
    preds = {s: [] for s in succs}
    for s, ms in succs.items():
        for t in ms:
            preds[t].append(s)
    # retrograde: value from perspective of the player to move
    # LOSS: no moves. WIN: some successor is LOSS. LOSS: all successors WIN.
    val = {}
    dist = {}
    deg = {s: len(ms) for s, ms in succs.items()}
    q = deque()
    for s, ms in succs.items():
        if not ms:
            val[s] = "LOSS"
            dist[s] = 0
            q.append(s)
    while q:
        s = q.popleft()
        for p in preds[s]:
            if p in val:
                continue
            if val[s] == "LOSS":
                val[p] = "WIN"
                dist[p] = dist[s] + 1
                q.append(p)
            else:
                deg[p] -= 1
                if deg[p] == 0:
                    val[p] = "LOSS"
                    dist[p] = 1 + max(dist[t] for t in succs[p])
                    q.append(p)
    nwin = sum(1 for v in val.values() if v == "WIN")
    nloss = sum(1 for v in val.values() if v == "LOSS")
    ndraw = len(succs) - nwin - nloss
    rootval = val.get(root, "DRAW")
    print(f"[{variant}] reachable={len(succs)} edges={n_edges} "
          f"WIN={nwin} LOSS={nloss} DRAW={ndraw} "
          f"root={rootval}" + (f" dist={dist[root]}" if root in val else ""))
    # a few sample solved positions for freezing
    terms = [s for s, ms in succs.items() if not ms]
    print(f"   terminal(stuck) positions reachable: {len(terms)}")
    # find a shortest scripted win line from root if root is WIN, else a
    # shortest path to any terminal for the blockade selftest probe
    path = shortest_terminal_line(root, succs)
    if path is not None:
        print(f"   shortest line root->stuck: {len(path)-1} plies")
        print("   line:", [fmt(s) for s in path[:1]], "...")
        mvs = []
        for a, b in zip(path, path[1:]):
            mvs.append(diff_move(a, b))
        print("   moves:", mvs)
    return val, dist, succs, root


def shortest_terminal_line(root, succs):
    prev = {root: None}
    q = deque([root])
    while q:
        s = q.popleft()
        if not succs[s]:
            path = []
            while s is not None:
                path.append(s)
                s = prev[s]
            return path[::-1]
        for t in succs[s]:
            if t not in prev:
                prev[t] = s
                q.append(t)
    return None


def fmt(state):
    occ, tm = state
    return "".join("." if o is None else str(o) for o in occ) + f"/{tm}"


def diff_move(a, b):
    oa, ob = a[0], b[0]
    src = dst = None
    for i in range(11):
        if oa[i] is not None and ob[i] is None:
            src = POINTS[i]
        if oa[i] is None and ob[i] is not None:
            dst = POINTS[i]
    return f"{src[0]},{src[1]}>{dst[0]},{dst[1]}"


if __name__ == "__main__":
    import time
    for variant in ("closed", "trap"):
        t0 = time.time()
        solve(variant)
        print(f"   ({time.time()-t0:.2f}s)")
