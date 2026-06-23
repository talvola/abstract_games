"""Shisima correctness anchor (pure stdlib -- imports only agp + this game).

There is no published perft for Shisima, so the anchor is the baked ruleset:

* TOPOLOGY: 8 octagon rim points + 1 CENTRE ('the water') = 9 points; the marked
  lines are the octagon rim (each rim point to its two ring-neighbours) and four
  diameters joining each rim point through the centre to the opposite rim point.
* ADJACENCY: each rim point <-> its two ring-neighbours and the centre; the
  centre <-> all 8 rim points; a rim point is NEVER adjacent to its opposite.
* PIECES / START: each player has exactly 3 pieces; player 0 on rim 0,1,2 and
  player 1 on rim 4,5,6, with rim 3, rim 7 and the centre empty.
* MOVEMENT: slide one piece along a line to an adjacent EMPTY point; no captures
  (opponent pieces are never removed); no placement phase.
* WIN: three pieces in a straight line THROUGH THE CENTRE, i.e. {rim i, centre,
  rim i+4}; that is the ONLY kind of three-in-a-row on this board.
* plus hand-built winning lines, a reached-by-sliding win, no-capture and draw
  checks, and a serialize round-trip.

Prints "SELFTEST OK" and exits 0 on success, nonzero on failure.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.shisima.game import (  # noqa: E402
    Shisima, SState, POINTS, RIM, CENTRE, ADJ, WIN_LINES, MEN,
)

G = Shisima()


def main():
    # --- topology: 8 rim + 1 centre = 9 points ---------------------------
    assert len(POINTS) == 9, len(POINTS)
    assert len(RIM) == 8, len(RIM)
    assert CENTRE not in RIM and CENTRE in POINTS
    assert MEN == 3

    # --- adjacency along the marked lines --------------------------------
    # centre is adjacent to ALL 8 rim points
    assert ADJ[CENTRE] == frozenset(RIM), ADJ[CENTRE]
    # each rim point: its two ring-neighbours + the centre (exactly 3)
    for i in range(8):
        a = str(i)
        exp = {str((i + 1) % 8), str((i - 1) % 8), CENTRE}
        assert ADJ[a] == frozenset(exp), (a, ADJ[a])
        assert len(ADJ[a]) == 3
    # a rim point is NEVER adjacent to its diametrically opposite rim point
    for i in range(8):
        opp = str((i + 4) % 8)
        assert opp not in ADJ[str(i)], f"{i} wrongly adjacent to opposite {opp}"
    # adjacency is symmetric
    for p in POINTS:
        for q in ADJ[p]:
            assert p in ADJ[q], f"asymmetric {p},{q}"

    # --- winning lines: exactly the 4 diameters through the centre --------
    assert len(WIN_LINES) == 4, len(WIN_LINES)
    expected = {frozenset({str(i), CENTRE, str(i + 4)}) for i in range(4)}
    assert {frozenset(ln) for ln in WIN_LINES} == expected, WIN_LINES
    # every winning line passes through the centre
    for ln in WIN_LINES:
        assert CENTRE in ln, f"win line {ln} does not pass through centre"
        assert len(ln) == 3

    # --- starting position: 3 pieces each, on the documented points ------
    st = G.initial_state()
    assert sum(1 for v in st.pos.values() if v == 0) == 3
    assert sum(1 for v in st.pos.values() if v == 1) == 3
    assert {p for p, v in st.pos.items() if v == 0} == {"0", "1", "2"}
    assert {p for p, v in st.pos.items() if v == 1} == {"4", "5", "6"}
    # rim 3, rim 7 and the centre start empty
    for empty in ("3", "7", CENTRE):
        assert empty not in st.pos, f"{empty} should start empty"
    assert st.to_move == 0 and st.winner is None
    assert not G.is_terminal(st)

    # --- legal moves are slides to an adjacent EMPTY point ---------------
    mv = G.legal_moves(st)
    assert mv and all(">" in m for m in mv), "moves should be slides"
    for m in mv:
        src, dst = m.split(">")
        assert st.pos.get(src) == st.to_move, "must move own piece"
        assert dst not in st.pos, "must move to empty point"
        assert dst in ADJ[src], f"slide {m} not along adjacency"
    # from the start: empty points are 3, 7, c.  Player 0 holds 0,1,2.
    # piece 0 can go to 7 (ring) and centre; piece 2 can go to 3 and centre;
    # piece 1 (rim 1) only neighbours 0,2 (occupied) and centre.
    legal = set(mv)
    assert "0>7" in legal and "0>c" in legal
    assert "2>3" in legal and "2>c" in legal
    assert "1>c" in legal
    # cannot move onto an occupied point
    assert "0>1" not in legal and "1>0" not in legal

    # --- a hand-built three-in-a-row through the centre is a win ----------
    for ln in WIN_LINES:
        pos = {q: 0 for q in ln}
        assert G._is_line(pos, 0), f"line {ln} not detected as a win"
        pos2 = {q: 1 for q in ln}
        assert G._is_line(pos2, 1), f"line {ln} not detected for player 1"
        # mixed ownership is NOT a win
        mixed = dict(pos)
        mixed[next(iter(ln))] = 1
        assert not G._is_line(mixed, 0) and not G._is_line(mixed, 1), \
            f"mixed line {ln} wrongly a win"

    # a rim-only set (no centre) can never be a win (not collinear here)
    rim_only = {"0": 0, "1": 0, "2": 0}
    assert not G._is_line(rim_only, 0), "rim-only triple wrongly a win"

    # --- win reached by SLIDING -----------------------------------------
    # P0 holds rim 0 and rim 4 (a diameter's ends) plus rim 1; centre empty.
    # P0 slides rim 1 -> centre to complete the {0, c, 4} diameter.
    s = SState(pos={"0": 0, "4": 0, "1": 0, "5": 1, "6": 1, "7": 1},
               to_move=0, ply=10)
    assert "1>c" in G.legal_moves(s), G.legal_moves(s)
    s2 = G.apply_move(s, "1>c")
    assert s2.winner == 0, f"winner={s2.winner}"
    assert G.is_terminal(s2) and G.returns(s2) == [1.0, -1.0]
    assert G.legal_moves(s2) == [], "no moves once terminal"

    # --- no capture: opponent pieces are never removed -------------------
    s = G.initial_state()
    before1 = sum(1 for v in s.pos.values() if v == 1)
    for m in G.legal_moves(s):
        after1 = sum(1 for v in G.apply_move(s, m).pos.values() if v == 1)
        assert after1 == before1, "opponent piece removed -- captures not allowed"
        # piece count is conserved overall (slide, not place/remove)
        assert len(G.apply_move(s, m).pos) == len(s.pos)

    # --- draw cap guarantees termination --------------------------------
    s = SState(pos={"0": 0, "1": 0, "2": 0, "4": 1, "5": 1, "6": 1},
               to_move=0, ply=G.PLY_CAP)
    assert G.is_terminal(s) and G.returns(s) == [0.0, 0.0], "draw cap not enforced"
    assert G.legal_moves(s) == [], "terminal state must offer no moves"

    # --- serialize round-trips ------------------------------------------
    s = G.apply_move(G.initial_state(), "0>c")
    assert G.serialize(G.deserialize(G.serialize(s))) == G.serialize(s)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
