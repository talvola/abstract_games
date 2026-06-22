"""TwixT correctness anchor (pure stdlib): the bridge-crossing geometry, the
peg-placement ownership rules, automatic knight's-move bridging (and its
suppression when a link would cross an existing bridge of EITHER colour), the
connection win, and the full-board draw."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.twixt.game import TwixT, TState, RED, BLACK, _crosses, _seg_key  # noqa: E402

G = TwixT()


def main():
    # --- crossing geometry ------------------------------------------------
    assert _crosses(((0, 0), (1, 2)), ((0, 2), (1, 0)))          # an X crosses
    assert not _crosses(((0, 0), (1, 2)), ((0, 0), (2, 1)))      # shared endpoint
    assert not _crosses(((0, 0), (1, 2)), ((3, 0), (4, 2)))      # parallel, apart

    # --- placement ownership (size 12) ------------------------------------
    s = G.initial_state()
    red_cols = {int(m.split(",")[0]) for m in G.legal_moves(s)}
    assert red_cols == set(range(1, 11)), red_cols               # red: not col 0/11
    sb = TState(size=12, to_move=BLACK)
    black_rows = {int(m.split(",")[1]) for m in G.legal_moves(sb)}
    assert black_rows == set(range(1, 11)), black_rows           # black: not row 0/11
    # corners are never playable
    assert "0,0" not in G.legal_moves(s) and "11,11" not in G.legal_moves(sb)

    # --- automatic knight's-move bridging ---------------------------------
    s = TState(size=12, pegs={(2, 2): RED}, to_move=RED)
    # wait: it's red's turn but we want to ADD a red peg a knight away
    s2 = G.apply_move(s, "3,4")                                  # knight (1,2) from (2,2)
    assert _seg_key((2, 2), (3, 4)) in s2.bridges[RED] and len(s2.bridges[RED]) == 1

    # --- a link that would CROSS an existing bridge is suppressed ----------
    #  Black already has the bridge (1,0)-(2,2); Red placing (1,2) with a red peg
    #  at (2,0) would make (1,2)-(2,0), which crosses it -> no bridge added.
    s = TState(size=12, pegs={(2, 0): RED}, bridges={RED: set(), BLACK: {_seg_key((1, 0), (2, 2))}},
               to_move=RED)
    s2 = G.apply_move(s, "1,2")
    assert _crosses(_seg_key((1, 2), (2, 0)), _seg_key((1, 0), (2, 2)))
    assert s2.bridges[RED] == set(), "bridge crossing an existing one must be suppressed"

    # --- connection win (size 5: red joins row 0 to row 4) ----------------
    s = TState(size=5, pegs={(1, 0): RED, (2, 2): RED}, bridges={RED: {_seg_key((1, 0), (2, 2))},
               BLACK: set()}, to_move=RED)
    s2 = G.apply_move(s, "3,4")                                  # bridges to (2,2), reaches row 4
    assert s2.winner == RED and G.returns(s2) == [1.0, -1.0]

    # --- termination: random games always end ------------------------------
    import random
    rng = random.Random(9)
    for _ in range(10):
        st = G.initial_state(options={"size": 6})
        while not G.is_terminal(st):
            st = G.apply_move(st, rng.choice(G.legal_moves(st)))
        assert st.winner is not None                            # a player or "draw"

    assert G.serialize(G.deserialize(G.serialize(s2))) == G.serialize(s2)
    print("twixt selftest OK")


if __name__ == "__main__":
    main()
