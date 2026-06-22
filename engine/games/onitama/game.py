"""Onitama (Shimpei Sato, 2014) -- an elegant 5x5 chess-like game driven by
**movement cards**.

Each player has five pawns and a master on their back row, and holds two of five
dealt cards. A turn is two steps: choose one of your cards, then move one piece by
one of that card's offsets (capturing what you land on). The used card is passed to
the middle and you take the middle card in its place. Win by capturing the enemy
master (Way of the Stone) or moving your master onto the enemy master's start
square (Way of the Stream).

The deal is random (``has_randomness``); after that the game is perfect
information. Turn model for the UI: ``"use:<Card>"`` selects a card (a card-strip
click), then ``"fc,fr>tc,tr"`` makes the move. Player 0 (red) is at the bottom.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from agp.game import Game

N = 5
# Each card: offsets (dc, dr) for player 0 (dr+ = forward, toward the opponent).
CARDS = {
    "Tiger": [(0, 2), (0, -1)],
    "Dragon": [(-2, 1), (2, 1), (-1, -1), (1, -1)],
    "Frog": [(-2, 0), (-1, 1), (1, -1)],
    "Rabbit": [(2, 0), (1, 1), (-1, -1)],
    "Crab": [(0, 1), (-2, 0), (2, 0)],
    "Elephant": [(-1, 0), (1, 0), (-1, 1), (1, 1)],
    "Goose": [(-1, 0), (-1, 1), (1, 0), (1, -1)],
    "Rooster": [(-1, 0), (-1, -1), (1, 0), (1, 1)],
    "Monkey": [(1, 1), (-1, 1), (1, -1), (-1, -1)],
    "Mantis": [(-1, 1), (1, 1), (0, -1)],
    "Horse": [(-1, 0), (0, 1), (0, -1)],
    "Ox": [(1, 0), (0, 1), (0, -1)],
    "Crane": [(0, 1), (-1, -1), (1, -1)],
    "Boar": [(-1, 0), (1, 0), (0, 1)],
    "Eel": [(-1, 1), (-1, -1), (1, 0)],
    "Cobra": [(1, 1), (1, -1), (-1, 0)],
}
TEMPLE = {0: (2, 0), 1: (2, 4)}        # each player's master start; reaching the foe's wins


def _cell(s):
    c, r = s.split(",")
    return int(c), int(r)


@dataclass
class OniState:
    board: dict = field(default_factory=dict)        # (c,r) -> (player, is_master)
    hands: dict = field(default_factory=dict)        # {0:[card,card], 1:[card,card]}
    middle: str = ""
    to_move: int = 0
    selected: object = None                          # chosen card name, or None
    winner: object = None


class Onitama(Game):
    uid = "onitama"
    name = "Onitama"

    @property
    def num_players(self):
        return 2

    def initial_state(self, options=None, rng=None):
        rng = rng or random.Random()
        deal = rng.sample(list(CARDS), 5)
        board = {}
        for c in range(N):
            board[(c, 0)] = (0, c == 2)
            board[(c, 4)] = (1, c == 2)
        return OniState(board=board, hands={0: deal[:2], 1: deal[2:4]}, middle=deal[4])

    def current_player(self, s):
        return s.to_move

    def _offsets(self, card, player):
        offs = CARDS[card]
        return offs if player == 0 else [(-dc, -dr) for (dc, dr) in offs]

    def legal_moves(self, s):
        if s.winner is not None:
            return []
        pl = s.to_move
        if s.selected is None:
            cards = [c for c in s.hands[pl] if self._card_has_move(s, c, pl)]
            # a player with no move at all must still pass a card to the middle
            return [f"use:{c}" for c in cards] or [f"pass:{c}" for c in s.hands[pl]]
        out = []
        for (c, r), (owner, _m) in s.board.items():
            if owner != pl:
                continue
            for dc, dr in self._offsets(s.selected, pl):
                to = (c + dc, r + dr)
                if 0 <= to[0] < N and 0 <= to[1] < N and (s.board.get(to) or (1 - pl,))[0] != pl:
                    out.append(f"{c},{r}>{to[0]},{to[1]}")
        return out + ["cancel"]

    def _card_has_move(self, s, card, pl):
        for (c, r), (owner, _m) in s.board.items():
            if owner != pl:
                continue
            for dc, dr in self._offsets(card, pl):
                to = (c + dc, r + dr)
                if 0 <= to[0] < N and 0 <= to[1] < N and (s.board.get(to) or (1 - pl,))[0] != pl:
                    return True
        return False

    def _rotate_card(self, s, card, pl):
        """Used `card` -> middle; old middle -> the player's hand."""
        hands = {0: list(s.hands[0]), 1: list(s.hands[1])}
        hands[pl] = [s.middle if c == card else c for c in hands[pl]]
        return hands, card

    def apply_move(self, s, move, rng=None):
        pl = s.to_move
        if move == "cancel":
            return OniState(board=dict(s.board), hands={0: list(s.hands[0]), 1: list(s.hands[1])},
                            middle=s.middle, to_move=pl, selected=None)
        if move.startswith("use:"):
            return OniState(board=dict(s.board), hands={0: list(s.hands[0]), 1: list(s.hands[1])},
                            middle=s.middle, to_move=pl, selected=move[4:])
        if move.startswith("pass:"):
            hands, mid = self._rotate_card(s, move[5:], pl)
            return OniState(board=dict(s.board), hands=hands, middle=mid,
                            to_move=1 - pl, selected=None)
        # a piece move using the selected card
        frm, to = (_cell(x) for x in move.split(">"))
        board = dict(s.board)
        mover = board.pop(frm)
        captured = board.get(to)
        board[to] = mover
        hands, mid = self._rotate_card(s, s.selected, pl)
        winner = None
        if captured is not None and captured[1]:
            winner = pl                                   # captured the enemy master
        elif mover[1] and to == TEMPLE[1 - pl]:
            winner = pl                                   # master reached the enemy temple
        return OniState(board=board, hands=hands, middle=mid, to_move=1 - pl,
                        selected=None, winner=winner)

    def is_terminal(self, s):
        return s.winner is not None

    def returns(self, s):
        if s.winner is None:
            return [0.0, 0.0]
        return [1.0 if i == s.winner else -1.0 for i in range(2)]

    def serialize(self, s):
        return {"board": {f"{c},{r}": list(v) for (c, r), v in s.board.items()},
                "hands": {str(p): list(s.hands[p]) for p in (0, 1)}, "middle": s.middle,
                "to_move": s.to_move, "selected": s.selected, "winner": s.winner}

    def deserialize(self, d):
        return OniState(board={_cell(k): tuple(v) for k, v in d["board"].items()},
                        hands={int(p): list(v) for p, v in d["hands"].items()},
                        middle=d["middle"], to_move=d["to_move"],
                        selected=d.get("selected"), winner=d.get("winner"))

    def describe_move(self, s, move):
        if move.startswith("use:"):
            return f"pick {move[4:]}"
        if move.startswith("pass:"):
            return f"pass {move[5:]} (no move)"
        if move == "cancel":
            return "deselect"
        frm, to = move.split(">")
        cap = "x" if _cell(to) in s.board else "-"
        return f"{s.selected} {frm}{cap}{to}"

    def render(self, s, perspective=None):
        pieces = [{"cell": f"{c},{r}", "owner": p, "label": "K" if m else "·"}
                  for (c, r), (p, m) in s.board.items()]
        # card strip: which hand each card is in, its offsets, and selectability
        cards = []
        for owner, names in ((0, s.hands[0]), (1, s.hands[1]), (None, [s.middle])):
            for name in names:
                cards.append({
                    "name": name, "offsets": CARDS[name], "owner": owner,
                    "selectable": owner == s.to_move and s.selected is None and s.winner is None,
                    "selected": name == s.selected,
                })
        if s.winner is not None:
            cap = f"Player {s.winner + 1} wins"
        elif s.selected:
            cap = f"Player {s.to_move + 1}: move with {s.selected}"
        else:
            cap = f"Player {s.to_move + 1} to move — pick a card"
        return {
            "board": {"type": "square", "width": N, "height": N, "cards": cards},
            "pieces": pieces,
            "highlights": [],
            "caption": cap,
        }
