"""Differential oracle: xiang_hex vs. the Game Courier GAME code.

MANUAL / ONE-TIME.  Not imported by `selftest.py` (which must stay pure-stdlib
and fast); this file is the one-off cross-check that anchored the port, kept
with it the way `games/kropki/_diff_oppai.py` and `games/blokus/_diff_pentobi.py`
are kept with theirs.

    cd engine && PYTHONPATH=. python3 games/xiang_hex/_diff_gamecourier.py \
        [n_games] [n_random_positions] [--literal-G]

It is an INDEPENDENT reimplementation of the rule-enforcing GAME code carried by
Fergus Duniho's Game Courier preset for Xiang Hex (`xianghex.gcsettings`, from
https://www.chessvariants.com/play.php?game=Xiang%20Hex&settings=xianghex),
written in Game Courier's own (file, rank) coordinate space with Game Courier's
own movement primitives, then compared legal-move-set for legal-move-set against
the platform module -- every ply of `n_games` random games and both sides of
`n_random_positions` scattered positions.

Last run: 10,675 positions, 0 mismatches (40 games + 600 scattered positions).

The preset's `def` clauses, transcribed verbatim (uppercase = Red):

  def N  checkatwostep #0 #1 0 1 1 1 or ... (12 clauses)
  def P  checkaleap -2 1 or checkaleap 2 -1 or checkaleap -1 1
         or checkaleap 1 0 and >= + rank #1 >> file #1 1 7 or checkaleap 0 1
  def R  checkaride 1 -1 or checkaride -1 1 or checkride 0 1
  def C  cond cond empty #0 capture (not empty #1) (hops) (rides) and #1
  def G  checkride #0 #1 1 0 and == #G #1
         or eval (checkaleap 1 -1 or checkaleap -1 1 or checkleap 0 1) and flag #1
  def F  eval (six diagonal checkaleaps) and flag #1 and #0
  def E  eval (six checkatwostep) and <= + rank #1 >> + file #1 1 1 7 and #0

Three properties of the GAME language that the transcription depends on, each
pinned against the `xiangqi` include the preset itself pulls in
(https://www.chessvariants.com/play/pbm/includes/xiangqi.txt), where the same
primitives describe the ordinary square-board game and the geometry is known:

* **`a`-prefixed primitives are the EXACT delta; unprefixed ones are the
  symmetric expansion.**  In the include, `def P ... or checkaleap #0 #1 0 1`
  is the Pawn's single forward step (the symmetric reading would let it retreat)
  while `def R checkride #0 #1 0 1` is the Rook's four lines.  Here that makes
  the Chariot's `checkaride 1 -1 or checkaride -1 1 or checkride 0 1` exactly the
  six hex orthogonals.
* **`and`/`or` have no precedence -- strictly left to right.**  The include's
  `def P checkaleap -1 0 or checkaleap 1 0 and > rank #0 4 or checkaleap 0 1`
  only describes Xiangqi if the gate binds BOTH sideways steps, i.e. if it parses
  as `((a or b) and gate) or forward`.  So Xiang Hex's Soldier gates all four of
  its extra steps, not just the last one before the `and`.
* **`rank` and `file` are 0-BASED.**  The include's Red Pawn may step sideways
  when `> rank #0 4`; on a 10-rank board a Red Pawn crosses after rank 5, which
  is `rank >= 5` 1-based and `> 4` 0-based.  `def E ... < rank #1 5` says the
  same for the Elephant.  With 0-based file and rank, Xiang Hex's Soldier gate
  `rank #1 + (file #1 >> 1) >= 7` is *exactly* "the destination is on or beyond
  the river" (D = q + 2r <= 0) and is the exact mirror of Blue's clause -- with
  either index 1-based it is neither.

`--literal-G` additionally reports how often the preset's literal `def G`
disagrees.  Both General clauses in the preset test `== #G #1`, and `#G` holds
RED's General's square, so `def g` is right and `def G` can never fire: in the
preset Red may not face the enemy General but Blue may.  The `xiangqi` include's
own symmetric pair (`== space #1 g` / `== space #1 G`) and the preset's own
symmetric `def GL` helper show that to be a copy-paste slip, so the module
implements the rule symmetrically; see note 6 of rules.md.  The divergence is
not academic -- 804 of 10,675 positions on the last run.
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from agp.loader import load_from_dir          # noqa: E402

MAN, GAME = load_from_dir(HERE)
GM = sys.modules[type(GAME).__module__]

# ---------------------------------------------------------------- GC geometry
FILES = "abcdefghi"


def ON(sq):
    f, R = sq
    return 0 <= f <= 8 and 0 <= R <= 10 and 4 <= f + R <= 14


ALL = [(f, R) for f in range(9) for R in range(11) if ON((f, R))]

# Palace flags exactly as the preset sets them (both palaces, no colour).
FLAGS = set()
for _n in ("e1 f1 d2 e2 f2 d3 e3 e9 f9 d10 e10 f10 d11 e11").split():
    FLAGS.add((FILES.index(_n[0]), int(_n[1:]) - 1))


def symset(a, b):
    out = set()
    for x, y in ((a, b), (b, a)):
        for sx in (1, -1):
            for sy in (1, -1):
                out.add((sx * x, sy * y))
    return sorted(out)


# ------------------------------------------------------- GC move primitives
def checkaleap(bd, o, d, df, dr):
    return (d[0] - o[0], d[1] - o[1]) == (df, dr)


def checkleap(bd, o, d, df, dr):
    return (d[0] - o[0], d[1] - o[1]) in symset(df, dr)


def _ray(bd, o, d, df, dr, screens):
    """True if d is reachable from o along (df,dr) with exactly `screens`
    occupied cells strictly in between."""
    cur = (o[0] + df, o[1] + dr)
    n = 0
    while ON(cur):
        if cur == d:
            return n == screens
        if cur in bd:
            n += 1
            if n > screens:
                return False
        cur = (cur[0] + df, cur[1] + dr)
    return False


def checkaride(bd, o, d, df, dr):
    return _ray(bd, o, d, df, dr, 0)


def checkride(bd, o, d, df, dr):
    return any(_ray(bd, o, d, a, b, 0) for a, b in symset(df, dr))


def checkahop(bd, o, d, df, dr):
    return _ray(bd, o, d, df, dr, 1)


def checkhop(bd, o, d, df, dr):
    return any(_ray(bd, o, d, a, b, 1) for a, b in symset(df, dr))


def checkatwostep(bd, o, d, f1, r1, f2, r2):
    mid = (o[0] + f1, o[1] + r1)
    if not ON(mid) or mid in bd:
        return False
    return d == (mid[0] + f2, mid[1] + r2)


# --------------------------------------------------------- the `def` clauses
_N_STEPS = [(0, 1, 1, 1), (0, 1, -1, 2), (1, 0, 1, 1), (1, 0, 2, -1),
            (1, -1, 2, -1), (1, -1, 1, -2), (0, -1, 1, -2), (0, -1, -1, -1),
            (-1, 0, -1, -1), (-1, 0, -2, 1), (-1, 1, -2, 1), (-1, 1, -1, 2)]
_E_STEPS = [(1, 1), (-1, -1), (2, -1), (-2, 1), (1, -2), (-1, 2)]
_F_LEAPS = [(1, 1), (-1, -1), (-1, 2), (1, -2), (-2, 1), (2, -1)]


def d_N(bd, o, d, side):                       # Horse
    return any(checkatwostep(bd, o, d, *s) for s in _N_STEPS)


def d_R(bd, o, d, side):                       # Chariot
    return (checkaride(bd, o, d, 1, -1) or checkaride(bd, o, d, -1, 1)
            or checkride(bd, o, d, 0, 1))


def d_C(bd, o, d, side):                       # Cannon
    if d in bd:                                # `not empty #1` -> a capture
        return (checkahop(bd, o, d, 1, -1) or checkahop(bd, o, d, -1, 1)
                or checkhop(bd, o, d, 0, 1))
    return d_R(bd, o, d, side)


def d_P(bd, o, d, side):                       # Soldier
    if side == 0:
        far = d[1] + (d[0] >> 1) >= 7
        gated = [(-2, 1), (2, -1), (-1, 1), (1, 0)]
        free = (0, 1)
    else:
        far = d[1] + ((d[0] + 1) >> 1) <= 7
        gated = [(-2, 1), (2, -1), (1, -1), (-1, 0)]
        free = (0, -1)
    if any(checkaleap(bd, o, d, a, b) for a, b in gated) and far:
        return True
    return checkaleap(bd, o, d, *free)


def d_E(bd, o, d, side):                       # Elephant
    if not any(checkatwostep(bd, o, d, a, b, a, b) for a, b in _E_STEPS):
        return False
    if side == 0:
        return d[1] + ((d[0] + 1) >> 1) <= 7
    return d[1] + (d[0] >> 1) >= 7


def d_F(bd, o, d, side):                       # Mandarin
    return (any(checkaleap(bd, o, d, a, b) for a, b in _F_LEAPS)
            and d in FLAGS)


def d_G(bd, o, d, side, literal=False):        # General
    gk = "G" if (literal or side == 1) else "g"   # see LITERAL note below
    foe = next((c for c, p in bd.items() if p == gk), None)
    fly = foe is not None and d == foe and checkride(bd, o, d, 1, 0)
    step = (checkaleap(bd, o, d, 1, -1) or checkaleap(bd, o, d, -1, 1)
            or checkleap(bd, o, d, 0, 1))
    return (fly or step) and d in FLAGS


DEFS = {"N": d_N, "R": d_R, "C": d_C, "P": d_P, "E": d_E, "F": d_F, "G": d_G}
UP = "NRCPEFG"


# ------------------------------------------------------------- GC move rules
def pseudo(bd, side, literal=False):
    out = []
    for o, p in bd.items():
        if (p.isupper() and side != 0) or (p.islower() and side != 1):
            continue
        fn = DEFS[p.upper()]
        for d in ALL:
            if d == o:
                continue
            q = bd.get(d)
            if q is not None and (q.isupper()) == (side == 0):
                continue                       # may not capture your own
            ok = (fn(bd, o, d, side, literal) if p.upper() == "G"
                  else fn(bd, o, d, side))
            if ok:
                out.append((o, d))
    return out


def in_check(bd, side, literal=False):
    gk = "G" if side == 0 else "g"
    g = next((c for c, p in bd.items() if p == gk), None)
    if g is None:
        return False
    return any(d == g for _o, d in pseudo(bd, 1 - side, literal))


def legal(bd, side, literal=False):
    out = []
    for o, d in pseudo(bd, side, literal):
        nb = dict(bd)
        nb[d] = nb.pop(o)
        if not in_check(nb, side, literal):
            out.append((o, d))
    return sorted(out)


# ----------------------------------------------------------------- transfer
def to_gc(state):
    bd = {}
    for (q, r), (o, t) in state.board.items():
        f, R = q + 4, 5 - q - r
        letter = {"S": "P", "H": "N", "C": "R", "A": "C",
                  "E": "E", "M": "F", "G": "G"}[t]
        bd[(f, R)] = letter if o == 0 else letter.lower()
    return bd


def to_plat(sq):
    f, R = sq
    return (f - 4, 9 - f - R)


def random_position(rng):
    """A scattered position: both Generals in their palaces (as the rules
    guarantee), Mandarins/Elephants on cells they could actually occupy, and
    everything else anywhere -- to exercise river/palace edges that a game
    from the opening may reach only rarely."""
    board = {}
    plat = {}
    reach = {0: set(), 1: set()}
    for seat in (0, 1):
        # cells an Elephant of `seat` can ever stand on
        for c in GM.CELLS:
            if GM._elephant_ok(seat, c):
                reach[seat].add(c)
    for seat in (0, 1):
        g = rng.choice(sorted(GM.PALACE[seat]))
        plat[g] = (seat, "G")
        for _ in range(rng.randrange(0, 3)):
            c = rng.choice(sorted(GM.PALACE[seat] - set(plat)))
            plat[c] = (seat, "M")
        for _ in range(rng.randrange(0, 3)):
            free = sorted(reach[seat] - set(plat))
            if free:
                plat[rng.choice(free)] = (seat, "E")
        for t in "SHCA":
            for _ in range(rng.randrange(0, 3)):
                free = sorted(set(GM.CELLS) - set(plat))
                c = rng.choice(free)
                # a Soldier never stands behind its own start line
                plat[c] = (seat, t)
    return plat


def main():
    n_games = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    n_rand = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    literal = "--literal-G" in sys.argv
    rng = random.Random(20260726)
    pos = mism = 0
    lit_diff = 0
    examples = []
    for i in range(n_rand):
        plat = random_position(rng)
        for side in (0, 1):
            st = GM.GState(board=dict(plat), to_move=side)
            st.hist = (GM._poskey(plat, side),)
            bd = to_gc(st)
            mine = sorted((tuple(map(int, a.split(","))),
                           tuple(map(int, b.split(","))))
                          for a, b in (m.split(">")
                                       for m in GAME.legal_moves(st)))
            theirs = sorted(set((to_plat(o), to_plat(d))
                                for o, d in legal(bd, side)))
            pos += 1
            if mine != theirs:
                mism += 1
                if len(examples) < 5:
                    examples.append((-1, i,
                                     [x for x in mine if x not in theirs][:6],
                                     [x for x in theirs if x not in mine][:6]))
            if literal:
                lt = sorted(set((to_plat(o), to_plat(d))
                                for o, d in legal(bd, side, True)))
                if lt != theirs:
                    lit_diff += 1
    for g in range(n_games):
        s = GAME.initial_state()
        while not GAME.is_terminal(s) and s.ply < 400:
            bd = to_gc(s)
            mine = sorted((tuple(map(int, a.split(","))),
                           tuple(map(int, b.split(","))))
                          for a, b in (m.split(">") for m in GAME.legal_moves(s)))
            theirs = sorted(set((to_plat(o), to_plat(d))
                                for o, d in legal(bd, s.to_move)))
            pos += 1
            if mine != theirs:
                mism += 1
                if len(examples) < 5:
                    only_m = [x for x in mine if x not in theirs]
                    only_t = [x for x in theirs if x not in mine]
                    examples.append((g, s.ply, only_m[:6], only_t[:6]))
            if literal:
                lt = sorted(set((to_plat(o), to_plat(d))
                                for o, d in legal(bd, s.to_move, True)))
                if lt != theirs:
                    lit_diff += 1
            mv = GAME.legal_moves(s)
            if not mv:
                break
            s = GAME.apply_move(s, rng.choice(mv))
    print(f"positions compared: {pos}   mismatches: {mism}")
    if literal:
        print(f"positions where the preset's LITERAL `def G` differs: {lit_diff}")
    for e in examples:
        print("  game %d ply %d  only-mine=%s  only-GC=%s" % e)
    return 0 if mism == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
