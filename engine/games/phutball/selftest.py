"""Phutball selftest — pure stdlib, fast. Run: PYTHONPATH=. python3 games/phutball/selftest.py

Anchors (baked rule asserts):
  (1) a turn is EITHER place ONE man on any empty point OR a ball-jump sequence
      (never both): on a FRESH turn the legal moves are placements (single empty
      cell ids) plus any single ball hops; once the ball has hopped, placements
      are gone and only further hops or "stop" remain — the ball-mover keeps the
      turn until they choose to stop.
  (2) a ball JUMP: from the ball, in one of 8 directions, over an unbroken line
      of >=1 men to the first empty point beyond, removing ALL jumped men; jumps
      CHAIN (after a hop the same player hops again, any direction) and the mover
      chooses when to stop; a jump over a gap or off a non-goal edge is illegal.
  (3) WIN: the ball reaching/crossing the mover's goal line.
Plus hand-built positions: single jump (men removed, ball moved), a 2-jump chain
in different directions (played as two apply_move hops), and a goal-line win
reached via apply_move.
"""
from __future__ import annotations
import sys
from games.phutball.game import Phutball, PhutballState


def check(cond, msg):
    if not cond:
        print("SELFTEST FAIL:", msg)
        sys.exit(1)


G = Phutball()


# --- basic shape -----------------------------------------------------------
s0 = G.initial_state()
check(s0.width == 15 and s0.height == 19, "default board 15x19")
check(s0.ball == (7, 9), "ball starts on centre point")
check(len(s0.men) == 0, "no men initially")
check(G.num_players == 2, "2 players")
check(not G.is_terminal(s0), "initial state not terminal")

# round-trip serialize
s_rt = G.deserialize(G.serialize(s0))
check(G.serialize(s_rt) == G.serialize(s0), "serialize round-trips")

# --- (1) place-or-jump, never both ----------------------------------------
# Empty board: every legal move is a placement (no men to jump over), no "stop".
lm = G.legal_moves(s0)
check("stop" not in lm, "no 'stop' on a fresh turn")
check(len(lm) == s0.width * s0.height - 1, "placements = all empty points except ball")
check("7,9" not in lm, "cannot place a man on the ball's point")
# a placement adds exactly one neutral man and passes the turn
s1 = G.apply_move(s0, "7,8")
check(len(s1.men) == 1 and (7, 8) in s1.men, "placement adds one man")
check(s1.ball == s0.ball, "placement does not move the ball")
check(s1.to_move == 1, "placement passes the turn")
check(not s1.chaining, "placement does not start a chain")

# --- (2) single jump: men removed, ball moves -----------------------------
# Ball at (7,9); a single man directly below at (7,10); empty at (7,11).
sj = PhutballState(width=15, height=19, men=frozenset({(7, 10)}), ball=(7, 9), to_move=0)
check("7,11" in G.legal_moves(sj), "single jump landing 7,11 is legal")
sj2 = G.apply_move(sj, "7,11")
check(sj2.ball == (7, 11), "ball moved to 7,11 after jump")
check((7, 10) not in sj2.men, "jumped man removed")
check(len(sj2.men) == 0, "all jumped men removed (single)")
# After a hop with no further men to jump, the only continuation is 'stop'.
check(G.legal_moves(sj2) == ["stop"], "after a lone hop, only 'stop' remains")
sj3 = G.apply_move(sj2, "stop")
check(sj3.to_move == 1 and not sj3.chaining, "'stop' ends the ball turn and passes")

# jump over multiple men in a line removes all of them
sline = PhutballState(width=15, height=19, men=frozenset({(7, 10), (7, 11), (7, 12)}), ball=(7, 9), to_move=0)
check("7,13" in G.legal_moves(sline), "jump over 3 men lands at 7,13")
sline2 = G.apply_move(sline, "7,13")
check(sline2.ball == (7, 13) and len(sline2.men) == 0, "all 3 men removed")

# jump over a GAP is illegal: man at (7,10), gap at (7,11), man at (7,12).
# A single hop lands on the FIRST empty point 7,11 only; it can never reach 7,13
# in one hop (that would require skipping the empty 7,11).
sgap = PhutballState(width=15, height=19, men=frozenset({(7, 10), (7, 12)}), ball=(7, 9), to_move=0)
hops = {land for land, _ in G._single_jumps(sgap)}
check((7, 11) in hops, "hop lands on first empty point 7,11")
check((7, 13) not in hops, "single hop cannot skip the gap at 7,11 to reach 7,13")

# jump off a non-goal edge is illegal. Ball near left edge, man to the left,
# empty beyond is off-board (column -1) and NOT a goal -> no such hop.
sedge = PhutballState(width=15, height=19, men=frozenset({(0, 9)}), ball=(1, 9), to_move=0)
ehops = {land for land, _ in G._single_jumps(sedge)}
check(all(0 <= c < 15 and 0 <= r < 19 for (c, r) in ehops),
      "no ball hop off a side (non-goal) edge")
check(len(ehops) == 0, "no legal ball hop exists off a side edge here")

# --- (2b) chain in DIFFERENT directions; mover chooses when to stop --------
# Ball (7,9). Man below (7,10) -> hop to (7,11). Then man to the right (8,11) ->
# hop to (9,11). Two hops in different directions, same player.
sc = PhutballState(width=15, height=19, men=frozenset({(7, 10), (8, 11)}), ball=(7, 9), to_move=0)
check("7,11" in G.legal_moves(sc), "first hop 7,11 legal")
a = G.apply_move(sc, "7,11")
check(a.to_move == 0 and a.chaining, "ball-mover keeps the turn mid-chain")
lm_mid = G.legal_moves(a)
check("stop" in lm_mid, "mover may stop after the first hop")
check("9,11" in lm_mid, "second hop (rightward) available, different direction")
# stopping early leaves the second man on the board
a_stop = G.apply_move(a, "stop")
check(a_stop.ball == (7, 11) and (8, 11) in a_stop.men and (7, 10) not in a_stop.men,
      "stopping after hop 1 removes only the first man")
check(a_stop.to_move == 1, "stop passes the turn")
# full chain removes both men and lands at 9,11
b = G.apply_move(a, "9,11")
check(b.ball == (9, 11) and len(b.men) == 0, "full chain removes both men")

# --- (3) WIN: ball reaching / crossing the mover's goal line ---------------
# Player 0 attacks the BOTTOM (row height-1 = 18). Ball (7,16), man (7,17),
# empty (7,18) which IS the goal row -> landing on it wins.
sw = PhutballState(width=15, height=19, men=frozenset({(7, 17)}), ball=(7, 16), to_move=0)
check("7,18" in G.legal_moves(sw), "jump onto bottom goal row is legal")
sw2 = G.apply_move(sw, "7,18")
check(sw2.winner == 0, "player 0 wins landing ON the bottom goal row")
check(G.is_terminal(sw2), "winning state is terminal")
check(G.legal_moves(sw2) == [], "terminal state has no legal moves")
check(G.returns(sw2) == [1.0, -1.0], "returns reflect player 0 win")

# Win by jumping OVER the edge: ball (7,16), men (7,17),(7,18); beyond is row 19
# (off the bottom edge) -> crosses goal -> win for player 0.
swo = PhutballState(width=15, height=19, men=frozenset({(7, 17), (7, 18)}), ball=(7, 16), to_move=0)
check("7,19" in G.legal_moves(swo), "jump landing one row past the bottom edge wins")
swo2 = G.apply_move(swo, "7,19")
check(swo2.winner == 0 and swo2.ball == (7, 19), "win by jumping OVER the goal line")

# Player 1 attacks the TOP (row 0). Ball (7,2), man (7,1), empty (7,0)=goal.
sw1 = PhutballState(width=15, height=19, men=frozenset({(7, 1)}), ball=(7, 2), to_move=1)
check("7,0" in G.legal_moves(sw1), "jump onto top goal row legal for player 1")
sw1b = G.apply_move(sw1, "7,0")
check(sw1b.winner == 1, "player 1 wins landing on top goal row")
check(G.returns(sw1b) == [-1.0, 1.0], "returns reflect player 1 win")

# A jump that crosses the OPPONENT's edge is NOT a win and NOT legal for this
# mover: player 1 (attacks top) cannot jump off the bottom edge.
sx = PhutballState(width=15, height=19, men=frozenset({(7, 17), (7, 18)}), ball=(7, 16), to_move=1)
check("7,19" not in G.legal_moves(sx), "player 1 may not jump off the bottom (opponent) edge")

# --- a short played sequence stays consistent ------------------------------
s = G.initial_state()
s = G.apply_move(s, "7,8")   # place
s = G.apply_move(s, "0,0")   # place (other player)
check(not G.is_terminal(s), "game continues after two placements")
check(s.plies == 2, "ply counter advances")

# --- ply cap is a real terminal (draw) ------------------------------------
from games.phutball.game import PLY_CAP
scap = PhutballState(width=15, height=19, men=frozenset(), ball=(7, 9),
                     to_move=0, plies=PLY_CAP)
check(G.is_terminal(scap), "ply-cap state is terminal")
check(G.returns(scap) == [0.0, 0.0], "ply-cap is a draw")

print("SELFTEST OK")
sys.exit(0)
