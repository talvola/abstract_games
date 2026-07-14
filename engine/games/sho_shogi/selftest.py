"""Sho Shogi correctness anchor (pure stdlib -- imports only agp + this game).

Anchors:
  * the 9x9 / 42-piece starting setup (21 each), verified against the Wikipedia
    setup diagram: back rank L N S G K G S N L, bishop/rook on the knights'
    files, and a Drunk Elephant on the king's file directly in front of it;
  * opening perft 26 / 676 at depths 1-2 (26 hand-derived piece-by-piece:
    9 pawns + 2 lances + 4 silver + 4 gold + 2 king + 2 elephant + 3 rook,
    knights/bishop blocked; 676 = 26x26 by the position's symmetry), no drops;
  * the Drunk Elephant's 7 targets from a central empty square and that it may
    NOT step straight backward; E promotes (optionally, in the far 3 ranks) to
    a Crown Prince that moves as a King and is a second ROYAL piece;
  * dual royalty: with a King AND a Crown Prince you are in check only when
    EVERY royal is attacked, so a royal may be legally left en prise and
    captured -- capturing one does NOT end the game; being mated with a sole
    royal DOES lose;
  * the bare-king win rule: baring the opponent (reducing them to only royal
    pieces) wins, but the bared player's immediately-following move may bare
    back for a DRAW (mutual bare);
  * NO drops: captures never bank to hand and no "@" drop move is ever
    generated; a random game terminates.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.sho_shogi.game import ShoShogi, ShoState, ELEPHANT      # noqa: E402
from agp.shogilike import BLACK, WHITE                             # noqa: E402

G = ShoShogi()


def st(board, to_move=BLACK, promoted=(), ply=0):
    s = ShoState(board=dict(board), promoted=frozenset(promoted),
                 hands={BLACK: {}, WHITE: {}}, to_move=to_move, ply=ply)
    s.reps = {G._poskey(s): 1}
    return s


def perft(state, d):
    if d == 0:
        return 1
    ms = G.legal_moves(state)
    if d == 1:
        return len(ms)
    return sum(perft(G.apply_move(state, m), d - 1) for m in ms)


def dests(state, frm):
    return sorted(m.split(">")[1].split("=")[0]
                  for m in G.legal_moves(state) if m.split(">")[0] == frm)


def main():
    s0 = G.initial_state()

    # ---- 1) setup ----------------------------------------------------------
    assert G.WIDTH == G.HEIGHT == 9 and G.ZONE == 3
    assert len(s0.board) == 42
    counts = {}
    for (pl, t) in s0.board.values():
        counts[(pl, t)] = counts.get((pl, t), 0) + 1
    per_type = {"K": 1, "E": 1, "R": 1, "B": 1, "G": 2, "S": 2, "N": 2,
                "L": 2, "P": 9}
    assert sum(per_type.values()) == 21
    for pl in (BLACK, WHITE):
        assert sum(1 for v in s0.board.values() if v[0] == pl) == 21
        for t, n in per_type.items():
            assert counts[(pl, t)] == n, (pl, t, counts.get((pl, t)))
    # back rank + the Drunk Elephant in front of the king
    assert [s0.board[(c, 0)][1] for c in range(9)] == \
        ["L", "N", "S", "G", "K", "G", "S", "N", "L"]
    assert s0.board[(4, 0)] == (BLACK, "K") and s0.board[(4, 1)] == (BLACK, "E")
    assert s0.board[(1, 1)] == (BLACK, "B") and s0.board[(7, 1)] == (BLACK, "R")
    assert s0.board[(4, 8)] == (WHITE, "K") and s0.board[(4, 7)] == (WHITE, "E")
    assert s0.board[(1, 7)] == (WHITE, "R") and s0.board[(7, 7)] == (WHITE, "B")

    # ---- 2) opening perft + no drops --------------------------------------
    ms0 = G.legal_moves(s0)
    assert len(ms0) == len(set(ms0)), "duplicate move strings"
    assert not any("@" in m for m in ms0), "drops must not exist in Sho Shogi"
    assert perft(s0, 1) == 26, perft(s0, 1)
    assert perft(s0, 2) == 676, perft(s0, 2)
    # the elephant's only opening moves are the two sideways steps
    assert dests(s0, "4,1") == ["3,1", "5,1"]

    # ---- 3) Drunk Elephant + Crown Prince ---------------------------------
    assert len(ELEPHANT) == 7 and (0, -1) not in ELEPHANT
    kk = {(0, 0): (BLACK, "K"), (8, 8): (WHITE, "K")}
    s = st({(4, 4): (BLACK, "E"), **kk})
    d = dests(s, "4,4")
    assert d == ["3,3", "3,4", "3,5", "4,5", "5,3", "5,4", "5,5"], d
    assert "4,3" not in d                       # cannot step straight backward
    # E promotes (optionally) in the far three ranks; +E moves as a King & royal
    s = st({(4, 6): (BLACK, "E"), **kk})
    em = [m for m in G.legal_moves(s) if m.startswith("4,6>")]
    assert "4,6>4,7" in em and "4,6>4,7=+" in em    # promotion is OPTIONAL
    n = G.apply_move(s, "4,6>4,7=+")
    assert (4, 7) in n.promoted
    cp = st({(4, 7): (BLACK, "E"), **kk}, promoted={(4, 7)})
    assert len(dests(cp, "4,7")) == 8               # Crown Prince = King's 8 steps
    assert (4, 7) in G._royals(n.board, n.promoted, BLACK)   # ...and it IS royal

    # ---- 4) dual royalty ---------------------------------------------------
    # White K(4,8) + Crown Prince(4,7); a Black rook on rank 8 attacks only the
    # King -> White is NOT in check (the Prince is safe) and the King is en prise.
    b = {(4, 8): (WHITE, "K"), (4, 7): (WHITE, "E"),
         (0, 0): (BLACK, "K"), (0, 8): (BLACK, "R")}
    assert not G.in_check(st(b, WHITE, {(4, 7)}).board, frozenset({(4, 7)}), WHITE)
    n = G.apply_move(st(b, BLACK, {(4, 7)}), "0,8>4,8")     # Black captures the King
    assert not G.is_terminal(n) and n.winner is None        # the Prince reigns on
    assert G._royals(n.board, n.promoted, WHITE) == [(4, 7)]
    # single-royal checkmate is a loss (White bare K(8,8), Gold guarded by a Lance)
    mate = st({(8, 8): (WHITE, "K"), (8, 7): (BLACK, "G"),
               (8, 0): (BLACK, "L"), (0, 0): (BLACK, "K")}, to_move=WHITE)
    assert G.in_check(mate.board, mate.promoted, WHITE)
    assert G.legal_moves(mate) == [] and G.is_terminal(mate)
    assert G.returns(mate) == [1.0, -1.0]                   # Black wins

    # ---- 5) bare-king rule -------------------------------------------------
    # (A) barer wins: Black bares White, White fails to bare back on its reply.
    b = {(1, 1): (WHITE, "K"), (1, 2): (WHITE, "P"),
         (8, 8): (BLACK, "K"), (1, 8): (BLACK, "R")}
    n = G.apply_move(st(b, BLACK), "1,8>1,2")               # rook captures the pawn
    assert n.winner is None and not G.is_terminal(n)        # deferred: White replies
    assert G._bare(n.board, n.promoted, WHITE)
    n2 = G.apply_move(n, "1,1>0,0")                         # King steps away; no bare-back
    assert n2.winner == BLACK and G.returns(n2) == [1.0, -1.0]
    # (B) mutual bare -> honest draw: White bares Black back on its reply.
    b = {(1, 1): (WHITE, "K"), (1, 2): (WHITE, "P"),
         (8, 8): (BLACK, "K"), (2, 2): (BLACK, "G")}
    n = G.apply_move(st(b, BLACK), "2,2>1,2")               # Gold captures pawn -> White bare
    assert n.winner is None and not G.is_terminal(n)
    n2 = G.apply_move(n, "1,1>1,2")                         # King captures the Gold -> Black bare
    assert n2.winner == "draw" and G.returns(n2) == [0.0, 0.0]

    # ---- 6) NO drops: captures never bank; zero-royal guard ---------------
    cap = G.apply_move(st({(0, 0): (BLACK, "K"), (8, 8): (WHITE, "K"),
                           (3, 0): (BLACK, "R"), (3, 5): (WHITE, "P")}, BLACK),
                       "3,0>3,5")
    assert cap.hands == {BLACK: {}, WHITE: {}}
    assert not any("@" in m for m in G.legal_moves(cap))
    z = st({(4, 4): (WHITE, "P"), (0, 0): (BLACK, "K")}, to_move=WHITE)
    assert not G._alive(z.board, z.promoted, WHITE)
    assert G.is_terminal(z) and G.returns(z) == [1.0, -1.0]

    # ---- 7) colour symmetry of move generation ----------------------------
    for pl in (BLACK, WHITE):
        rk = (4, 1) if pl == BLACK else (4, 7)
        s = st({(0, 0): (BLACK, "K"), (8, 8): (WHITE, "K"), rk: (pl, "R")}, pl)
        assert len(dests(s, f"{rk[0]},{rk[1]}")) == 19

    # ---- 8) serialize round-trips (board + promoted + winner) -------------
    mid = G.apply_move(G.apply_move(s0, "2,2>2,3"), "6,6>6,5")
    assert json.dumps(G.serialize(G.deserialize(G.serialize(mid))), sort_keys=True) \
        == json.dumps(G.serialize(mid), sort_keys=True)

    # ---- 9) a random game terminates --------------------------------------
    rng = random.Random(7)
    sx = G.initial_state()
    for _ in range(G.PLY_CAP + 1):
        if G.is_terminal(sx):
            break
        sx = G.apply_move(sx, rng.choice(G.legal_moves(sx)))
    assert G.is_terminal(sx)
    ret = G.returns(sx)
    assert len(ret) == 2 and all(isinstance(x, float) for x in ret)

    print("sho_shogi selftest: all checks passed")


if __name__ == "__main__":
    main()
