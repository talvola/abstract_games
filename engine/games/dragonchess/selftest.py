"""Dragonchess correctness anchors (pure stdlib; runs under system python3).

  cd engine && PYTHONPATH=. python3 games/dragonchess/selftest.py

Anchors:
  (a) perft(1)=90 (hand-derived, justified piece-by-piece in rules.md) and the
      frozen perft(2)=8094 regression value.
  (b) the fast reverse-attack scan == the forward reference over random games.
  (c) exact destination sets for every piece type from a representative cell,
      including inter-level moves and the Dragon's capture-from-afar.
  (d) rule positions: Basilisk freeze/unfreeze, Sylph return-home, Warrior
      promotion, Dragon remote capture, checkmate, stalemate.
  (e) serialize round-trip, move-string uniqueness, random-playout termination.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from games.dragonchess.game import (          # noqa: E402
    Dragonchess, DragonState, _setup, _legal, _apply, _piece_moves, _frozen,
    _attacked, _attacked_slow, _in_check, _perft, _enemy, GOLD, SCARLET,
)

G = Dragonchess()
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("  FAIL:", msg)
    else:
        print("  ok  :", msg)


def dests(pieces, fpos):
    """Pseudo-move destinations (level,col,row) of the piece at fpos."""
    o, let = pieces[fpos]
    return {(tl, tc, tr)
            for (tl, tc, tr, promo, remote)
            in _piece_moves(pieces, _frozen(pieces), fpos, o, let)}


def st(pieces, to_move):
    s = DragonState(pieces=dict(pieces), to_move=to_move)
    s.seen = {}
    return s


# --------------------------------------------------------------- (a) perft ----
def test_perft():
    print("[perft]")
    p = _setup()
    check(len(p) == 84, "initial position has 84 pieces (42 per side)")
    check(_perft(p, GOLD, 1) == 90, "perft(1) == 90")
    check(_perft(p, GOLD, 2) == 8094, "perft(2) == 8094")


# ------------------------------------------------ (b) attack cross-check ------
def test_attack_crosscheck():
    print("[attack fast==slow]")
    rng = random.Random(11)
    p = _setup()
    player = GOLD
    mism = 0
    cells = [(l, c, r) for l in (1, 2, 3) for c in range(12) for r in range(8)]
    for _ in range(22):
        fr = _frozen(p)
        for by in (0, 1):
            for cell in cells:
                if _attacked(p, cell, by, fr) != _attacked_slow(p, cell, by, fr):
                    mism += 1
        L = _legal(p, player)
        if not L:
            break
        fpos, mv = rng.choice(L)
        p, _ = _apply(p, fpos, mv)
        player = _enemy(player)
    check(mism == 0, "reverse attack scan identical to forward oracle")


# --------------------------------------------------- (c) piece geometry -------
def test_pieces():
    print("[piece move geometry]")
    HOME = {(1, f, 1) for f in (0, 2, 4, 6, 8, 10)}

    # Sylph on sky (Gold): quiet diagonals fwd, capture ahead, capture down
    p = {(1, 3, 4): (GOLD, "S"), (1, 3, 5): (SCARLET, "O"),
         (2, 3, 4): (SCARLET, "O")}
    check(dests(p, (1, 3, 4)) == {(1, 2, 5), (1, 4, 5), (1, 3, 5), (2, 3, 4)},
          "Sylph sky: 2 quiet diagonals + capture-ahead + capture straight-down")

    # Sylph on ground (Gold): return up OR to any empty home cell
    p = {(2, 9, 3): (GOLD, "S")}
    check(dests(p, (2, 9, 3)) == {(1, 9, 3)} | HOME,
          "Sylph ground: return directly-up + 6 home cells")

    # Griffin on sky
    p = {(1, 3, 4): (GOLD, "G")}
    exp = {(1, 5, 7), (1, 1, 7), (1, 5, 1), (1, 1, 1), (1, 6, 6), (1, 0, 6),
           (1, 6, 2), (1, 0, 2), (2, 2, 3), (2, 4, 3), (2, 2, 5), (2, 4, 5)}
    check(dests(p, (1, 3, 4)) == exp, "Griffin sky: 8 (3,2)-leaps + 4 diag-below")

    # Griffin on ground
    p = {(2, 10, 1): (GOLD, "G")}
    exp = {(2, 9, 0), (2, 11, 0), (2, 9, 2), (2, 11, 2),
           (1, 9, 0), (1, 11, 0), (1, 9, 2), (1, 11, 2)}
    check(dests(p, (2, 10, 1)) == exp,
          "Griffin ground: 1 diagonal + return-to-sky diagonals")

    # Dragon on sky (empty): Bishop + King-orthogonal, never leaves the sky
    p = {(1, 5, 4): (GOLD, "R")}
    d = dests(p, (1, 5, 4))
    check(len(d) == 18 and all(l == 1 for (l, c, r) in d),
          "Dragon: 18 moves on an empty sky, none leave the top board")

    # Dragon capture-from-afar: the 5-cell cross directly below + orthogonals
    p = {(1, 5, 4): (GOLD, "R"),
         (2, 5, 4): (SCARLET, "W"), (2, 4, 4): (SCARLET, "W"),
         (2, 6, 4): (SCARLET, "W"), (2, 5, 5): (SCARLET, "W"),
         (2, 5, 3): (SCARLET, "W")}
    remote = {(tl, tc, tr) for (tl, tc, tr, pr, rem)
              in _piece_moves(p, _frozen(p), (1, 5, 4), GOLD, "R") if rem}
    check(remote == {(2, 5, 4), (2, 4, 4), (2, 6, 4), (2, 5, 5), (2, 5, 3)},
          "Dragon capture-from-afar targets the 5-cell cross below")
    np, cap = _apply(p, (1, 5, 4), (2, 4, 4, None, True))
    check(cap and np.get((1, 5, 4)) == (GOLD, "R") and (2, 4, 4) not in np,
          "capture-from-afar removes the enemy; the Dragon does NOT move")

    # Oliphant = Rook, Unicorn = Knight, Thief = Bishop, Mage = Queen (+/-)
    check(len(dests({(2, 5, 4): (GOLD, "O")}, (2, 5, 4))) == 18, "Oliphant=Rook (18)")
    check(len(dests({(2, 5, 4): (GOLD, "U")}, (2, 5, 4))) == 8, "Unicorn=Knight (8)")
    check(len(dests({(2, 5, 4): (GOLD, "T")}, (2, 5, 4))) == 14, "Thief=Bishop (14)")
    check(len(dests({(2, 5, 4): (GOLD, "M")}, (2, 5, 4))) == 34,
          "Mage ground = Queen(32) + up + down (34)")

    # Hero on ground: 1 & 2 diagonals + to-sky + to-underworld
    p = {(2, 2, 5): (GOLD, "H")}
    exp = {(2, 1, 4), (2, 3, 4), (2, 1, 6), (2, 3, 6),          # 1 diagonal
           (2, 0, 3), (2, 4, 3), (2, 0, 7), (2, 4, 7),          # 2 diagonal
           (1, 1, 4), (1, 3, 4), (1, 1, 6), (1, 3, 6),          # to sky
           (3, 1, 4), (3, 3, 4), (3, 1, 6), (3, 3, 6)}          # to underworld
    check(dests(p, (2, 2, 5)) == exp, "Hero ground: 16 destinations across levels")

    # Cleric: King on its level + directly up + directly down
    p = {(2, 4, 3): (GOLD, "C")}
    check(len(dests(p, (2, 4, 3))) == 10, "Cleric ground: King(8) + up + down (10)")

    # Mage on sky: 4 orthogonal + down-1 + down-2 (through empty ground)
    p = {(1, 1, 6): (GOLD, "M")}
    check(dests(p, (1, 1, 6)) == {(1, 0, 6), (1, 2, 6), (1, 1, 7), (1, 1, 5),
                                  (2, 1, 6), (3, 1, 6)},
          "Mage sky: 4 orthogonal + down-1 + down-2")

    # King: ground = 10; on the sky it can only drop back to the ground
    check(len(dests({(2, 4, 4): (GOLD, "K")}, (2, 4, 4))) == 10,
          "King ground: King(8) + up + down (10)")
    check(dests({(1, 4, 4): (GOLD, "K")}, (1, 4, 4)) == {(2, 4, 4)},
          "King on the sky is a sitting duck (only returns to the ground)")

    # Paladin: ground = King+Knight+board-to-board; sky = King+board-to-board
    check(len(dests({(2, 5, 2): (GOLD, "P")}, (2, 5, 2))) == 24,
          "Paladin ground: King(8)+Knight(8)+3D-knight(8) = 24")
    check(len(dests({(1, 2, 5): (GOLD, "P")}, (1, 2, 5))) == 16,
          "Paladin sky: King(8) + 3D-knight(8) = 16")

    # Warrior: quiet forward only; captures diagonally forward
    check(dests({(2, 5, 3): (GOLD, "W")}, (2, 5, 3)) == {(2, 5, 4)},
          "Warrior: 1 quiet forward on an empty board")
    p = {(2, 5, 3): (GOLD, "W"), (2, 4, 4): (SCARLET, "W"), (2, 6, 4): (SCARLET, "W")}
    check(dests(p, (2, 5, 3)) == {(2, 5, 4), (2, 4, 4), (2, 6, 4)},
          "Warrior: forward push + two diagonal captures")

    # Warrior promotion to Hero on the far rank
    p = {(2, 5, 6): (GOLD, "W")}
    mvs = list(_piece_moves(p, _frozen(p), (2, 5, 6), GOLD, "W"))
    check(mvs == [(2, 5, 7, "H", False)], "Warrior promotes to Hero on rank 8")
    np, _ = _apply(p, (2, 5, 6), (2, 5, 7, "H", False))
    check(np.get((2, 5, 7)) == (GOLD, "H"), "promotion yields a Hero")

    # Basilisk: forward move/capture (3) + straight back (quiet)
    check(dests({(3, 5, 3): (GOLD, "B")}, (3, 5, 3))
          == {(3, 5, 4), (3, 4, 4), (3, 6, 4), (3, 5, 2)},
          "Basilisk: 3 forward + 1 straight-back")

    # Elemental on the underworld: orthogonal-2 + diagonal-1 + to-ground
    p = {(3, 2, 3): (GOLD, "E")}
    exp = {(3, 2, 4), (3, 2, 5), (3, 2, 2), (3, 2, 1),          # ortho up/down
           (3, 1, 3), (3, 0, 3), (3, 3, 3), (3, 4, 3),          # ortho left/right
           (3, 1, 4), (3, 3, 4), (3, 1, 2), (3, 3, 2),          # 1 diagonal (quiet)
           (2, 1, 3), (2, 3, 3), (2, 2, 4), (2, 2, 2)}          # to the ground
    check(dests(p, (3, 2, 3)) == exp, "Elemental underworld: 16 destinations")
    check(dests({(2, 9, 3): (GOLD, "E")}, (2, 9, 3))
          == {(3, 8, 3), (3, 10, 3), (3, 9, 4), (3, 9, 2)},
          "Elemental ground: only returns to the underworld (4)")

    # Dwarf: forward/lateral quiet, diagonal-forward capture, up-capture
    check(dests({(3, 2, 2): (GOLD, "D")}, (3, 2, 2))
          == {(3, 2, 3), (3, 1, 2), (3, 3, 2)},
          "Dwarf underworld: forward + 2 lateral")
    p = {(3, 2, 2): (GOLD, "D"), (2, 2, 2): (SCARLET, "W")}
    check((2, 2, 2) in dests(p, (3, 2, 2)),
          "Dwarf: up-capture to the ground when an enemy is directly above")
    check(dests({(2, 9, 2): (GOLD, "D")}, (2, 9, 2))
          == {(2, 9, 3), (2, 8, 2), (2, 10, 2), (3, 9, 2)},
          "Dwarf ground: forward + 2 lateral + drop to the underworld")


# ------------------------------------------------------ (d) rule positions ----
def test_freeze():
    print("[Basilisk freeze]")
    # Gold Basilisk under a Scarlet Oliphant -> the Oliphant is frozen.
    p = {(3, 4, 3): (GOLD, "B"), (2, 4, 3): (SCARLET, "O"),
         (2, 6, 0): (SCARLET, "K"), (2, 6, 7): (GOLD, "K")}
    fr = _frozen(p)
    check((2, 4, 3) in fr, "enemy piece directly above a Basilisk is frozen")
    scar_moves = [m for (fp, m) in _legal(p, SCARLET) if fp == (2, 4, 3)]
    check(scar_moves == [], "a frozen piece generates no moves")

    # Same-owner piece above one's own Basilisk is NOT frozen.
    p2 = {(3, 4, 3): (GOLD, "B"), (2, 4, 3): (GOLD, "O")}
    check((2, 4, 3) not in _frozen(p2),
          "a Basilisk only freezes OPPOSING pieces")

    # Move the Basilisk away -> the Oliphant thaws.
    p3 = dict(p)
    del p3[(3, 4, 3)]
    p3[(3, 4, 2)] = (GOLD, "B")
    thawed = [m for (fp, m) in _legal(p3, SCARLET) if fp == (2, 4, 3)]
    check(len(thawed) > 0, "freezing is temporary: the piece thaws when unblocked")


def test_mate_and_stalemate():
    print("[checkmate / stalemate]")
    # Checkmate delivered by a Gold Cleric dropping onto the sky above the
    # cornered Scarlet King; every escape square is covered.
    base = {
        (2, 0, 0): (SCARLET, "K"),      # cornered king
        (2, 1, 7): (GOLD, "O"),         # covers file b: (2,1,0) & (2,1,1)
        (2, 1, 3): (GOLD, "U"),         # knight covers (2,0,1)
        (3, 1, 0): (GOLD, "C"),         # covers (3,0,0) & (2,1,0)
        (1, 1, 1): (GOLD, "C"),         # defends the checking square (1,0,0)
        (2, 6, 4): (GOLD, "K"),         # Gold king, safe
    }
    p = dict(base)
    p[(1, 1, 0)] = (GOLD, "C")          # the future checker
    s = st(p, GOLD)
    check(not _in_check(p, SCARLET), "pre-mate: Scarlet is not yet in check")
    ns = G.apply_move(s, "1,1,0>1,0,0")
    check(G.is_terminal(ns) and ns.winner == GOLD, "Cleric drop is checkmate (Gold wins)")
    check(G.returns(ns) == [1.0, -1.0], "returns reflect the Gold win")

    # Stalemate: Gold's final quiet move cages the Scarlet King with no check.
    # (1,1,1) stays -- it covers the (1,0,0) up-escape.
    p = dict(base)
    p[(3, 2, 0)] = (GOLD, "C")          # will slide to (3,1,0)
    del p[(3, 1, 0)]                    # (3,0,0) currently open -> king can flee
    s = st(p, GOLD)
    pre = [m for (fp, m) in _legal(p, SCARLET)]
    check(len(pre) > 0, "pre-stalemate: Scarlet still has the (3,0,0) escape")
    ns = G.apply_move(s, "3,2,0>3,1,0")
    check(G.is_terminal(ns) and ns.draw and ns.winner is None,
          "sealing the last escape with no check is stalemate = DRAW")
    check(G.returns(ns) == [0.0, 0.0], "stalemate returns [0,0]")


# ------------------------------------------------- (e) invariants / play ------
def test_invariants():
    print("[invariants]")
    s = G.initial_state()
    snap = G.serialize(s)
    import json
    json.dumps(snap)
    again = G.serialize(G.deserialize(snap))
    check(again == snap, "serialize round-trips on the initial state")

    moves = G.legal_moves(s)
    check(len(moves) == len(set(moves)), "opening move strings are unique")
    check(len(moves) == 90, "legal_moves lists all 90 opening moves")

    rng = random.Random(3)
    for gi in range(2):
        s = G.initial_state()
        steps = 0
        while not G.is_terminal(s):
            s = G.apply_move(s, rng.choice(G.legal_moves(s)))
            steps += 1
        check(True, f"random game {gi} terminated after {steps} plies "
                    f"(returns {G.returns(s)})")


def main():
    test_perft()
    test_attack_crosscheck()
    test_pieces()
    test_freeze()
    test_mate_and_stalemate()
    test_invariants()
    print()
    if FAILS:
        print(f"SELFTEST FAILED ({len(FAILS)} failures)")
        sys.exit(1)
    print("all dragonchess selftests passed")


if __name__ == "__main__":
    main()
