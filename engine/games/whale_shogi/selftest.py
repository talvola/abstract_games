"""Whale Shogi (Kujira Shogi) correctness anchor (pure stdlib).

Whale Shogi has no published perft, so we hand-verify the setup and the distinctive
piece geometries against the rules (R. W. Schmittberger, 1981; Wikipedia "Whale
Shogi"), pin the opening legal-move count, and freeze this engine's self-computed
perft 1/2/3.

Opening = 7 moves for Black: the Narwhal's forward jump over its own dolphin
((4,0)>(4,2)) plus one forward step for each of the six dolphins. Every back-rank
piece is blocked by its own men at the start.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from games.whale_shogi.game import WhaleShogi        # noqa: E402
from agp.shogilike import SState, BLACK, WHITE        # noqa: E402

G = WhaleShogi()


def perft(s, d):
    if d == 0:
        return 1
    if G.is_terminal(s):
        return 0
    return sum(perft(G.apply_move(s, m), d - 1) for m in G.legal_moves(s))


def targets(board, sq, pl, letter):
    return sorted(G._piece_targets(board, sq, pl, letter))


def main():
    s0 = G.initial_state()
    b = s0.board

    # --- setup: 12 pieces a side, whale back rank H G W P N B, dolphins in front ---
    assert "".join(b[(c, 0)][1] for c in range(6)) == "HGWPNB"
    assert "".join(b[(c, 5)][1] for c in range(6)) == "BNPWGH"      # White, 180deg rotated
    assert all(b[(c, 1)] == (BLACK, "D") for c in range(6))
    assert all(b[(c, 4)] == (WHITE, "D") for c in range(6))
    assert b[(2, 0)] == (BLACK, "W") and b[(3, 5)] == (WHITE, "W")  # white whales (royal), offset
    assert sum(1 for v in b.values() if v[0] == BLACK) == 12
    assert sum(1 for v in b.values() if v[0] == WHITE) == 12

    # --- opening move count + perft (self-computed; no published reference) ---
    lm = G.legal_moves(s0)
    assert len(lm) == 7, len(lm)
    assert "4,0>4,2" in lm, "Narwhal must jump two squares forward over its own dolphin"
    assert not any("@" in m for m in lm)      # nothing in hand at the start -> no drops yet
    for d, want in {1: 7, 2: 49, 3: 398}.items():
        got = perft(s0, d)
        assert got == want, f"perft d{d}: {got} != {want}"

    # --- distinctive piece geometry (Black frame, from an open square) ---
    kings = {(0, 0): (BLACK, "W"), (5, 5): (WHITE, "W")}
    # Killer Whale = Dragon King: rook slides + one diagonal step (NOT two).
    kb = dict(kings); kb[(2, 2)] = (BLACK, "K")
    kt = targets(kb, (2, 2), BLACK, "K")
    assert (2, 5) in kt and (5, 2) in kt and (2, 0) in kt          # slides to the edges
    assert (3, 3) in kt and (1, 1) in kt                          # single diagonal step
    assert (4, 4) not in kt                                       # ...but only one step
    # Grey Whale: slide straight forward or diagonally backward (nothing else).
    assert targets({(2, 2): (BLACK, "G")}, (2, 2), BLACK, "G") == \
        [(0, 0), (1, 1), (2, 3), (2, 4), (2, 5), (3, 1), (4, 0)]
    # Narwhal: jump 2 forward, plus one step back / sideways (jumps over pieces).
    assert targets({(2, 2): (BLACK, "N")}, (2, 2), BLACK, "N") == \
        [(1, 2), (2, 1), (2, 4), (3, 2)]
    # Humpback: four diagonal steps + one step straight back.
    assert targets({(2, 2): (BLACK, "H")}, (2, 2), BLACK, "H") == \
        [(1, 1), (1, 3), (2, 1), (3, 1), (3, 3)]
    # Blue Whale: one step fwd/back + one diagonally forward.
    assert targets({(2, 2): (BLACK, "B")}, (2, 2), BLACK, "B") == \
        [(1, 3), (2, 1), (2, 3), (3, 3)]
    # Porpoise: one square sideways only.
    assert targets({(2, 2): (BLACK, "P")}, (2, 2), BLACK, "P") == [(1, 2), (3, 2)]
    # White Whale: king (all eight).
    assert len(targets({(2, 2): (BLACK, "W")}, (2, 2), BLACK, "W")) == 8

    # --- Dolphin conditional move: diagonal-backward slide ONLY on the far rank ---
    assert targets({(2, 2): (BLACK, "D")}, (2, 2), BLACK, "D") == [(2, 3)]   # normal: 1 fwd
    assert targets({(2, 5): (BLACK, "D")}, (2, 5), BLACK, "D") == \
        [(0, 3), (1, 4), (3, 4), (4, 3), (5, 2)]                            # far rank: slides back

    # --- promotion happens ONLY on capture: porpoise -> killer whale in hand ---
    st = SState(board={(0, 0): (BLACK, "W"), (5, 5): (WHITE, "W"),
                       (2, 2): (BLACK, "P"), (2, 3): (WHITE, "B")},
                hands={BLACK: {}, WHITE: {}}, to_move=WHITE)
    st2 = G.apply_move(st, "2,3>2,2")                 # White's blue whale captures the porpoise
    assert st2.hands[WHITE] == {"K": 1}, st2.hands    # banked as a KILLER WHALE, not a porpoise
    assert st2.board[(2, 2)] == (WHITE, "B")
    # no move ever carries a promotion suffix (there is no promotion zone)
    assert not any(m.endswith("=+") for m in G.legal_moves(s0))

    # --- Whale Shogi HAS drops; a killer whale drops freely (even on the last rank) ---
    st3 = G.apply_move(st2, "0,0>0,1")                # Black steps its whale
    kdrops = [m for m in G.legal_moves(st3) if m.startswith("K@")]
    assert kdrops, "killer whale in hand must be droppable"
    assert "K@5,5" not in kdrops                      # occupied (White whale) -> not a target
    assert "K@0,0" in kdrops and "K@2,0" in kdrops    # no rank restriction for non-dolphins

    # --- Dolphin drop restrictions (last rank + at most two per file) ---
    st = SState(board={(0, 0): (BLACK, "W"), (5, 5): (WHITE, "W"),
                       (3, 1): (BLACK, "D"), (3, 2): (BLACK, "D")},
                hands={BLACK: {"D": 1}, WHITE: {}}, to_move=BLACK)
    ddrops = [m for m in G.legal_moves(st) if m.startswith("D@")]
    assert not any(m == f"D@{c},5" for c in range(6) for m in ddrops), "no dolphin on the far rank"
    assert not any(m.startswith("D@3,") for m in ddrops), "file already holds two dolphins"
    assert "D@2,2" in ddrops                          # a different, legal file is fine

    # --- serialize round-trips ---
    assert G.serialize(G.deserialize(G.serialize(s0))) == G.serialize(s0)
    assert G.serialize(G.deserialize(G.serialize(st2))) == G.serialize(st2)

    print("SELFTEST OK")


if __name__ == "__main__":
    main()
