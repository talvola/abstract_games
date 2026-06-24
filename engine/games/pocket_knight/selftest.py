"""Pure-stdlib correctness anchor for Pocket Knight Chess.

Frozen, engine-derived facts (no external oracle needed):
  * The opening has 52 moves = 20 normal chess opening moves + 32 pocket-knight
    drops (one per empty square; at the start the 32 squares on ranks 3-6 are
    empty). DERIVED from the move generator and frozen here.
  * Each seat starts with exactly one pocket knight in hand ({"N": 1}).
  * A drop "N@c,r" places a knight on an empty square and EMPTIES that seat's
    hand (one-time only).
  * Captures do NOT bank into the reserve (unlike Crazyhouse): after capturing an
    enemy piece the capturer's hand is unchanged.
  * A seat can drop only once.
  * render() emits a reserve tray containing the pocket knight.
  * serialize/deserialize round-trips, including hands.

Run: PYTHONPATH=. python3 games/pocket_knight/selftest.py
"""

from __future__ import annotations

from agp.chesslike import CState, WHITE, BLACK
from games.pocket_knight.game import PocketKnight


def main() -> None:
    g = PocketKnight()
    s = g.initial_state()

    # --- opening move count (frozen, engine-derived) ---
    moves = g.legal_moves(s)
    drops = [m for m in moves if "@" in m]
    normal = [m for m in moves if "@" not in m]
    assert len(normal) == 20, f"opening normal moves {len(normal)} != 20"
    assert len(drops) == 32, f"opening drops {len(drops)} != 32 (empty squares)"
    assert len(moves) == 52, f"opening total {len(moves)} != 52"
    # every drop is a knight onto an empty square on a middle rank
    for m in drops:
        letter, cs = m.split("@")
        c, r = (int(x) for x in cs.split(","))
        assert letter == "N", f"non-knight drop {m}"
        assert 2 <= r <= 5, f"drop on non-empty rank: {m}"
        assert s.board.get((c, r)) is None, f"drop on occupied square: {m}"

    # --- each seat starts with exactly one pocket knight ---
    assert s.hands == {WHITE: {"N": 1}, BLACK: {"N": 1}}, f"start hands {s.hands}"

    # --- a drop places a knight and empties that seat's hand ---
    s2 = g.apply_move(s, "N@4,3")
    assert s2.board.get((4, 3)) == (WHITE, "N"), "knight not placed by drop"
    assert s2.hands.get(WHITE, {}).get("N", 0) == 0, "white hand not emptied by drop"
    assert s2.hands.get(BLACK, {}).get("N", 0) == 1, "black hand should still hold its knight"

    # --- a seat can drop only once (no more white drops after the drop) ---
    # play a black move, return to white, confirm white has no drop available.
    black_drops = [m for m in g.legal_moves(s2) if "@" in m]
    assert all(m.split("@")[0] == "N" for m in black_drops)  # only black's knight
    s3 = g.apply_move(s2, "N@3,4")            # black drops its pocket knight
    assert s3.hands.get(BLACK, {}).get("N", 0) == 0, "black hand not emptied"
    s4_moves = g.legal_moves(s3)
    assert not any("@" in m for m in s4_moves), "no drops should remain once both pockets are spent"

    # --- captures do NOT bank into the reserve (NOT Crazyhouse) ---
    # White pawn on d4 captures a black pawn on e5; hands must be unchanged.
    board = {
        (3, 3): (WHITE, "P"), (4, 4): (BLACK, "P"),
        (4, 0): (WHITE, "K"), (4, 7): (BLACK, "K"),
    }
    st = CState(board=board, to_move=WHITE, castling=frozenset(), ep=None,
                hands={WHITE: {"N": 1}, BLACK: {"N": 1}})
    assert "3,3>4,4" in g.legal_moves(st), "expected the pawn capture to be legal"
    st2 = g.apply_move(st, "3,3>4,4")
    assert st2.board.get((4, 4)) == (WHITE, "P"), "capture did not land"
    assert st2.hands == {WHITE: {"N": 1}, BLACK: {"N": 1}}, \
        f"capture banked into reserve (should not!): {st2.hands}"

    # --- render emits a reserve tray with the pocket knight ---
    r = g.render(s)
    assert "reserve" in r, "render missing reserve tray"
    assert r["reserve"]["0"].get("N") == 1, "white reserve tray missing pocket knight"
    assert r["reserve"]["1"].get("N") == 1, "black reserve tray missing pocket knight"

    # --- serialize round-trip (including hands) ---
    for state in (s, s2, s3):
        round_tripped = g.deserialize(g.serialize(state))
        assert round_tripped.hands == state.hands, "hands lost in serialize round-trip"
        assert round_tripped.board == state.board, "board lost in serialize round-trip"

    print("SELFTEST OK  (opening moves: 52 = 20 normal + 32 drops)")


if __name__ == "__main__":
    main()
