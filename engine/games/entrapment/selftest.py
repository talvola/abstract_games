"""Entrapment correctness anchors (pure stdlib).

Anchored on the Boardspace.net official rules + the Boardspace Java reference
implementation (EntrapmentBoard.java) semantics: jump-flip, trapped vs dead
(immediate capture), the neighbour-helper escape, the mandatory-escape first
action, the double-trap kill-selection by the mover, the second-entrapment
auto-kill, exact legal-move counts, and random-playout termination.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.entrapment.game import Entrapment  # noqa: E402

G = Entrapment()


def mk(**kw):
    """Build a state via deserialize (the sanctioned raw constructor)."""
    d = {"w": 7, "h": 7, "nro": 3,
         "ro": [[None] * 3, [None] * 3], "bars": {}, "trapped": [],
         "unplaced": [0, 0], "supply": [20, 20], "dead": [0, 0],
         "to_move": 0, "phase": "act1", "placement_done": True,
         "single_turn": False, "ply": 40, "nop": 0, "winner": None, "draw": False}
    d.update(kw)
    s = G.deserialize(d)
    # sanity: supplied trapped flags must be ground truth
    occ = G._occ(s)
    for pl in (0, 1):
        for c in s.ro[pl]:
            if c:
                assert G._is_trapped(s, c, occ) == (c in s.trapped), \
                    f"inconsistent trapped flag for {c}"
    return s


def test_setup_and_single_turn():
    s = G.initial_state()
    assert s.phase == "place" and len(G.legal_moves(s)) == 49
    s = G.apply_move(s, "0,0")            # W a1
    assert s.to_move == 1 and len(G.legal_moves(s)) == 48
    for m in ["12,12", "0,12", "12,0", "6,6", "12,6"]:
        s = G.apply_move(s, m)
    # setup done -> White's ONE-action turn: 84 barrier drops + 16 roamer moves
    assert s.placement_done and s.single_turn and s.phase == "act2" and s.to_move == 0
    lm = G.legal_moves(s)
    drops = [m for m in lm if m.startswith("B@")]
    moves = [m for m in lm if ">" in m]
    assert len(drops) == 84 and len(moves) == 16 and len(lm) == 100
    # one action only: after it, it is Black's turn
    s2 = G.apply_move(s, "B@1,0")
    assert s2.to_move == 1 and s2.phase == "act1" and s2.supply[0] == 24
    # normal turn is TWO actions
    s3 = G.apply_move(s2, "12,12>12,8")
    assert s3.to_move == 1 and s3.phase == "act2"
    s4 = G.apply_move(s3, "B@11,0")
    assert s4.to_move == 0 and s4.phase == "act1"
    # 6x7 variant
    s6 = G.initial_state({"board": "6x7", "roamers": 4})
    assert s6.w == 7 and s6.h == 6 and s6.nro == 4
    assert len(G.legal_moves(s6)) == 42


def test_jump_flip():
    # Friendly resting barrier east of a1: both 1- and 2-step jumps legal, flip it.
    s = mk(ro=[["0,0", None, None], ["12,12", None, None]], dead=[2, 2],
           bars={"1,0": [0, False]})
    assert set(G.legal_moves(s)) == {"0,0>2,0", "0,0>4,0", "0,0>0,2", "0,0>0,4"}
    s1 = G.apply_move(s, "0,0>2,0")
    assert s1.bars["1,0"] == [0, True], "1-step jump must flip the barrier"
    s2 = G.apply_move(s, "0,0>4,0")
    assert s2.bars["1,0"] == [0, True] and "4,0" in G._occ(s2)
    assert "(flips barrier)" in G.describe_move(s, "0,0>2,0")
    # Enemy resting barrier: impassable (no eastward move at all).
    se = mk(ro=[["0,0", None, None], ["12,12", None, None]], dead=[2, 2],
            bars={"1,0": [1, False]})
    assert set(G.legal_moves(se)) == {"0,0>0,2", "0,0>0,4"}
    # Standing friendly barrier: impassable too.
    su = mk(ro=[["0,0", None, None], ["12,12", None, None]], dead=[2, 2],
            bars={"1,0": [0, True]})
    assert set(G.legal_moves(su)) == {"0,0>0,2", "0,0>0,4"}
    # At most ONE jump per move: barriers in BOTH crossed grooves kill the 2-step.
    sj = mk(ro=[["0,0", None, None], ["12,12", None, None]], dead=[2, 2],
            bars={"1,0": [0, False], "3,0": [0, False]})
    lm = set(G.legal_moves(sj))
    assert "0,0>2,0" in lm and "0,0>4,0" not in lm
    # ...and jumping a friendly roamer + a barrier together is also barred.
    sk = mk(ro=[["0,0", "2,0", None], ["12,12", None, None]], dead=[1, 2],
            bars={"1,0": [0, False]})
    lm = set(G.legal_moves(sk))
    assert "0,0>4,0" not in lm             # would jump roamer AND barrier
    assert "2,0>2,2" in lm                 # the front roamer moves freely


def test_immediate_capture_and_win():
    # Black's last roamer at a1, White barrier already north; sealing the east
    # groove captures it immediately (no escape) and wins the game.
    s = mk(ro=[["6,6", "6,10", "8,8"], ["0,0", None, None]], dead=[0, 2],
           bars={"0,1": [0, False]}, to_move=0, phase="act2")
    s1 = G.apply_move(s, "B@1,0")
    assert s1.dead[1] == 3 and "0,0" not in G._occ(s1)
    assert G.is_terminal(s1) and s1.winner == 0 and G.returns(s1) == [1.0, -1.0]


def test_escapable_trap_and_mandatory_escape():
    # Sealing a1 whose east groove holds BLACK's OWN resting barrier: trapped
    # but alive (it can jump out); Black's next first action is escape-only.
    s = mk(ro=[["6,6", "6,10", "8,8"], ["0,0", "12,12", "12,0"]],
           bars={"1,0": [1, False]}, to_move=0, phase="act2")
    s1 = G.apply_move(s, "B@0,1")
    assert "0,0" in G._occ(s1), "escapable trapped roamer must NOT be captured"
    assert s1.trapped == {"0,0"} and s1.to_move == 1 and s1.phase == "act1"
    assert set(G.legal_moves(s1)) == {"0,0>2,0", "0,0>4,0"}, "escape moves only"
    s2 = G.apply_move(s1, "0,0>2,0")
    assert s2.bars["1,0"] == [1, True]     # escaped by flipping its own barrier
    assert s2.trapped == set() and s2.phase == "act2"
    assert any(m.startswith("B@") for m in G.legal_moves(s2))


def test_helper_escape():
    # a1 trapped with NO move of its own; adjacent friendly b1 (empty groove
    # between) can move -> a1 survives, and the forced first action is any
    # move of the helper b1.
    s = mk(ro=[["6,10", None, None], ["0,0", "2,0", None]], dead=[2, 1],
           bars={"0,1": [0, False], "3,0": [0, False]},
           trapped=["0,0"], to_move=1, phase="act1")
    occ = G._occ(s)
    assert G._roamer_moves(s, "0,0", occ) == []      # the trapped one is stuck
    assert not G._is_dead(s, "0,0", occ), "helper neighbour keeps it alive"
    assert set(G.legal_moves(s)) == {"2,0>2,2", "2,0>2,4"}


def test_double_trap_mover_chooses():
    # White's 2-step move lands d4=(6,6), simultaneously trapping Black c4 and
    # e4 (each alive via its own jumpable barrier) -> the MOVER picks the victim.
    bars = {"4,7": [0, False], "4,5": [0, False], "3,6": [1, False],
            "8,7": [0, False], "8,5": [0, False], "9,6": [1, False]}
    s = mk(ro=[["6,2", None, None], ["4,6", "8,6", None]], dead=[2, 1],
           bars=bars, to_move=0, phase="act1")
    s1 = G.apply_move(s, "6,2>6,6")
    assert s1.phase == "kill_other1" and G.current_player(s1) == 0
    assert s1.trapped == {"4,6", "8,6"} and s1.dead[1] == 1
    assert G.legal_moves(s1) == ["4,6", "8,6"]
    s2 = G.apply_move(s1, "4,6")
    assert s2.dead[1] == 2 and "4,6" not in G._occ(s2)
    assert s2.trapped == {"8,6"}, "the unchosen roamer stays trapped"
    assert s2.phase == "act2" and s2.to_move == 0, "kill is part of the same turn"
    assert G.describe_move(s1, "4,6") == "capture c4"


def test_double_trap_second_action_and_both_auto_killed():
    # (QA regression, verified against the Boardspace Java oracle.)
    # 1) The double-trap on the SECOND action -> kill_other2, and the turn
    #    ends right after the mover's choice.
    bars = {"4,7": [0, False], "4,5": [0, False], "3,6": [1, False],
            "8,7": [0, False], "8,5": [0, False], "9,6": [1, False]}
    s = mk(ro=[["6,2", "0,0", None], ["4,6", "8,6", None]], dead=[1, 1],
           bars=bars, to_move=0, phase="act2")
    s1 = G.apply_move(s, "6,2>6,6")
    assert s1.phase == "kill_other2" and G.current_player(s1) == 0
    s2 = G.apply_move(s1, "8,6")
    assert s2.dead[1] == 2 and s2.to_move == 1 and s2.phase == "act1"
    assert set(G.legal_moves(s2)) == {"4,6>2,6", "4,6>0,6"}, "forced escape"
    # 2) If a player ALREADY has a trapped roamer, an action that newly traps
    #    TWO more kills BOTH immediately (Java checkTrapped prevTrapped>0
    #    fires per newly-trapped roamer) -- no selection phase.
    bars2 = dict(bars)
    bars2.update({"1,0": [1, False], "0,1": [0, False]})
    s = mk(ro=[["6,2", None, None], ["4,6", "8,6", "0,0"]], dead=[2, 0],
           bars=bars2, trapped=["0,0"], to_move=0, phase="act1")
    s1 = G.apply_move(s, "6,2>6,6")
    assert s1.dead[1] == 2 and s1.trapped == {"0,0"}
    occ = G._occ(s1)
    assert "4,6" not in occ and "8,6" not in occ
    assert s1.phase == "act2" and s1.to_move == 0, "no kill-selection phase"


def test_second_entrapment_auto_kill():
    # Black e4 already trapped (alive). White's barrier seals c4 (also alive
    # via its own jumpable south barrier) -> c4 is a SECOND trapped roamer and
    # is captured immediately, no choice offered.
    bars = {"4,7": [0, False], "4,5": [1, False],
            "8,7": [0, False], "8,5": [0, False], "9,6": [1, False]}
    s = mk(ro=[["6,6", None, None], ["4,6", "8,6", None]], dead=[2, 1],
           bars=bars, trapped=["8,6"], to_move=0, phase="act2")
    s1 = G.apply_move(s, "B@3,6")
    assert s1.dead[1] == 2 and "4,6" not in G._occ(s1)
    assert s1.trapped == {"8,6"}
    assert s1.to_move == 1 and s1.phase == "act1"
    assert set(G.legal_moves(s1)) == {"8,6>10,6", "8,6>12,6"}


def test_relocation_when_supply_empty():
    s = mk(ro=[["0,0", None, None], ["12,12", None, None]], dead=[2, 2],
           bars={"5,6": [0, False], "6,5": [0, True], "7,6": [1, False]},
           supply=[0, 20], to_move=0, phase="act2")
    lm = G.legal_moves(s)
    assert not any(m.startswith("B@") for m in lm)
    relocs = [m for m in lm if ">" in m and int(m.split(">")[0].split(",")[0]) % 2
              + int(m.split(">")[0].split(",")[1]) % 2 == 1]
    # only the own RESTING barrier (5,6) may move: 84 grooves - 3 occupied
    assert len(relocs) == 81 and all(m.startswith("5,6>") for m in relocs)
    s1 = G.apply_move(s, "5,6>1,0")
    assert "5,6" not in s1.bars and s1.bars["1,0"] == [0, False]
    assert s1.to_move == 1


def test_serialize_and_bot():
    s = G.initial_state()
    for m in ["0,0", "12,12", "0,12", "12,0", "6,6", "12,6", "B@1,0"]:
        s = G.apply_move(s, m)
    blob = G.serialize(s)
    assert json.dumps(blob) == json.dumps(G.serialize(G.deserialize(blob)))
    spec = G.render(s)
    assert spec["board"]["type"] == "polygons"
    assert len(spec["board"]["cells"]) == 49 + 84       # squares + grooves
    assert any(p.get("shape") == "fill" for p in spec["pieces"])
    # heuristic must be a per-seat payoff list (forced rollout cutoff)
    from agp.mcts import MCTSBot
    h = G.heuristic(s)
    assert isinstance(h, list) and len(h) == 2
    m = MCTSBot(random.Random(1), iterations=16, max_rollout=4).select(G, s)
    assert m in G.legal_moves(s)


def check_invariants(s):
    occ = G._occ(s)
    for pl in (0, 1):
        on_board = sum(1 for c in s.ro[pl] if c)
        assert on_board + s.dead[pl] + s.unplaced[pl] == s.nro, "roamer conservation"
        for c in s.ro[pl]:
            if c:
                assert G._is_trapped(s, c, occ) == (c in s.trapped), \
                    "trapped flags must be ground truth"
        if s.phase in ("place", "act1", "act2"):
            assert G._ntrap(s, pl) <= 1, \
                "a player can never keep two trapped roamers"
    for g, (o, up) in s.bars.items():
        gx, gy = (int(v) for v in g.split(","))
        assert (gx + gy) % 2 == 1 and o in (0, 1)


def test_random_termination():
    outcomes = {"win": 0, "draw": 0}
    for seed in range(20):
        rng = random.Random(seed)
        s = G.initial_state({"board": "7x7" if seed % 2 else "6x7"})
        for step in range(5000):
            if G.is_terminal(s):
                break
            lm = G.legal_moves(s)
            assert lm, "non-terminal state with no legal moves"
            s = G.apply_move(s, rng.choice(lm))
            if step % 7 == 0:
                check_invariants(s)
        assert G.is_terminal(s), f"seed {seed} did not terminate"
        r = G.returns(s)
        assert len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r)
        outcomes["draw" if s.winner is None else "win"] += 1
    print(f"  random playouts: {outcomes}")


def main():
    for fn in [test_setup_and_single_turn, test_jump_flip,
               test_immediate_capture_and_win,
               test_escapable_trap_and_mandatory_escape, test_helper_escape,
               test_double_trap_mover_chooses,
               test_double_trap_second_action_and_both_auto_killed,
               test_second_entrapment_auto_kill,
               test_relocation_when_supply_empty, test_serialize_and_bot,
               test_random_termination]:
        fn()
        print(f"ok {fn.__name__}")
    print("entrapment selftest: all tests passed")


if __name__ == "__main__":
    main()
