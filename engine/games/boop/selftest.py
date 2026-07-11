"""Standalone correctness anchor for boop. (pure stdlib + agp + this game).

Run: PYTHONPATH=. python3 games/boop/selftest.py   -> prints SELFTEST OK, exit 0.

Anchors (vs the official Smirk & Dagger rulebook + Dized FAQ):
  * boop physics: all 8 directions, blocking by the piece behind, no chain
    reactions, edge boop-offs returning to the owner's pool, Kittens unable
    to boop Cats (Cats booping both);
  * graduation: auto single all-Kitten row, mixed Cat+Kitten row, the
    multiple-rows choice (resolve sub-move), the all-8-on-the-bed pick-up;
  * wins via apply_move: three Cats in a row, all 8 Cats on the bed, and
    mover-only scoring (a row booped together for the OPPONENT waits for
    their own turn);
  * draw backstops (threefold repetition + ply cap), serialize round-trip,
    and 300 seeded random playouts (termination + result mix + backstop rates).
"""

from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from games.boop.game import Boop, BoopState, MAX_PLIES  # noqa: E402

G = Boop()


def check(cond, msg):
    if not cond:
        print(f"SELFTEST FAIL: {msg}")
        sys.exit(1)


def mk(board=None, pools=None, to_move=0):
    """Hand-built mid-game state (phase 'place'). board: {(c,r): (owner,kind)}."""
    s = G.initial_state()
    if board:
        s.board = dict(board)
    if pools:
        s.pools = {p: dict(h) for p, h in pools.items()}
    else:
        # keep the active-8 invariant: pool = 8 - on-board pieces
        for p in (0, 1):
            n = sum(1 for (o, _k) in s.board.values() if o == p)
            s.pools[p] = {"K": 8 - n, "C": 0}
    s.to_move = to_move
    s.reps = {G._poskey(s): 1}
    return s


def test_opening():
    s = G.initial_state()
    ms = G.legal_moves(s)
    check(len(ms) == 36, f"opening moves {len(ms)} != 36")
    check(all(m.endswith("=K") for m in ms), "opening: only Kittens placeable")
    check(G.current_player(s) == 0, "P0 starts")


def test_boop_all_8_directions():
    # 8 opponent kittens ring the empty centre; placing there pushes all 8.
    ring = [(1, 1), (2, 1), (3, 1), (1, 2), (3, 2), (1, 3), (2, 3), (3, 3)]
    s = mk(board={c: (1, "K") for c in ring}, to_move=0)
    ns = G.apply_move(s, "2,2=K")
    dests = {(0, 0), (2, 0), (4, 0), (0, 2), (4, 2), (0, 4), (2, 4), (4, 4)}
    got = {c for c, (o, _k) in ns.board.items() if o == 1}
    check(got == dests, f"8-direction boop: {sorted(got)}")
    check(ns.board[(2, 2)] == (0, "K"), "placed piece stays put")
    check(ns.to_move == 1, "turn passes (no line for the mover)")


def test_blocking_and_no_chain():
    # Kitten at (2,3) has a piece directly behind at (2,4): it must not move,
    # and (2,4) must not move either (no chain reactions).
    s = mk(board={(2, 3): (1, "K"), (2, 4): (1, "K")}, to_move=0)
    ns = G.apply_move(s, "2,2=K")
    check(ns.board[(2, 3)] == (1, "K"), "blocked piece moved")
    check(ns.board[(2, 4)] == (1, "K"), "chain reaction happened")


def test_edge_boop_off_returns_to_pool():
    s = mk(board={(0, 0): (1, "K")}, to_move=0)
    check(s.pools[1] == {"K": 7, "C": 0}, "setup pool")
    ns = G.apply_move(s, "1,1=K")
    check((0, 0) not in ns.board, "corner kitten should be booped off")
    check(ns.pools[1] == {"K": 8, "C": 0}, "booped-off kitten returns to pool")


def test_kitten_cannot_boop_cat():
    s = mk(board={(2, 3): (1, "C")},
           pools={0: {"K": 8, "C": 0}, 1: {"K": 7, "C": 0}}, to_move=0)
    ns = G.apply_move(s, "2,2=K")
    check(ns.board[(2, 3)] == (1, "C"), "Kitten booped a Cat")
    # ...but a Cat boops both Cats and Kittens.
    s2 = mk(board={(2, 3): (1, "C"), (3, 2): (1, "K")},
            pools={0: {"K": 7, "C": 1}, 1: {"K": 6, "C": 0}}, to_move=0)
    ns2 = G.apply_move(s2, "2,2=C")
    check(ns2.board.get((2, 4)) == (1, "C"), "Cat failed to boop a Cat")
    check(ns2.board.get((4, 2)) == (1, "K"), "Cat failed to boop a Kitten")


def test_auto_graduation_single_row():
    # (0,0),(1,1) mine; placing (2,2) completes the diagonal. (1,1) is boop-
    # blocked by (0,0) -- the rulebook's "played into that line" case.
    s = mk(board={(0, 0): (0, "K"), (1, 1): (0, "K")}, to_move=0)
    ns = G.apply_move(s, "2,2=K")
    check(all((c, c) not in ns.board for c in range(3)), "row not removed")
    check(ns.pools[0] == {"K": 5, "C": 3}, f"3 Cats to pool: {ns.pools[0]}")
    check(ns.to_move == 1 and ns.phase == "place", "turn passes after auto-grad")


def test_mixed_row_graduates():
    s = mk(board={(0, 0): (0, "K"), (1, 1): (0, "C")},
           pools={0: {"K": 6, "C": 0}, 1: {"K": 8, "C": 0}}, to_move=0)
    ns = G.apply_move(s, "2,2=K")
    check(len([1 for (o, _k) in ns.board.values() if o == 0]) == 0,
          "mixed row: all three removed")
    check(ns.pools[0] == {"K": 5, "C": 3},
          f"mixed row -> 3 Cats to pool: {ns.pools[0]}")


def test_multiple_rows_choice():
    # Placing at (2,2) completes BOTH diagonals' triples; blockers stop the
    # boop from disturbing them. Mover must choose one row (resolve phase).
    board = {(0, 0): (0, "K"), (1, 1): (0, "K"),      # diag, blocked by (0,0)
             (1, 3): (0, "K"), (3, 1): (0, "K"),      # anti-diag arms
             (0, 4): (1, "K"), (4, 0): (1, "K")}      # opp blockers behind
    s = mk(board=board, to_move=0)
    ns = G.apply_move(s, "2,2=K")
    check(ns.phase == "resolve" and ns.to_move == 0, "resolve phase expected")
    ms = G.legal_moves(ns)
    check(len(ms) == 6, f"2 rows x 3 anchor cells = 6 moves, got {ms}")
    at_center = [m for m in ms if m.startswith("2,2=G")]
    check(len(at_center) == 2, "centre cell anchors both rows")
    grad = G.apply_move(ns, at_center[0])
    check(grad.pools[0]["C"] == 3 and grad.to_move == 1, "chosen row graduates")
    check(sum(1 for (o, _k) in grad.board.values() if o == 0) == 2,
          "other row's outer pieces stay on the board")
    # serialize round-trip of the resolve-phase state too
    check(G.serialize(G.deserialize(G.serialize(ns))) == G.serialize(ns),
          "resolve-phase round-trip")
    json.dumps(G.serialize(ns))


def test_all_8_on_bed_pickup():
    # 7 scattered pieces + placing the 8th (no row) -> forced pick-up choice.
    board = {(0, 0): (0, "K"), (2, 0): (0, "K"), (4, 0): (0, "K"),
             (0, 2): (0, "K"), (4, 2): (0, "C"), (0, 4): (0, "K"),
             (2, 4): (0, "K")}
    s = mk(board=board, pools={0: {"K": 1, "C": 0}, 1: {"K": 8, "C": 0}},
           to_move=0)
    ns = G.apply_move(s, "5,5=K")
    check(ns.phase == "resolve", "all-8: resolve phase")
    ms = G.legal_moves(ns)
    check(len(ms) == 8 and all(m.endswith("=LIFT") for m in ms),
          f"all-8: 8 LIFT options, got {ms}")
    up_k = G.apply_move(ns, "0,0=LIFT")           # Kitten graduates
    check(up_k.pools[0] == {"K": 0, "C": 1} and (0, 0) not in up_k.board,
          f"lifted Kitten becomes a Cat in pool: {up_k.pools[0]}")
    up_c = G.apply_move(ns, "4,2=LIFT")           # Cat returns as a Cat
    check(up_c.pools[0] == {"K": 0, "C": 1} and (4, 2) not in up_c.board,
          "lifted Cat returns to pool")
    check(up_k.to_move == 1, "turn passes after pick-up")


def test_cat_row_win():
    s = mk(board={(0, 0): (0, "C"), (1, 1): (0, "C")},
           pools={0: {"K": 5, "C": 1}, 1: {"K": 8, "C": 0}}, to_move=0)
    ns = G.apply_move(s, "2,2=C")
    check(ns.winner == 0, "three Cats in a row should win")
    check(G.is_terminal(ns) and G.returns(ns) == [1.0, -1.0], "returns")
    check(G.legal_moves(ns) == [], "no moves at terminal")


def test_all_8_cats_win():
    board = {(0, 0): (0, "C"), (2, 0): (0, "C"), (4, 0): (0, "C"),
             (0, 2): (0, "C"), (4, 2): (0, "C"), (0, 4): (0, "C"),
             (2, 4): (0, "C")}
    s = mk(board=board, pools={0: {"K": 0, "C": 1}, 1: {"K": 8, "C": 0}},
           to_move=0)
    ns = G.apply_move(s, "5,5=C")
    check(ns.winner == 0, "all 8 Cats on the bed should win")


def test_opponent_row_waits_for_their_turn():
    # My boop pushes an OPPONENT kitten into their row of 3: nothing happens
    # on my turn; it graduates at the end of THEIR next turn (Dized FAQ:
    # "only the active player" resolves on their turn).
    board = {(2, 1): (1, "K"), (2, 2): (1, "K"), (2, 4): (1, "K")}
    s = mk(board=board, to_move=0)
    ns = G.apply_move(s, "2,5=K")                 # boops (2,4) down to (2,3)
    check(ns.board.get((2, 3)) == (1, "K"), "kitten booped into the column")
    check(ns.phase == "place" and ns.to_move == 1 and ns.winner is None,
          "opponent row must NOT resolve on the mover's turn")
    check(ns.pools[1]["C"] == 0, "no cats yet for the opponent")
    far = G.apply_move(ns, "5,0=K")               # their own quiet placement
    check(far.pools[1] == {"K": 4, "C": 3},
          f"row graduates on their own turn: {far.pools[1]}")


def test_mover_wins_ties():
    # The OPPONENT already has three Cats in a row on the board (booped
    # together on my previous turn); my placement completes MY cat row:
    # the active player wins (Dized FAQ: win checks only at the end of the
    # active player's turn).
    board = {(0, 0): (0, "C"), (1, 1): (0, "C"),
             (5, 3): (1, "C"), (5, 4): (1, "C"), (5, 5): (1, "C")}
    s = mk(board=board, pools={0: {"K": 5, "C": 1}, 1: {"K": 5, "C": 0}},
           to_move=0)
    ns = G.apply_move(s, "2,2=C")
    check(ns.winner == 0, "active player wins simultaneous rows")


def test_draw_backstops():
    # Ply cap: a quiet move at the cap yields an honest draw.
    s = mk(board={(5, 5): (1, "K")}, to_move=0)
    s.ply = MAX_PLIES - 1
    ns = G.apply_move(s, "0,0=K")
    check(ns.draw == "plycap" and G.is_terminal(ns)
          and G.returns(ns) == [0.0, 0.0], "ply-cap draw")
    # Threefold repetition: preload the successor position's key at count 2.
    s1 = mk(board={(5, 5): (1, "K")}, to_move=0)
    once = G.apply_move(s1, "0,0=K")
    key = G._poskey(once)
    s1b = mk(board={(5, 5): (1, "K")}, to_move=0)
    s1b.reps = {key: 2}
    rep = G.apply_move(s1b, "0,0=K")
    check(rep.draw == "repetition" and G.returns(rep) == [0.0, 0.0],
          "threefold-repetition draw")


def test_serialize_roundtrip():
    s = G.initial_state()
    rng = random.Random(7)
    for _ in range(25):
        if G.is_terminal(s):
            break
        s = G.apply_move(s, rng.choice(G.legal_moves(s)))
        d1 = G.serialize(s)
        check(G.serialize(G.deserialize(d1)) == d1, "round-trip drifted")
        json.dumps(d1)


def test_render_shape():
    s = G.initial_state()
    spec = G.render(s)
    check(spec["board"] == {"type": "square", "width": 6, "height": 6}, "board")
    check(spec["pieces"] == [], "no pieces at start")
    s2 = G.apply_move(s, "2,2=K")
    spec2 = G.render(s2)
    check(spec2["pieces"][0]["size"] == 1, "kitten renders small")
    check("Blue to place" in spec2["caption"], spec2["caption"])
    json.dumps(spec2)


def test_playouts():
    rng = random.Random(2024)
    N = 300
    wins = [0, 0]
    draws = {"repetition": 0, "plycap": 0}
    plies, max_ply = 0, 0
    for _ in range(N):
        s = G.initial_state()
        while not G.is_terminal(s):
            ms = G.legal_moves(s)
            check(ms, "non-terminal state with no legal moves")
            s = G.apply_move(s, rng.choice(ms))
        plies += s.ply
        max_ply = max(max_ply, s.ply)
        if s.winner is not None:
            wins[s.winner] += 1
        else:
            draws[s.draw] += 1
    print(f"  playouts: N={N} P0={wins[0]} P1={wins[1]} "
          f"rep-draws={draws['repetition']} plycap-draws={draws['plycap']} "
          f"avg-plies={plies / N:.1f} max-plies={max_ply}")
    check(wins[0] > 0 and wins[1] > 0, "both players should win sometimes")
    check(max_ply <= MAX_PLIES + 1, "termination bound")
    backstops = draws["repetition"] + draws["plycap"]
    check(backstops < N * 0.25, f"backstop rate too high: {backstops}/{N}")


def main():
    test_opening()
    test_boop_all_8_directions()
    test_blocking_and_no_chain()
    test_edge_boop_off_returns_to_pool()
    test_kitten_cannot_boop_cat()
    test_auto_graduation_single_row()
    test_mixed_row_graduates()
    test_multiple_rows_choice()
    test_all_8_on_bed_pickup()
    test_cat_row_win()
    test_all_8_cats_win()
    test_opponent_row_waits_for_their_turn()
    test_mover_wins_ties()
    test_draw_backstops()
    test_serialize_roundtrip()
    test_render_shape()
    test_playouts()
    print("SELFTEST OK")


if __name__ == "__main__":
    main()
