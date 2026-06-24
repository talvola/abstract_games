"""Gess correctness anchor — pure stdlib, fast.

No published perft for Gess, so the anchor is a set of baked rule assertions:
board/border geometry, the 43+43 symmetric opening with one ring each, the
footprint -> direction mapping (corner=diagonal, edge=orthogonal), center-stone
range (occupied=unlimited, empty=max-3), slide-stop-at-first-collision
(including the "masking" case where a leading carried stone bumps a blocker that
sits where it would land -- a regression guard for a real slide-through bug),
the authoritative-opening chess-piece move-sets, multi-cell capture,
self-capture, border-kill removal, ring detection, the multi-ring win/loss
rules, and a serialize round-trip.

Run with:  PYTHONPATH=. python3 games/gess/selftest.py
Prints "SELFTEST OK" and exits 0 on success; raises on failure.
"""

from __future__ import annotations

import json

from games.gess.game import (
    Gess, CState, BLACK, WHITE, N,
    _is_inner, _is_border, _count_rings, _start_board, _alg,
)


def ring_at(player, cx, cy):
    """Return a board dict with a single ring of `player` centered at (cx,cy)."""
    b = {}
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            b[(cx + dc, cy + dr)] = player
    return b


def main() -> None:
    g = Gess()

    # ---- (1) board & border geometry --------------------------------------
    assert N == 20
    assert _is_inner(1, 1) and _is_inner(18, 18)
    assert not _is_inner(0, 5) and not _is_inner(19, 5) and not _is_inner(5, 0)
    assert _is_border(0, 5) and _is_border(19, 5) and _is_border(5, 0) and _is_border(5, 19)
    assert not _is_border(1, 1) and not _is_border(18, 18)

    # ---- (2) opening: 43+43, vertical symmetry, exactly one ring each ------
    st = g.initial_state()
    nb = sum(1 for v in st.board.values() if v == BLACK)
    nw = sum(1 for v in st.board.values() if v == WHITE)
    assert nb == 43 and nw == 43, f"expected 43+43, got {nb}+{nw}"
    # vertical mirror symmetry r -> 19-r between the two colours
    for (c, r), owner in st.board.items():
        mirror = st.board.get((c, N - 1 - r))
        assert mirror is not None and mirror != owner, \
            f"opening not symmetric at {(c, r)}"
    # exactly one ring per side, at l3=(11,2) and l18=(11,17)
    assert _count_rings(st.board, BLACK) == 1, "Black should start with one ring"
    assert _count_rings(st.board, WHITE) == 1, "White should start with one ring"
    # the black ring is centered at (11,2) with empty center & 8 black neighbours
    assert (11, 2) not in st.board, "Black ring center l3 must be empty"
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == 0 and dr == 0:
                continue
            assert st.board.get((11 + dc, 2 + dr)) == BLACK, "Black ring outer missing"
    # render emits a 20x20 square board with border tints + owner discs (no label)
    rs = g.render(st)
    assert rs["board"]["type"] == "square"
    assert rs["board"]["width"] == 20 and rs["board"]["height"] == 20
    assert "0,5" in rs["board"]["tints"], "border kill-zone must be tinted"
    assert "5,5" not in rs["board"]["tints"], "inner cells must not be tinted"
    assert all("label" not in p for p in rs["pieces"]), "stones are owner discs, no label"
    assert len(rs["pieces"]) == 86

    # ---- (3) footprint -> direction mapping (corner=diagonal, edge=orthog) -
    # A footprint with ONLY a top-mid (N) edge stone (and empty center) enables
    # ONLY the N direction. Center (5,5); the only outer stone at (5,4) = N edge.
    st = CState(board={(5, 4): BLACK}, to_move=BLACK)
    dsts = set(g._gen_from_center(st, 5, 5))
    # N direction = (0,-1); with empty center, range up to 3, nothing to collide
    assert (5, 4) in dsts and (5, 3) in dsts and (5, 2) in dsts, "N moves missing"
    assert (5, 1) not in dsts, "empty-center range must cap at 3"
    assert (6, 5) not in dsts and (5, 6) not in dsts, "non-N directions must be absent"
    # A corner stone at (4,4) = NW corner -> enables ONLY the NW diagonal
    st = CState(board={(4, 4): BLACK}, to_move=BLACK)
    dsts = set(g._gen_from_center(st, 5, 5))
    assert (4, 4) in dsts and (3, 3) in dsts and (2, 2) in dsts, "NW diagonal missing"
    assert (5, 4) not in dsts and (4, 5) not in dsts, "orthogonals must be absent for a corner"

    # ---- (4) center occupied -> unlimited range ---------------------------
    # Center occupied + an N edge stone -> N range is unlimited (to inner edge).
    st = CState(board={(5, 5): BLACK, (5, 4): BLACK}, to_move=BLACK)
    dsts = set(g._gen_from_center(st, 5, 5))
    assert (5, 1) in dsts, "occupied-center range must be unlimited (reach inner edge)"
    # center must stay inner -> cannot push center to a border row 0
    assert (5, 0) not in dsts, "center must remain on the inner board"

    # ---- (5) slide stops at first collision -------------------------------
    # N-moving footprint (empty center, edge stone at (5,4)); an enemy stone sits
    # at (5,1). Footprint centered at (5,2) covers (5,1) -> must stop at (5,2);
    # cannot reach (5,1) center (its footprint would still cover the blocker, but
    # also that's the collision stop).  It may stop earlier at (5,3) or (5,4).
    st = CState(board={(5, 4): BLACK, (5, 1): WHITE}, to_move=BLACK)
    dsts = set(g._gen_from_center(st, 5, 5))
    assert (5, 4) in dsts and (5, 3) in dsts, "early clear stops missing"
    assert (5, 2) in dsts, "collision-stop step must be a legal destination"
    assert (5, 1) not in dsts, "cannot advance past the first collision"

    # ---- (5b) REGRESSION: a leading carried stone bumping into a blocker must
    # STOP, even when the blocker sits exactly where the carried stone would land
    # (the "masking" case). This needs an OCCUPIED-center (unlimited-range) piece
    # so the empty-center range cap can't hide a slide-through. Center (10,10)
    # occupied + SW corner (9,9) enables SW (unlimited); enemy blocker at (7,7).
    # Sliding SW: at center (8,8) the footprint (7,7..9,9) covers the enemy -> it
    # must stop at (8,8); it must NOT slide on to (7,7) or (6,6).
    st = CState(board={(10, 10): BLACK, (9, 9): BLACK, (7, 7): WHITE}, to_move=BLACK)
    dsts = set(g._gen_from_center(st, 10, 10))
    assert (9, 9) in dsts and (8, 8) in dsts, "early/collision SW stops missing"
    assert (7, 7) not in dsts and (6, 6) not in dsts, \
        "must NOT slide THROUGH a blocker that a carried stone would land on"
    ns = g.apply_move(st, "10,10>8,8")
    assert ns.board.get((7, 7)) == BLACK, \
        "enemy captured, then the carried SW stone lands on (7,7) -> owned by mover"
    assert ns.board.get((8, 8)) == BLACK, "carried center lands at the destination"
    # The mover's OWN non-carried stone masks-and-blocks identically.
    st = CState(board={(10, 10): BLACK, (9, 9): BLACK, (7, 7): BLACK}, to_move=BLACK)
    dsts = set(g._gen_from_center(st, 10, 10))
    assert (8, 8) in dsts and (7, 7) not in dsts, \
        "own non-carried stone must block (and self-capture), not be slid through"

    # ---- (5c) AUTHORITATIVE OPENING: the chess-piece footprints move as the
    # Archimedeans designed (direction-enablement on REAL game pieces, not just
    # synthetic ones). The start position is the canonical source of truth; these
    # direction sets are rule-derived (counts are engine-derived regression locks).
    st0 = g.initial_state()
    open_moves = g.legal_moves(st0)
    assert len(open_moves) == 416, \
        f"opening legal-move count regressed (expected 416, got {len(open_moves)})"

    def dirset(state, cx, cy):
        names = {(0, 1): "N", (0, -1): "S", (1, 0): "E", (-1, 0): "W",
                 (1, 1): "NE", (-1, 1): "NW", (1, -1): "SE", (-1, -1): "SW"}
        out = {}
        for (dx, dy) in g._gen_from_center(state, cx, cy):
            sx = (dx > cx) - (dx < cx); sy = (dy > cy) - (dy < cy)
            out.setdefault(names[(sx, sy)], 0)
            out[names[(sx, sy)]] += 1
        return out

    ortho = {"N", "S", "E", "W"}
    diag = {"NE", "NW", "SE", "SW"}
    alleight = ortho | diag
    # "Rooks" c3=(2,2)/r3=(17,2): orthogonal only (edge stones, occupied center)
    for c in (2, 17):
        d = dirset(st0, c, 2)
        assert set(d) == ortho, f"rook at ({c},2) should be orthogonal-only, got {set(d)}"
    # "Bishops" f3=(5,2)/o3=(14,2): diagonal only (corner stones)
    for c in (5, 14):
        d = dirset(st0, c, 2)
        assert set(d) == diag, f"bishop at ({c},2) should be diagonal-only, got {set(d)}"
    # "Queens" i3=(8,2)/j3=(9,2): all 8 directions (occupied center, full surround)
    for c in (8, 9):
        d = dirset(st0, c, 2)
        assert set(d) == alleight, f"queen at ({c},2) should be all-8, got {set(d)}"
    # "King"/ring l3=(11,2): all 8 directions, EMPTY center => max distance 3
    dk = dirset(st0, 11, 2)
    assert set(dk) == alleight, f"ring/king l3 should be all-8, got {set(dk)}"
    kmax = max(max(abs(dx - 11), abs(dy - 2))
               for (dx, dy) in g._gen_from_center(st0, 11, 2))
    assert kmax == 3, f"empty-center ring must cap at distance 3, got {kmax}"
    # "Pawn": the lone front stone c7=(2,6) cannot be a center (no neighbour in its
    # 3x3); it is pushed forward by the empty-center footprint behind it at (2,5),
    # which enables ONLY N (toward the enemy) and advances 1..3.
    assert g._footprint_owner(st0.board, 2, 6, BLACK) is None, \
        "a lone front stone cannot be a legal footprint center"
    dp = dirset(st0, 2, 5)
    assert set(dp) == {"N"} and dp["N"] == 3, \
        f"pawn-pusher (2,5) should be N-only, 3 moves, got {dp}"

    # ---- (5d) occupied-center diagonal slides UNLIMITED on an open board ------
    # (the packed opening blocks bishops early; prove the range rule directly.)
    st = CState(board={(5, 5): BLACK, (6, 6): BLACK}, to_move=BLACK)  # center + NE
    dsts = set(g._gen_from_center(st, 5, 5))
    assert (18, 18) in dsts, "occupied-center diagonal must slide unobstructed to the edge"

    # ---- (6) multi-cell capture: all non-carried stones in dest 3x3 removed
    # Footprint center (5,5), single carried edge stone at (5,4) (offset N).
    # The footprint must be clean (no enemy in its source 3x3 rows 4..6 cols 4..6).
    # Move N by 1 -> center (5,4), dest 3x3 = rows 3..5 cols 4..6. Enemies in the
    # NEW row 3 (not in the source) at (4,3) and (6,3) are inside dest -> both
    # captured. The carried stone (5,4)->(5,3).
    st = CState(board={(5, 4): BLACK,
                       (4, 3): WHITE, (6, 3): WHITE}, to_move=BLACK)
    ns = g.apply_move(st, "5,5>5,4")
    for e in [(4, 3), (6, 3)]:
        assert e not in ns.board, f"capture must remove enemy at {e}"
    assert ns.board.get((5, 3)) == BLACK, "carried stone lands at its offset"

    # ---- (7) self-capture: own non-carried stones in dest are removed too --
    # Footprint center (5,5), carried = single edge stone (5,4). A FRIENDLY,
    # NON-CARRIED stone (outside the source 3x3) sits in the new row 3 of the
    # destination at (4,3). Move N by 1 -> center (5,4), dest rows 3..5 cols 4..6
    # covers (4,3) -> the own stone is self-captured (removed).
    st = CState(board={(5, 4): BLACK, (4, 3): BLACK}, to_move=BLACK)
    ns = g.apply_move(st, "5,5>5,4")
    assert (4, 3) not in ns.board, "self-capture: own non-carried stone in dest removed"
    assert ns.board.get((5, 3)) == BLACK, "carried stone still placed"

    # ---- (8) border kill: carried stone landing on border vanishes --------
    # Footprint near the top inner edge. Center at (5,18) with an edge stone at
    # (5,17) (S of center... we want to push a carried stone over the top border).
    # Put carried outer stone at (5,19)? that's border, can't. Instead: center
    # (5,17), carried stone at (5,16) and (5,18); move N by 1 -> center (5,18)
    # (inner), carried (5,18)->(5,19) BORDER vanishes, (5,16)->(5,17) stays.
    st = CState(board={(5, 16): BLACK, (5, 18): BLACK}, to_move=BLACK)
    # footprint center (5,17) empty; outer stones (5,16),(5,18) enable N & S.
    assert "5,17>5,18" in g.legal_moves(st), "the border-kill move must be legal"
    ns = g.apply_move(st, "5,17>5,18")   # slide S by 1 -> center (5,18)
    assert (5, 19) not in ns.board, "carried stone pushed onto border must vanish"
    assert ns.board.get((5, 17)) == BLACK, "the other carried stone survives"
    assert (5, 18) not in ns.board, "the (empty) center cell stays empty after the slide"

    # ---- (9) ring detection -----------------------------------------------
    b = ring_at(BLACK, 10, 10)
    assert _count_rings(b, BLACK) == 1 and _count_rings(b, WHITE) == 0
    # filling the center destroys the ring
    b2 = dict(b); b2[(10, 10)] = BLACK
    assert _count_rings(b2, BLACK) == 0, "an occupied center is NOT a ring"
    # a mixed-colour surround is not a ring
    b3 = ring_at(BLACK, 10, 10); b3[(9, 9)] = WHITE
    assert _count_rings(b3, BLACK) == 0

    # ---- (10) win/loss: opponent ringless -> mover wins -------------------
    # Black has a ring at (5,5); White is ringless (a lone stone far away). Black
    # makes a quiet move with a SEPARATE 2-stone gadget so its ring survives.
    bd = ring_at(BLACK, 5, 5)
    bd[(15, 15)] = WHITE          # a lone white stone, not a ring
    bd[(10, 10)] = BLACK          # mover gadget center
    bd[(10, 9)] = BLACK           # outer N stone -> enables the N direction
    st = CState(board=dict(bd), to_move=BLACK)
    assert "10,10>10,9" in g.legal_moves(st), "the quiet gadget move must be legal"
    ns = g.apply_move(st, "10,10>10,9")    # slide N by 1, captures nothing
    assert _count_rings(ns.board, BLACK) >= 1, "Black ring must survive the move"
    assert _count_rings(ns.board, WHITE) == 0
    assert ns.winner == BLACK, "opponent ringless at end of turn -> mover wins"
    assert g.is_terminal(ns) and g.returns(ns) == [1.0, -1.0]

    # ---- (11) mover strands itself ringless -> MOVER loses ----------------
    # Black's ONLY ring is at (5,8). A Black mover above it (center (5,11), outer
    # N stone (5,10)) slides N and crashes into the ring's top row, SELF-capturing
    # those ring stones -> Black ends ringless and so the MOVER loses.
    bd = ring_at(BLACK, 5, 8)
    bd[(5, 10)] = BLACK            # outer N stone of the mover gadget
    st = CState(board=dict(bd), to_move=BLACK)
    assert "5,11>5,10" in g.legal_moves(st), "strand-self move must be legal"
    ns = g.apply_move(st, "5,11>5,10")
    assert _count_rings(ns.board, BLACK) == 0, "Black must have destroyed its last ring"
    assert ns.winner == WHITE, "mover ringless at end of turn -> mover loses"
    assert g.returns(ns) == [-1.0, 1.0]

    # ---- (12) mutual-ringless -> MOVER loses ------------------------------
    # Black ring at (5,8) and White ring at (5,5). A single Black footprint that
    # stops centered at (5,6) covers rows 5..7: White ring outer rows 4..6 (its
    # top) AND Black ring outer rows 7..9 (its bottom) -> BOTH rings break at once.
    # Approach from the side along row 6 so nothing is hit before column 5:
    # mover center (9,6), outer W stone (8,6), empty center (range 3) -> the slide
    # W stops at (7,6), whose 3x3 (cols 6..8 rows 5..7) reaches the ring stones.
    board = {}
    board.update(ring_at(BLACK, 5, 8))
    board.update(ring_at(WHITE, 5, 5))
    board[(8, 6)] = BLACK
    st = CState(board=dict(board), to_move=BLACK)
    assert _count_rings(st.board, BLACK) == 1 and _count_rings(st.board, WHITE) == 1
    assert "9,6>7,6" in g.legal_moves(st), "the mutual-break move must be legal"
    ns = g.apply_move(st, "9,6>7,6")
    assert _count_rings(ns.board, BLACK) == 0 and _count_rings(ns.board, WHITE) == 0, \
        "the move must break BOTH rings simultaneously"
    assert ns.winner == WHITE, \
        "mutual-ringless at end of turn -> the MOVER loses (opponent wins)"
    assert g.returns(ns) == [-1.0, 1.0]

    # ---- (13) move encoding & legality round-trip -------------------------
    st = g.initial_state()
    moves = g.legal_moves(st)
    assert moves, "opening must have legal moves"
    for m in moves[:50]:
        assert ">" in m, "move string is src>dst"
        ns = g.apply_move(st, m)           # must not raise
        assert ns.to_move == WHITE
    # describe_move produces algebraic notation
    desc = g.describe_move(st, moves[0])
    assert "-" in desc or "x" in desc

    # ---- (14) serialize round-trips, JSON-able ----------------------------
    d = g.serialize(g.initial_state())
    assert g.serialize(g.deserialize(d)) == d
    assert json.loads(json.dumps(d)) == d

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
