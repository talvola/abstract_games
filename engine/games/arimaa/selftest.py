"""Standalone correctness anchor for Arimaa (pure-stdlib).

Run from the engine dir:  PYTHONPATH=. python3 games/arimaa/selftest.py

Asserts:
  * the 16-piece reserve / 32-piece deployed setup,
  * a basic step, and that a rabbit CANNOT step backward,
  * FREEZE (a piece next to a stronger enemy with no friendly neighbour is frozen;
    a friendly neighbour unfreezes it),
  * a PUSH and a PULL (a stronger piece displaces an adjacent weaker enemy; you may
    NOT push an equal/stronger piece),
  * a TRAP capture (a piece on a trap with no friendly neighbour is removed; with a
    friendly neighbour it survives), including mid-turn,
  * the net-null illegal turn,
  * a rabbit reaching the goal row WINS (via apply_move),
  * capture-all-rabbits win,
  * serialize round-trip,
  * conformance (random play terminates, returns well-formed).

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""

from __future__ import annotations

import json
import sys

from games.arimaa.game import (
    Arimaa, ArimaaState, GOLD, SILVER, RESERVE, TRAPS,
    _is_frozen, _board_key, _pos_key, _resolve_traps,
)
from agp.conformance import check as check_conformance


def fail(msg: str):
    print(f"SELFTEST FAILED: {msg}")
    sys.exit(1)


def check(cond, msg):
    if not cond:
        fail(msg)


G = Arimaa()


def play_state(board, to_move=GOLD, steps_used=0, turn_start=None):
    """A mid-play state (setup done) with the given board."""
    if turn_start is None:
        turn_start = _board_key(board)
    return ArimaaState(board=dict(board), to_move=to_move, hands={GOLD: {}, SILVER: {}},
                       setup=False, steps_used=steps_used, turn_start=turn_start,
                       reps={}, ply=0, winner=None)


def main():
    # ---- reserve counts ----
    check(sum(RESERVE.values()) == 16, f"reserve total {sum(RESERVE.values())} != 16")
    check(RESERVE["R"] == 8 and RESERVE["E"] == 1 and RESERVE["M"] == 1, "reserve composition")
    check(TRAPS == frozenset([(2, 2), (5, 2), (2, 5), (5, 5)]), "trap squares")

    # ---- setup phase: deploy all 32 ----
    s = G.initial_state()
    check(s.setup and s.to_move == GOLD, "initial setup/gold")
    count = 0
    while s.setup:
        m = G.legal_moves(s)[0]
        s = G.apply_move(s, m)
        count += 1
    check(count == 32, f"deployed {count} pieces, expected 32")
    check(len(s.board) == 32, f"board has {len(s.board)} pieces after setup")
    check(s.to_move == GOLD and not s.setup, "play begins with Gold")
    check(sum(1 for o, t in s.board.values() if o == GOLD) == 16, "gold has 16")
    # all gold on rows 0-1, all silver on rows 6-7
    for (c, r), (o, t) in s.board.items():
        if o == GOLD:
            check(r in (0, 1), f"gold piece off home row at {c},{r}")
        else:
            check(r in (6, 7), f"silver piece off home row at {c},{r}")

    # ---- basic step ----
    st = play_state({(3, 3): (GOLD, "H"), (0, 0): (GOLD, "R"), (7, 7): (SILVER, "R")})
    moves = set(G.legal_moves(st))
    check("3,3>3,4" in moves, "horse should be able to step north")
    check("3,3>4,3" in moves, "horse should be able to step east")
    s2 = G.apply_move(st, "3,3>3,4")
    check(s2.board.get((3, 4)) == (GOLD, "H") and (3, 3) not in s2.board, "step applied")
    check(s2.steps_used == 1 and s2.to_move == GOLD, "same player, 1 step used")
    check("finish" in G.legal_moves(s2), "finish available after a step")

    # ---- rabbit cannot step backward ----
    st = play_state({(3, 3): (GOLD, "R"), (0, 0): (GOLD, "E"), (7, 7): (SILVER, "R")})
    rm = set(G.legal_moves(st))
    check("3,3>3,4" in rm, "gold rabbit can step forward (north)")
    check("3,3>4,3" in rm and "3,3>2,3" in rm, "gold rabbit can step sideways")
    check("3,3>3,2" not in rm, "gold rabbit must NOT step backward (south)")
    # silver rabbit: backward = north
    st_s = play_state({(3, 3): (SILVER, "R"), (0, 0): (SILVER, "E"), (7, 7): (GOLD, "R")},
                      to_move=SILVER)
    rms = set(G.legal_moves(st_s))
    check("3,3>3,2" in rms, "silver rabbit can step forward (south)")
    check("3,3>3,4" not in rms, "silver rabbit must NOT step backward (north)")

    # ---- freeze ----
    # Gold cat next to a silver elephant, no friendly neighbour -> frozen.
    b = {(3, 3): (GOLD, "C"), (3, 4): (SILVER, "E"), (0, 0): (GOLD, "R"), (7, 7): (SILVER, "R")}
    check(_is_frozen(b, 3, 3), "cat next to stronger enemy with no friend should be frozen")
    st = play_state(b)
    fm = set(G.legal_moves(st))
    check(not any(m.startswith("3,3>") for m in fm), "frozen cat must have no step moves")
    # add a friendly neighbour -> unfrozen
    b2 = dict(b)
    b2[(2, 3)] = (GOLD, "R")
    check(not _is_frozen(b2, 3, 3), "friendly neighbour should unfreeze the cat")
    # weaker enemy does NOT freeze: cat next to enemy rabbit is fine
    b3 = {(3, 3): (GOLD, "C"), (3, 4): (SILVER, "R"), (0, 0): (GOLD, "R"), (7, 7): (SILVER, "R")}
    check(not _is_frozen(b3, 3, 3), "weaker enemy must not freeze")

    # ---- push ----
    # Gold horse pushes adjacent silver cat into an empty square.
    b = {(3, 3): (GOLD, "H"), (3, 4): (SILVER, "C"), (0, 0): (GOLD, "R"), (7, 7): (SILVER, "R")}
    st = play_state(b)
    pm = set(G.legal_moves(st))
    check("push 3,3>3,4>3,5" in pm, "horse should be able to push cat north")
    s2 = G.apply_move(st, "push 3,3>3,4>3,5")
    check(s2.board.get((3, 5)) == (SILVER, "C"), "pushed cat moved to 3,5")
    check(s2.board.get((3, 4)) == (GOLD, "H"), "horse advanced into vacated 3,4")
    check((3, 3) not in s2.board, "horse left 3,3")
    check(s2.steps_used == 2, "push used 2 steps")
    # cannot push equal/stronger: horse vs horse
    b = {(3, 3): (GOLD, "H"), (3, 4): (SILVER, "H"), (0, 0): (GOLD, "R"), (7, 7): (SILVER, "R")}
    st = play_state(b)
    pm = set(G.legal_moves(st))
    check(not any(m.startswith("push 3,3>3,4") for m in pm), "must not push equal-strength")

    # ---- pull ----
    b = {(3, 3): (GOLD, "H"), (3, 4): (SILVER, "C"), (0, 0): (GOLD, "R"), (7, 7): (SILVER, "R")}
    st = play_state(b)
    pm = set(G.legal_moves(st))
    # puller h at 3,3 steps to empty 2,3 ; cat at 3,4 fills 3,3
    check("pull 3,3>2,3>3,4" in pm, "horse should be able to pull cat")
    s2 = G.apply_move(st, "pull 3,3>2,3>3,4")
    check(s2.board.get((2, 3)) == (GOLD, "H"), "puller moved to 2,3")
    check(s2.board.get((3, 3)) == (SILVER, "C"), "cat pulled into 3,3")
    check((3, 4) not in s2.board, "cat left 3,4")
    check(s2.steps_used == 2, "pull used 2 steps")

    # ---- trap capture ----
    # Silver cat alone on c3 (2,2) -> captured. Place an enemy that steps away so it
    # becomes unsupported. Simpler: a gold piece steps onto a trap with no friend.
    # Direct resolve check:
    b = {(2, 2): (SILVER, "C")}  # on a trap, no friendly neighbour
    check((2, 2) not in _resolve_traps(b), "unsupported trap piece must be removed")
    b2 = {(2, 2): (SILVER, "C"), (2, 1): (SILVER, "R")}  # supported
    check((2, 2) in _resolve_traps(b2), "supported trap piece must survive")
    # Mid-turn trap: gold dog on trap supported by a gold rabbit; rabbit steps away.
    b = {(2, 2): (GOLD, "D"), (2, 1): (GOLD, "R"), (0, 0): (GOLD, "E"), (7, 7): (SILVER, "R")}
    st = play_state(b)
    # step the supporting rabbit away: 2,1 -> 1,1 (sideways ok)
    s2 = G.apply_move(st, "2,1>1,1")
    check((2, 2) not in s2.board, "dog should be trapped after its support leaves")

    # ---- net-null illegal turn ----
    # Use a piece that can step out and back? A single step always changes the board,
    # so net-null only arises via a step + its reverse (2 steps). Construct it:
    b = {(3, 3): (GOLD, "H"), (0, 0): (GOLD, "E"), (7, 7): (SILVER, "R")}
    st = play_state(b)
    s1 = G.apply_move(st, "3,3>3,4")    # step out
    s2 = G.apply_move(s1, "3,4>3,3")    # step back -> board == turn_start
    check(_board_key(s2.board) == s2.turn_start, "board returned to start")
    check("finish" not in G.legal_moves(s2), "net-null finish must be illegal")
    # but there are still legal (changing) moves, so not terminal/empty
    check(len(G.legal_moves(s2)) > 0, "non-terminal state must offer some move")

    # ---- rabbit reaches goal -> win (via apply_move) ----
    # Gold rabbit on row 6 (one step from row 7 goal). Step it to row 7, then finish.
    b = {(4, 6): (GOLD, "R"), (0, 0): (GOLD, "E"), (7, 0): (SILVER, "R")}
    st = play_state(b)
    s1 = G.apply_move(st, "4,6>4,7")     # rabbit to goal rank (row 7)
    check(not G.is_terminal(s1), "win only resolves at finish, not mid-turn")
    s2 = G.apply_move(s1, "finish")
    check(G.is_terminal(s2) and s2.winner == GOLD, "gold wins by reaching goal rank")
    check(G.returns(s2) == [1.0, -1.0], "gold-win returns")

    # ---- capture-all-rabbits win ----
    # Silver has exactly one rabbit on a trap with no support; gold removes its support.
    # Setup: silver rabbit on c3 (2,2), its only support is silver cat at (2,1) which
    # gold pushes away. Simpler: silver's last rabbit is unsupported on a trap and a
    # gold step elsewhere... we need the rabbit to be removed BY a gold action.
    # Gold pushes the silver rabbit off support onto/around: easiest is push the
    # supporting piece. Construct: silver rabbit (only one) at (2,2) supported by a
    # silver cat at (3,2); a gold horse pushes that cat away.
    b = {
        (2, 2): (SILVER, "R"),          # silver's ONLY rabbit, on trap c3
        (3, 2): (SILVER, "C"),          # its only support
        (4, 2): (GOLD, "H"),            # gold horse adjacent to the cat
        (0, 0): (GOLD, "R"),            # gold keeps a rabbit
        (0, 7): (SILVER, "E"),          # silver non-rabbit so it isn't already lost
    }
    st = play_state(b)
    # horse 4,2 pushes cat 3,2 -> 3,3 (empty); horse 4,2 -> 3,2. Cat no longer
    # supports the rabbit on the trap.
    s1 = G.apply_move(st, "push 4,2>3,2>3,3")
    check((2, 2) not in s1.board, "silver's last rabbit should be trapped")
    s2 = G.apply_move(s1, "finish")
    check(G.is_terminal(s2) and s2.winner == GOLD, "gold wins by eliminating all silver rabbits")

    # ---- serialize round-trip ----
    for test_state in (G.initial_state(), st, s2, s):
        d = G.serialize(test_state)
        js = json.dumps(d)  # must be JSON-able
        back = G.deserialize(json.loads(js))
        check(G.serialize(back) == d, "serialize round-trip mismatch")

    # ---- conformance ----
    with open("games/arimaa/manifest.json") as f:
        manifest = json.load(f)
    report = check_conformance(G, manifest, games=12, seed=1, max_moves=4000)
    check(report.ok, f"conformance failed: {report.checks}")

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
