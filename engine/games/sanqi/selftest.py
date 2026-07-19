"""SanQi selftest — pure stdlib.

Anchors (designer's rules document "The Rules of SanQi" — the same ruleset
as the Abstract Games #17 reprint, pp. 13-17):

1. Board/pattern geometry: hex-4 = 37 cells (111 opening placements);
   goal-window census on hex-4 = 19 circles + 12 lines + 36 triangles
   (hand-derived independently); the goal-diagram patterns are windows.
2. The section 2.32 worked replacement example, replayed exactly: "The Xia
   and the isolated Zhong can both be REPLACEd by a Shang. But none of the
   others can be REPLACEd" — the complete legal replacement set is asserted.
3. Immunity: the opponent's just-created piece is not replaceable for one
   turn; the protection shifts to the next move's piece afterwards.
4. Goals, each replayed one move from completion, both seats:
   circle (First only), line (Second only), triangle (either) — including
   the "end of that player's turn" persistence rule: a pattern completed
   on the opponent's move wins for you at the end of YOUR next turn.
5. Termination backstops (implementation notes documented in rules.md):
   consecutive-replacement cap, hard ply cap, and full-board stalemate all
   end as honest draws (winner None, returns [0, 0]).
6. Random-playout smoke: seeded random games terminate with well-formed
   returns; serialization round-trips; heuristic returns a per-seat list
   (exercised through MCTSBot with a forced rollout cutoff).
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agp.loader import load_from_dir  # noqa: E402
from agp.mcts import MCTSBot  # noqa: E402

PKG = Path(__file__).resolve().parent
man, g = load_from_dir(PKG)

checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        print(f"FAIL: {msg}")
        sys.exit(1)


def mk(pieces, to_move=0, immune=None, size=4, repl_run=0, ply=None):
    """Build a state via the public deserialize API. pieces: {"q,r": type}."""
    return g.deserialize({
        "size": size,
        "board": dict(pieces),
        "to_move": to_move,
        "immune": immune,
        "winner": None,
        "over": False,
        "end": None,
        "repl_run": repl_run,
        "ply": ply if ply is not None else len(pieces),
    })


def replacement_moves(state):
    """Legal moves whose target cell is occupied."""
    board = g.serialize(state)["board"]
    return {m for m in g.legal_moves(state) if m.split("=")[0] in board}


# ---------------------------------------------------------------- 1. geometry
s0 = g.initial_state({"size": 4})
ok(g.current_player(s0) == 0, "First moves first")
moves0 = g.legal_moves(s0)
ok(len(moves0) == 37 * 3, f"hex-4 opening: 37 cells x 3 types, got {len(moves0)}")
ok(len(set(moves0)) == len(moves0), "no duplicate moves")
s5 = g.initial_state({"size": 5})
ok(len(g.legal_moves(s5)) == 61 * 3, "hex-5 opening: 61 cells x 3 types")

# window census on hex-4 (independent hand-derivation, see docstring):
# circles = interior cells with a full ring = hexhex-3 cell count = 19;
# lines of 6 = rows of length>=6 per axis: (7-|r|>=6) -> 2+1+1 = 4 per axis;
# side-3 triangles = 18 per geometric orientation x 2 = 36.
_windows = sys.modules[type(g).__module__]._windows

wins4, by_cell4 = _windows(4)
census = {}
for kind, cells in wins4:
    census[kind] = census.get(kind, 0) + 1
    ok(len(cells) == 6 and len(set(cells)) == 6, "every window has 6 cells")
ok(census == {"circle": 19, "line": 12, "triangle": 36},
   f"hex-4 window census, got {census}")

# the goal-diagram triangle (doc section 2.4, X pieces) is a triangle window
tri_doc = frozenset([(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (0, 2)])
ok(any(kind == "triangle" and frozenset(cells) == tri_doc
       for kind, cells in wins4), "doc triangle is a window")
# the ring around 0,0 is a circle window
ring = frozenset([(1, 0), (0, 1), (1, -1), (-1, 0), (0, -1), (-1, 1)])
ok(any(kind == "circle" and frozenset(cells) == ring
       for kind, cells in wins4), "ring around 0,0 is a window")

# ------------------------------------------- 2. section 2.32 worked example
# Doc diagram (converted from the brick diagram to axial):
#   Z(0,0)  S(-1,1) S(1,0) S(0,1)  Z(-1,2)  X(1,1)  Z(0,2)
# "The Xia and the isolated Zhong can both be REPLACEd by a Shang. But none
#  of the others can be REPLACEd."
EX232 = {"0,0": "Z", "-1,1": "S", "1,0": "S", "0,1": "S",
         "-1,2": "Z", "1,1": "X", "0,2": "Z"}
sx = mk(EX232, to_move=0)
ok(replacement_moves(sx) == {"0,0=S", "1,1=S"},
   f"2.32 example: exactly Xia+isolated Zhong replaceable by Shang, "
   f"got {sorted(replacement_moves(sx))}")
ok(len(g.legal_moves(sx)) == (37 - 7) * 3 + 2, "2.32 placements + 2 replacements")
ok(g.describe_move(sx, "0,0=S").startswith("replace"), "describe replacement")
ok(g.describe_move(sx, "2,-2=Z").startswith("place"), "describe placement")

# serialize round-trip
ok(g.serialize(g.deserialize(g.serialize(sx))) == g.serialize(sx),
   "serialize round-trips")

# ------------------------------------------------------------- 3. immunity
si = mk(EX232, to_move=0, immune="1,1")   # opponent just created the Xia
ok(replacement_moves(si) == {"0,0=S"},
   "just-created piece is protected for one turn")
s_after = g.apply_move(si, "2,-2=Z")      # First plays elsewhere
ok(not g.is_terminal(s_after), "no accidental win")
ok(g.current_player(s_after) == 1, "turn passes")
rm = replacement_moves(s_after)
ok(rm == {"0,0=S", "1,1=S"}, f"exact replacement set after the shift, got {sorted(rm)}")
ok("1,1=S" in rm, "protection lapses after one turn")
ok(not any(m.startswith("2,-2=") for m in rm),
   "protection shifted to the new piece")

# a replacement also creates a protected piece (AG#17: "placed or replaced")
sr = g.apply_move(mk(EX232, to_move=0), "1,1=S")   # First replaces the Xia
ok(g.serialize(sr)["board"]["1,1"] == "S", "replacement rewrites the cell")
ok(g.serialize(sr)["immune"] == "1,1", "replaced piece is now the protected one")
ok(g.serialize(sr)["repl_run"] == 1, "replacement run counts")
ok(g.serialize(g.apply_move(sr, "3,0=Z"))["repl_run"] == 0,
   "placement resets the replacement run")

# --------------------------------------------------- 4. goals, both seats
RING5 = {"1,0": "S", "0,1": "S", "1,-1": "S", "-1,0": "S", "-1,1": "S"}

# First completes a circle -> wins
w = g.apply_move(mk(RING5, to_move=0), "0,-1=S")
ok(g.is_terminal(w) and g.returns(w) == [1.0, -1.0]
   and g.serialize(w)["end"] == "circle", "First wins by circle")

# Second completes the same circle -> NOT a win for Second...
w2 = g.apply_move(mk(RING5, to_move=1), "0,-1=S")
ok(not g.is_terminal(w2), "a circle does not win for Second")
# ...but it wins for First at the end of First's next (unrelated) turn
w3 = g.apply_move(w2, "3,0=Z")
ok(g.is_terminal(w3) and g.returns(w3) == [1.0, -1.0]
   and g.serialize(w3)["end"] == "circle",
   "persisting circle wins at the end of First's own turn")

LINE5 = {"-3,0": "Z", "-2,0": "Z", "-1,0": "Z", "0,0": "Z", "1,0": "Z"}

# Second completes a line -> wins
w = g.apply_move(mk(LINE5, to_move=1), "2,0=Z")
ok(g.is_terminal(w) and g.returns(w) == [-1.0, 1.0]
   and g.serialize(w)["end"] == "line", "Second wins by line")

# First completes the line -> no win; Second then wins on any quiet move
w2 = g.apply_move(mk(LINE5, to_move=0), "2,0=Z")
ok(not g.is_terminal(w2), "a line does not win for First")
w3 = g.apply_move(w2, "0,-3=S")
ok(g.is_terminal(w3) and g.returns(w3) == [-1.0, 1.0],
   "persisting line wins at the end of Second's own turn")

TRI5 = {"0,0": "X", "1,0": "X", "2,0": "X", "0,1": "X", "1,1": "X"}

for seat, ret in ((0, [1.0, -1.0]), (1, [-1.0, 1.0])):
    w = g.apply_move(mk(TRI5, to_move=seat), "0,2=X")
    ok(g.is_terminal(w) and g.returns(w) == ret
       and g.serialize(w)["end"] == "triangle",
       f"seat {seat} wins by triangle")

# -------------------------------------------------------- 5. draw backstops
# consecutive-replacement cap (hex-4 cap = max(40, 37) = 40)
sd = mk(EX232, to_move=0, repl_run=39)
d = g.apply_move(sd, "0,0=S")             # 40th consecutive replacement
ok(g.is_terminal(d) and g.returns(d) == [0.0, 0.0]
   and g.serialize(d)["winner"] is None, "no-progress draw is honest")

# hard ply cap (hex-4: 20*37 = 740)
sp = mk({}, to_move=0, ply=739)
d = g.apply_move(sp, "0,0=S")
ok(g.is_terminal(d) and g.returns(d) == [0.0, 0.0], "ply-cap draw is honest")

# full-board stalemate -> draw. Mechanism test on a hand-built (unreachable)
# board: all Shang except one vacancy; after Second fills it with a Zhong,
# First has no placement and no legal replacement (the Zhong is protected,
# and no Shang has attackers >= defenders+2).
full = {}
n = 3
for q in range(-n, n + 1):
    for r in range(-n, n + 1):
        if max(abs(q), abs(r), abs(q + r)) <= n and (q, r) != (0, 0):
            full[f"{q},{r}"] = "S"
d = g.apply_move(mk(full, to_move=1), "0,0=Z")
ok(g.is_terminal(d) and g.serialize(d)["winner"] is None
   and g.returns(d) == [0.0, 0.0]
   and g.serialize(d)["end"] == "no legal moves", "stalemate is an honest draw")

# ---------------------------------------------- 6. smoke: playouts, bot eval
h = g.heuristic(mk(RING5, to_move=0))
ok(isinstance(h, list) and len(h) == 2 and h[0] > 0,
   "heuristic is a per-seat payoff list favouring First's 5-ring")

# forced rollout cutoff exercises the heuristic inside MCTS back-prop
mv = MCTSBot(random.Random(1), iterations=25, max_rollout=4).select(
    g, g.initial_state({"size": 4}))
ok(mv in g.legal_moves(g.initial_state({"size": 4})), "MCTSBot returns a legal move")

outcomes = {0: 0, 1: 0, None: 0}
total_plies = 0
for i in range(60):
    rng = random.Random(1000 + i)
    st = g.initial_state({"size": 4})
    plies = 0
    while not g.is_terminal(st):
        lm = g.legal_moves(st)
        ok(len(lm) > 0, "non-empty legal moves on non-terminal state")
        st = g.apply_move(st, rng.choice(lm))
        plies += 1
        ok(plies <= 20 * 37, "ply cap bounds every game")
    r = g.returns(st)
    ok(len(r) == 2 and all(x in (-1.0, 0.0, 1.0) for x in r), "well-formed returns")
    outcomes[g.serialize(st)["winner"]] += 1
    total_plies += plies
ok(outcomes[0] + outcomes[1] > 0, "random play produces decisive games")
print(f"random hex-4 playouts: First {outcomes[0]}, Second {outcomes[1]}, "
      f"draws {outcomes[None]}, avg plies {total_plies / 60:.1f}")

print(f"sanqi selftest OK — {checks} checks passed")
