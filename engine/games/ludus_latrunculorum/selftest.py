"""Selftest for Ludus Latrunculorum (Locus Ludi / Schädler reconstruction).

Anchors (pure stdlib):
  a) the Locus Ludi leaflet's worked figures, transcribed and reached via
     apply_move: figure A (corner capture), figure B (two counters trapped in
     one move, removed one per turn), figure C (a leap whose landing traps a
     counter), the freeing figure (trapping a guard frees the victim);
  b) the Seneca trap -> forced-removal two-turn sequence (removal offered only
     and exactly at the start of the trapper's next turn);
  c) freeing probes: guard trapped -> victim freed instantly; guard departs ->
     victim freed;
  d) leap legality: own-colour counters only (enemy leap illegal), multi-leap
     chains with legal prefixes, a leap never captures by itself;
  e) the placement phase makes no captures/traps;
  f) a scored end with equal captures is an honest DRAW [0,0];
  g) Piso variant: immediate removal (corner + double capture), no leap moves,
     no suicide, reduced-to-one ends the game;
  h) termination: random playouts to terminal under both variants;
  i) frozen legal-move counts (opening placement = 64; a scripted full
     placement yields exactly 8 movement moves);
plus serialization round-trip, heuristic shape (list of 2), the no-shuttling
rule, and the pieces (16/20/24) option.

Figure coordinates: the leaflet's figures are strips of a wider board; they
are transcribed onto our 8x8 (cols/rows 0..7) preserving every adjacency, with
the figure-B right edge mapped to column 7.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))  # engine/ on the path

from agp.loader import load_from_dir  # noqa: E402

_, G = load_from_dir(HERE)

WHITE, BLACK = 0, 1


def cid(c, r):
    return f"{c},{r}"


def mk(board, variant="seneca", trapped=None, to_move=WHITE, stage="move",
       captures=(0, 0), last=(None, None), n_pieces=20):
    """Build a movement-phase state via the public deserialize API."""
    trapped = trapped or {}
    d = {
        "board": {cid(*c): o for c, o in board.items()},
        "trapped": {cid(*c): [cid(*g[0]), cid(*g[1])]
                    for c, g in trapped.items()},
        "variant": variant,
        "n_pieces": n_pieces,
        "phase": "move",
        "stage": stage,
        "to_move": to_move,
        "placed": [n_pieces, n_pieces],
        "captures": list(captures),
        "last": [None if m is None else [cid(*m[0]), cid(*m[1])] for m in last],
        "winner": None,
        "over": False,
        "no_progress": 0,
        "ply": 0,
    }
    return G.deserialize(d)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# ---------------------------------------------------------------- figure A
def test_figure_a_corner_trap_and_forced_removal():
    """Leaflet figure A: White moves 2,0>1,0; Black in the corner 0,0 is
    trapped by the two orthogonally adjacent counters; White must remove it at
    the start of his NEXT turn (anchor b)."""
    s = mk({(0, 0): BLACK, (2, 0): WHITE, (0, 1): WHITE,
            (5, 5): BLACK, (6, 5): BLACK, (6, 7): WHITE})
    check("2,0>1,0" in G.legal_moves(s), "A: trapping step missing")
    s = G.apply_move(s, "2,0>1,0")
    check(s.trapped.get((0, 0)) is not None, "A: corner counter not trapped")
    g = set(s.trapped[(0, 0)])
    check(g == {(1, 0), (0, 1)}, f"A: wrong corner guards {g}")
    check((0, 0) in s.board and s.captures == [0, 0],
          "A: trapped counter must stay on the board (not yet removed)")
    # Black to move: the incitus cannot move; no removal for Black
    check(G.current_player(s) == BLACK and s.stage == "move", "A: black stage")
    check(not any(m.startswith("0,0>") for m in G.legal_moves(s)),
          "A: a trapped counter must not move")
    s = G.apply_move(s, "5,5>5,6")
    # White's turn: removal is FORCED and is the whole legal-move set
    check(G.current_player(s) == WHITE and s.stage == "remove",
          "A: white must be in the removal stage")
    check(G.legal_moves(s) == ["0,0"], f"A: forced removal, got {G.legal_moves(s)}")
    s = G.apply_move(s, "0,0")
    check((0, 0) not in s.board and s.captures == [1, 0],
          "A: removal must capture the counter")
    check(G.current_player(s) == WHITE and s.stage == "move",
          "A: after removing, the same player moves")
    check(all(">" in m for m in G.legal_moves(s)),
          "A: no second removal in the same turn")


# ---------------------------------------------------------------- figure B
def test_figure_b_double_trap_one_removal_per_turn():
    """Leaflet figure B (right edge -> column 7): Black plays 7,0>7,1 and
    traps TWO white counters in one move; they are removed on Black's
    following turns, one per turn, Black choosing the order."""
    s = mk({(7, 0): BLACK, (5, 1): BLACK, (6, 1): WHITE,
            (7, 2): WHITE, (7, 3): BLACK,
            (0, 7): WHITE, (1, 7): WHITE}, to_move=BLACK)
    s = G.apply_move(s, "7,0>7,1")
    check(set(s.trapped) == {(6, 1), (7, 2)},
          f"B: expected two trapped whites, got {set(s.trapped)}")
    check(set(s.trapped[(6, 1)]) == {(7, 1), (5, 1)}, "B: guards of 6,1")
    check(set(s.trapped[(7, 2)]) == {(7, 1), (7, 3)}, "B: guards of 7,2")
    check(s.captures == [0, 0], "B: trapping is not yet capturing")
    # White has no removal (the trapped are white's own) and must move
    check(G.current_player(s) == WHITE and s.stage == "move", "B: white moves")
    check(not any(m.startswith("7,2>") for m in G.legal_moves(s)),
          "B: trapped white cannot move")
    s = G.apply_move(s, "0,7>0,6")
    # Black now chooses which trapped counter to remove
    check(s.stage == "remove" and sorted(G.legal_moves(s)) == ["6,1", "7,2"],
          f"B: removal choice, got {G.legal_moves(s)}")
    s = G.apply_move(s, "6,1")
    check(s.captures == [0, 1] and (7, 2) in s.trapped,
          "B: only ONE removal per turn")
    check(all(">" in m for m in G.legal_moves(s)), "B: must move after removing")
    s = G.apply_move(s, "5,1>5,0")
    s = G.apply_move(s, "1,7>2,7")            # White again
    check(s.stage == "remove" and G.legal_moves(s) == ["7,2"],
          "B: the second trapped counter is removed next turn")
    s = G.apply_move(s, "7,2")
    check(s.captures == [0, 2], "B: second removal")


# ---------------------------------------------------------------- figure C
def test_figure_c_leap_traps_on_landing():
    """Leaflet figure C: Black leaps 6,4 over his own 5,4 to 4,4; the landing
    encloses White 4,3 against Black 4,2. The jumped counter is untouched."""
    s = mk({(4, 2): BLACK, (4, 3): WHITE, (5, 3): WHITE,
            (5, 4): BLACK, (6, 4): BLACK,
            (0, 7): WHITE, (1, 6): WHITE}, to_move=BLACK)
    lm = G.legal_moves(s)
    check("6,4>4,4" in lm, "C: leap over own colour missing")
    check("5,4>5,2" not in lm, "C/d: a leap over an ENEMY counter is illegal")
    s = G.apply_move(s, "6,4>4,4")
    check(s.trapped.get((4, 3)) is not None, "C: leap landing must trap")
    check(set(s.trapped[(4, 3)]) == {(4, 4), (4, 2)}, "C: guards of 4,3")
    check(s.board.get((5, 4)) == BLACK, "C: a leap never captures the jumped counter")
    check((5, 3) not in s.trapped, "C: 5,3 is not enclosed")
    check(s.captures == [0, 0], "C: no immediate capture in Seneca")


# ------------------------------------------------------------- freeing (c)
def test_freeing_when_guard_is_trapped():
    """Leaflet freeing figure / Seneca Letters 117.30: White's trapped counter
    is set free the instant one of its two black guards is itself trapped."""
    s = mk({(3, 3): WHITE, (2, 3): BLACK, (4, 3): BLACK,
            (2, 2): WHITE, (2, 5): WHITE,
            (7, 7): BLACK, (6, 7): BLACK},
           trapped={(3, 3): ((2, 3), (4, 3))})
    check((3, 3) in s.trapped, "freeing: setup")
    s = G.apply_move(s, "2,5>2,4")   # traps guard 2,3 between 2,4 and 2,2
    check((2, 3) in s.trapped and set(s.trapped[(2, 3)]) == {(2, 4), (2, 2)},
          "freeing: the guard must be trapped")
    check((3, 3) not in s.trapped, "freeing: victim must be freed instantly")
    # the freed counter moves again on White's later turn
    s = G.apply_move(s, "7,7>7,6")
    check(s.stage == "remove" and G.legal_moves(s) == ["2,3"], "freeing: removal")
    s = G.apply_move(s, "2,3")
    check(any(m.startswith("3,3>") for m in G.legal_moves(s)),
          "freeing: freed counter must be mobile again")


def test_freeing_when_guard_departs():
    """A guard leaving its square also frees the victim (the removal proviso
    'provided his two surrounding stones themselves are still free')."""
    s = mk({(3, 3): WHITE, (2, 3): BLACK, (4, 3): BLACK,
            (0, 0): WHITE, (0, 2): WHITE},
           trapped={(3, 3): ((2, 3), (4, 3))}, to_move=BLACK)
    s = G.apply_move(s, "2,3>2,2")
    check(s.trapped == {}, "departure: victim must be freed when a guard leaves")


# ------------------------------------------------------------- no suicide
def test_no_suicide():
    s = mk({(2, 2): BLACK, (4, 2): BLACK, (3, 1): WHITE,
            (0, 7): WHITE, (7, 7): BLACK, (7, 6): BLACK})
    s = G.apply_move(s, "3,1>3,2")   # steps between two black counters
    check((3, 2) not in s.trapped and s.board.get((3, 2)) == WHITE,
          "no-suicide: mover must not be trapped by its own move")
    # and it is still free after Black replies
    s = G.apply_move(s, "7,7>6,7")
    check((3, 2) not in s.trapped, "no-suicide: still free next turn")


# ------------------------------------------------------------ multi-leap (d)
def test_multi_leap_chain_and_prefix():
    s = mk({(0, 0): WHITE, (1, 0): WHITE, (3, 0): WHITE,
            (7, 7): BLACK, (7, 6): BLACK})
    lm = G.legal_moves(s)
    check("0,0>2,0" in lm, "leap: single hop missing")
    check("0,0>2,0>4,0" in lm, "leap: chained double hop missing")
    s2 = G.apply_move(s, "0,0>2,0>4,0")
    check(s2.board.get((4, 0)) == WHITE and (0, 0) not in s2.board
          and s2.board.get((1, 0)) == WHITE and s2.board.get((3, 0)) == WHITE,
          "leap: chain endpoint wrong or a jumped counter vanished")


# ------------------------------------------------------------ shuttling
def test_no_shuttling():
    s = mk({(4, 4): WHITE, (0, 0): WHITE,
            (7, 7): BLACK, (7, 6): BLACK, (0, 7): BLACK})
    s = G.apply_move(s, "4,4>4,5")
    s = G.apply_move(s, "7,7>6,7")
    lm = G.legal_moves(s)
    check("4,5>4,4" not in lm, "shuttle: immediate undo must be illegal")
    check("4,5>3,5" in lm, "shuttle: other moves of the same counter stay legal")


# ------------------------------------------------------------ placement (e, i)
def test_placement_no_captures_and_frozen_counts():
    s = G.initial_state()
    check(G.current_player(s) == WHITE and s.phase == "place", "place: opening")
    check(len(G.legal_moves(s)) == 64, "i: opening placement count must be 64")
    s = G.apply_move(s, "1,0")            # White
    check(len(G.legal_moves(s)) == 63, "i: 63 after one placement")
    s = G.apply_move(s, "0,0")            # Black places INTO the corner...
    s = G.apply_move(s, "0,1")            # ...White completes the corner sandwich
    check(s.trapped == {} and (0, 0) in s.board and s.captures == [0, 0],
          "e: no trapping/capturing during placement")
    # scripted full placement: rows 0-4 row-major => even columns White
    s = G.initial_state()
    for k in range(40):
        s = G.apply_move(s, cid(k % 8, k // 8))
    check(s.phase == "move" and G.current_player(s) == WHITE,
          "e: White opens the movement phase")
    check(s.placed == [20, 20] and s.trapped == {}, "e: placement bookkeeping")
    lm = G.legal_moves(s)
    check(len(lm) == 8, f"i: frozen movement count 8, got {len(lm)}")
    check("0,4>0,5" in lm and "0,3>0,5" in lm,
          "i: expected the row-4 steps and the row-3 vertical leaps")


def test_pieces_option():
    s = G.initial_state({"pieces": 16})
    check(s.n_pieces == 16, "pieces option ignored")
    for k in range(32):
        s = G.apply_move(s, cid(k % 8, k // 8))
    check(s.phase == "move", "pieces=16: phase must flip after 32 placements")
    check(G.initial_state({"pieces": 24}).n_pieces == 24, "pieces=24")
    check(G.initial_state().n_pieces == 20, "default 20 counters (leaflet)")


# ------------------------------------------------------------ draw (f)
def test_blockade_with_equal_captures_is_draw():
    s = mk({(0, 0): BLACK, (1, 0): BLACK,
            (0, 1): WHITE, (1, 1): WHITE, (2, 0): WHITE, (5, 5): WHITE})
    s = G.apply_move(s, "5,5>5,4")   # harmless; Black is now blockaded
    check(G.is_terminal(s), "f: blockade must end the game")
    check(s.winner is None and G.returns(s) == [0.0, 0.0],
          "f: equal captures must be an honest draw")


def test_blockade_scores_by_captures():
    s = mk({(0, 0): BLACK, (1, 0): BLACK,
            (0, 1): WHITE, (1, 1): WHITE, (2, 0): WHITE, (5, 5): WHITE},
           captures=(3, 1))
    s = G.apply_move(s, "5,5>5,4")
    check(G.is_terminal(s) and s.winner == WHITE and G.returns(s) == [1.0, -1.0],
          "blockade: most captures must win")


# ------------------------------------------------------------ Piso (g)
def test_piso_immediate_corner_capture():
    s = mk({(0, 0): BLACK, (2, 0): WHITE, (0, 1): WHITE,
            (5, 5): BLACK, (6, 5): BLACK, (6, 7): WHITE}, variant="piso")
    s = G.apply_move(s, "2,0>1,0")
    check((0, 0) not in s.board and s.captures == [1, 0],
          "piso: corner capture must be immediate")
    check(s.trapped == {}, "piso: no incitus state")
    check(G.current_player(s) == BLACK and s.stage == "move",
          "piso: no removal stage")


def test_piso_double_capture_together():
    s = mk({(7, 0): BLACK, (5, 1): BLACK, (6, 1): WHITE,
            (7, 2): WHITE, (7, 3): BLACK,
            (0, 7): WHITE, (1, 7): WHITE, (2, 7): WHITE}, variant="piso",
           to_move=BLACK)
    s = G.apply_move(s, "7,0>7,1")
    check((6, 1) not in s.board and (7, 2) not in s.board
          and s.captures == [0, 2],
          "piso: both trapped counters must be removed together")


def test_piso_has_no_leaps_and_no_suicide():
    s = mk({(4, 2): BLACK, (4, 3): WHITE, (5, 3): WHITE,
            (5, 4): BLACK, (6, 4): BLACK,
            (0, 7): WHITE, (1, 6): WHITE}, variant="piso", to_move=BLACK)
    lm = G.legal_moves(s)
    check("6,4>4,4" not in lm, "piso: leaps must not exist")
    check(all(len(m.split(">")) == 2 for m in lm), "piso: steps only")
    # no suicide
    s2 = mk({(2, 2): BLACK, (4, 2): BLACK, (3, 1): WHITE,
             (0, 7): WHITE, (7, 7): BLACK, (7, 6): BLACK}, variant="piso")
    s2 = G.apply_move(s2, "3,1>3,2")
    check(s2.board.get((3, 2)) == WHITE and s2.captures == [0, 0],
          "piso: no suicide")


def test_piso_reduced_to_one_ends():
    s = mk({(0, 0): BLACK, (4, 4): BLACK,
            (0, 1): WHITE, (2, 0): WHITE, (6, 6): WHITE}, variant="piso")
    s = G.apply_move(s, "2,0>1,0")
    check(G.is_terminal(s) and s.winner == WHITE and G.returns(s) == [1.0, -1.0],
          "piso: reduced to one counter must end with most-captures winner")


def test_seneca_removal_to_one_ends():
    s = mk({(0, 0): BLACK, (4, 4): BLACK,
            (0, 1): WHITE, (1, 0): WHITE, (6, 6): WHITE},
           trapped={(0, 0): ((1, 0), (0, 1))}, stage="remove")
    s = G.apply_move(s, "0,0")
    check(G.is_terminal(s) and s.winner == WHITE,
          "seneca: removal reducing the enemy to one counter ends the game")


# ------------------------------------------------------------ misc plumbing
def test_serialize_roundtrip_and_heuristic():
    s = mk({(3, 3): WHITE, (2, 3): BLACK, (4, 3): BLACK, (0, 0): WHITE,
            (7, 7): BLACK},
           trapped={(3, 3): ((2, 3), (4, 3))}, last=(((0, 1), (0, 0)), None),
           captures=(2, 1))
    d1 = G.serialize(s)
    d2 = G.serialize(G.deserialize(d1))
    check(d1 == d2, "serialize must round-trip identically")
    h = G.heuristic(s)
    check(isinstance(h, list) and len(h) == 2, "heuristic must be a 2-list")
    check(abs(h[0] + h[1]) < 1e-9, "heuristic must be zero-sum")
    # trapped White counter counts almost nothing: Black should be ahead
    check(h[1] > 0, "heuristic: trapped material must be discounted")
    h0 = G.heuristic(G.initial_state())
    check(h0 == [0.0, 0.0], "heuristic: empty board is balanced")


def test_render_shape():
    spec = G.render(G.initial_state())
    check(spec["board"] == {"type": "square", "width": 8, "height": 8},
          "render: board shape")
    check(spec["pieces"] == [] and "caption" in spec, "render: initial spec")
    s = mk({(3, 3): WHITE, (2, 3): BLACK, (4, 3): BLACK, (7, 7): BLACK},
           trapped={(3, 3): ((2, 3), (4, 3))})
    ps = {p["cell"]: p for p in G.render(s)["pieces"]}
    check("fill" in ps["3,3"] and "stroke" in ps["3,3"],
          "render: trapped counter must carry a fill/stroke override")
    check("fill" not in ps["2,3"], "render: free counters use seat colours")


# ------------------------------------------------------------ termination (h)
def test_random_playouts_terminate():
    for variant in ("seneca", "piso"):
        for seed in range(12):
            rng = random.Random(1000 * seed + (7 if variant == "piso" else 0))
            s = G.initial_state({"variant": variant,
                                 "pieces": rng.choice([16, 20, 24])})
            plies = 0
            while not G.is_terminal(s):
                lm = G.legal_moves(s)
                check(lm, f"h/{variant}: empty legal_moves on non-terminal")
                s = G.apply_move(s, rng.choice(lm))
                plies += 1
                check(plies < 3000, f"h/{variant}: game did not terminate")
            r = G.returns(s)
            check(len(r) == 2 and r in ([0.0, 0.0], [1.0, -1.0], [-1.0, 1.0]),
                  f"h/{variant}: malformed returns {r}")
            check(G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s),
                  f"h/{variant}: terminal state must round-trip")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"ludus_latrunculorum selftest: {len(tests)} tests passed")


if __name__ == "__main__":
    main()
