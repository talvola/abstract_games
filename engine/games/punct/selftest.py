#!/usr/bin/env python3
"""PÜNCT correctness anchor — pure-stdlib, fast.

No published perft exists for PÜNCT, so the anchor is a set of baked rule
assertions on hand-built positions, verifying:

  (1) the hexagonal board geometry (side-9 hexagon, 6 corners clipped → 211
      fields; three pairs of opposite edges);
  (2) the three piece shapes (straight / angular / triangular), each covering
      THREE connected fields, placed flat on empty fields OR stacked on top of
      lower pieces per the support + bridging rule;
  (3) the TOP piece at a field determines its colour for connection;
  (4) WIN = a connected chain of your colour (top pieces) linking your two
      OPPOSITE board edges (BFS like Hex), reached via apply_move;
  plus a hand-built flat placement, a legal stack-on-top (and the illegal
  PÜNCT-on-opponent case), and a legal BRIDGE move.

Run:  PYTHONPATH=. python3 games/punct/selftest.py
"""

import sys

from games.punct.game import (
    Punct, PunctState, Piece,
    board_cells, neighbors, on_board, edge_of, connects,
    shape_offsets, shape_of, top_owner, field_stacks, height_at,
    piece_immobile, add_move, move_move, RADIUS,
)


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def find_move(game, state, predicate):
    """Return a legal move matching `predicate(kind, src, punct, minors_set)`."""
    from games.punct.game import parse
    for m in game.legal_moves(state):
        kind, src, punct, minors = parse(m)
        if predicate(kind, src, punct, frozenset(minors)):
            return m
    return None


def main():
    g = Punct()

    # ---------------------------------------------------------------- (1) board
    cells = board_cells()
    check(len(cells) == 211, f"board must have 211 fields, got {len(cells)}")
    # it is a side-9 hexagon (max coord 8) with the 6 single corners removed
    check((0, 0) in cells, "centre field must be on board")
    for corner in [(-8, 0), (-8, 8), (0, -8), (0, 8), (8, -8), (8, 0)]:
        check(corner not in cells, f"corner {corner} must be clipped")
    # every field within radius 8
    for (q, r) in cells:
        check(max(abs(q), abs(r), abs(-q - r)) <= RADIUS, f"{q,r} out of hexagon")
    # three pairs of opposite edges (one per cube axis): each non-empty & disjoint
    for axis in (0, 1, 2):
        pos = [c for c in cells if edge_of(c, axis, +1)]
        neg = [c for c in cells if edge_of(c, axis, -1)]
        check(pos and neg, f"axis {axis} must have both opposite edges")
        check(not (set(pos) & set(neg)), f"axis {axis} edges must be disjoint")

    # --------------------------------------------------------------- (2) shapes
    forms = shape_offsets()
    check(set(forms) == {"straight", "angular", "triangular"}, "three shape kinds")
    # each oriented placement covers THREE connected fields
    for kind, lst in forms.items():
        check(lst, f"{kind} must have orientations")
        for (a, b) in lst:
            cells3 = [(0, 0), a, b]
            # connectivity: the 3 cells form one connected group
            seen = {(0, 0)}
            stack = [(0, 0)]
            while stack:
                x = stack.pop()
                for nb in neighbors(x):
                    if nb in (a, b) and nb not in seen:
                        seen.add(nb)
                        stack.append(nb)
            check(len(seen) == 3, f"{kind} {a,b} must be 3 connected fields")
            check(shape_of(a, b) == kind, f"shape_of mis-classifies {kind} {a,b}")
    # straight = 3 collinear (some orientation has minors at +d and -d through punct)
    check(any(a == (-b[0], -b[1]) for (a, b) in forms["straight"]),
          "straight must include a middle-anchored (opposite minors) orientation")
    # straight must ALSO include an end-anchored orientation (a minor 2 steps away)
    check(any(max(abs(a[0]), abs(a[1]), abs(a[0] + a[1])) == 2
              or max(abs(b[0]), abs(b[1]), abs(b[0] + b[1])) == 2
              for (a, b) in forms["straight"]),
          "straight must include an end-anchored orientation (enables bridging)")
    # triangular = three mutually-adjacent fields
    for (a, b) in forms["triangular"]:
        check((b[0] - a[0], b[1] - a[1]) in
              [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)],
              f"triangular minors {a,b} must be adjacent to each other")

    # ------------------------------------------------- (2b/3) flat placement
    s = g.initial_state()
    check(g.current_player(s) == 0, "White moves first")
    legal = g.legal_moves(s)
    check(all(m.startswith("P") for m in legal), "opening moves are all placements")
    # opening restriction: the first piece may not touch the central hexagon
    central = {(0, 0)} | set(neighbors((0, 0)))
    from games.punct.game import parse as _parse
    for m in legal:
        _, _, punct, minors = _parse(m)
        check(not ({punct, minors[0], minors[1]} & central),
              "first piece must not touch the central hexagon")
    # apply one flat placement and verify per-field top colour. Find the engine's
    # canonical move string covering the three target fields (a straight piece).
    target = {(4, -7), (5, -7), (3, -7)}
    flat = None
    for m in legal:
        _, _, p, mn = _parse(m)
        if {p, mn[0], mn[1]} == target:
            flat = m
            break
    check(flat is not None, "a flat straight placement on three empty fields must be legal")
    s1 = g.apply_move(s, flat)
    top = top_owner(s1.pieces)
    for c in ((4, -7), (5, -7), (3, -7)):
        check(top.get(c) == 0, f"flat piece must top {c} as White")
    check(s1.reserve[0] == 17, "reserve decrements after adding a piece")
    check(g.current_player(s1) == 1, "turn passes to Black after a placement")

    # --------------------------------------------- (2c) legal stack-on-top
    base = Piece(0, (0, 0), ((1, 0), (0, 1)), 0)            # White triangular base
    mover = Piece(0, (3, 0), ((4, 0), (3, 1)), 0)          # White triangular mover
    ss = PunctState(pieces=[base, mover], reserve=(0, 0),
                    to_move=0, winner=None, ply=10)
    stack_mv = find_move(
        g, ss,
        lambda k, src, p, mn: src == (3, 0) and p == (0, 0)
        and mn == frozenset({(1, 0), (0, 1)}))
    check(stack_mv is not None,
          "PÜNCT must be able to jump on top of an OWN piece")
    s2 = g.apply_move(ss, stack_mv)
    stk = field_stacks(s2.pieces)
    for c in ((0, 0), (1, 0), (0, 1)):
        check(height_at(stk, c) == 2, f"{c} must be 2 high after stacking")
    check(top_owner(s2.pieces)[(0, 0)] == 0, "top of stack stays White")
    check(piece_immobile(s2.pieces, 0, stk),
          "a covered piece (the base) must be immobilised")
    check(g.serialize(g.deserialize(g.serialize(s2))) == g.serialize(s2),
          "serialize must round-trip")

    # illegal: a PÜNCT may NEVER land on an opponent's piece
    baseB = Piece(1, (0, 0), ((1, 0), (0, 1)), 0)          # Black base
    moverW = Piece(0, (3, 0), ((4, 0), (3, 1)), 0)         # White mover
    sb = PunctState(pieces=[baseB, moverW], reserve=(0, 0),
                    to_move=0, winner=None, ply=10)
    check(not any(m.startswith("3,0>P0,0") for m in g.legal_moves(sb)),
          "PÜNCT must NOT be allowed to land on an opponent's piece")

    # --------------------------------------------- (2d) legal BRIDGE move
    # Two White pillars under (0,0) and (-2,0); the gap (-1,0) is empty at base.
    # A White straight piece slides its PÜNCT to (0,0): far end lands on the
    # second pillar, the MIDDLE minor bridges the empty gap.
    pillar1 = Piece(0, (0, 0), ((0, 1), (1, 0)), 0)
    pillar2 = Piece(0, (-2, 0), ((-2, 1), (-3, 1)), 0)
    brmover = Piece(0, (3, 0), ((4, 0), (5, 0)), 0)        # straight, end-anchored
    check(brmover.shape() == "straight", "bridge mover must be straight")
    sbr = PunctState(pieces=[pillar1, pillar2, brmover], reserve=(0, 0),
                     to_move=0, winner=None, ply=10)
    bridge_mv = find_move(
        g, sbr,
        lambda k, src, p, mn: src == (3, 0) and p == (0, 0)
        and mn == frozenset({(-2, 0), (-1, 0)}))
    check(bridge_mv is not None,
          "a straight piece must be able to bridge an empty gap with its middle dot")
    s3 = g.apply_move(sbr, bridge_mv)
    stk3 = field_stacks(s3.pieces)
    check(height_at(stk3, (0, 0)) == 2, "bridge PÜNCT end rests on pillar1 (h=2)")
    check(height_at(stk3, (-2, 0)) == 2, "bridge far end rests on pillar2 (h=2)")
    check(height_at(stk3, (-1, 0)) == 1,
          "bridged MIDDLE minor hangs over the empty gap (only the bridge there)")

    # ------------------------------------------------- (4) connection WIN
    # A White chain across the q-axis (edge q=+8 to edge q=-8), built from two
    # straight segments; leave a one-piece gap, then COMPLETE it via apply_move.
    seg1 = [(8, -7), (7, -7), (6, -7), (5, -7), (4, -7),
            (3, -7), (2, -7), (1, -7), (0, -7)]               # dir (-1,0)
    seg2 = [(0, -7), (-1, -6), (-2, -5), (-3, -4), (-4, -3),
            (-5, -2), (-6, -1), (-7, 0), (-8, 1)]             # dir (-1,1)
    path = seg1 + seg2[1:]
    check(all(on_board(c) for c in path), "the test path must be on board")
    check(edge_of(path[0], 0, +1) and edge_of(path[-1], 0, -1),
          "the path must run edge-to-edge on the q-axis")

    def straight_piece(a, b, c):  # b is the middle (PÜNCT centred)
        return Piece(0, b, (a, c), 0)

    pieces = []
    for i in range(0, 9, 3):
        pieces.append(straight_piece(seg1[i], seg1[i + 1], seg1[i + 2]))
    s2f = seg2[1:]                       # 8 new fields after the shared (0,-7)
    for i in range(0, 6, 3):            # tile first 6; leave the last 2 as the gap
        pieces.append(straight_piece(s2f[i], s2f[i + 1], s2f[i + 2]))

    top_before = top_owner(pieces)
    check(connects(top_before, 0) is None,
          "the chain must NOT yet connect while the gap is open")
    missing = [f for f in path if f not in top_before]
    check(set(missing) == {(-7, 0), (-8, 1)},
          f"only the gap fields should be missing, got {missing}")

    sw = PunctState(pieces=list(pieces), reserve=(18, 18),
                    to_move=0, winner=None, ply=20)
    # final straight piece closes the gap: punct (-7,0), minors (-6,-1) & (-8,1)
    final = Piece(0, (-7, 0), ((-6, -1), (-8, 1)), 0)
    check(final.shape() == "straight", "final closing piece is straight")
    final_mv = add_move(final.punct, final.minors)
    s_win = g.apply_move(sw, final_mv)
    check(s_win.winner == 0, "completing the chain via apply_move must win for White")
    check(g.is_terminal(s_win), "the won state must be terminal")
    check(g.returns(s_win) == [1.0, -1.0], "returns must reward the winner")
    # and the connection is on the q-axis as intended
    check(connects(top_owner(s_win.pieces), 0) == 0,
          "the winning connection must be on the q-axis (axis 0)")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
