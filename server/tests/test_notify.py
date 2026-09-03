"""End-to-end notification tests through the real routes (TestClient + a throw-
away SQLite DB). Emails are captured by monkeypatching notify.send_email; the
sync flag makes delivery inline so assertions see them immediately.

Run:  .venv/bin/python -m unittest server.tests.test_notify -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

_TMP = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["AGP_EMAIL_SYNC"] = "1"
os.environ["AGP_BASE_URL"] = "https://example.test"
os.environ.pop("AGP_SMTP_HOST", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from server import app as appmod, db as dbmod, events, games as G, notify  # noqa: E402
from server.models import Match, Notification  # noqa: E402

SENT: list[tuple[str, str, str]] = []


def _capture(to, subject, body):
    SENT.append((to, subject, body))


class NotifyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbmod.init_db()
        notify.send_email = _capture
        cls.game = "tic_tac_toe"

    def setUp(self):
        SENT.clear()
        self.a = TestClient(appmod.app)
        self.b = TestClient(appmod.app)
        n = datetime.utcnow().strftime("%H%M%S%f")
        self.a_email, self.b_email = f"a{n}@x.test", f"b{n}@x.test"
        r = self.a.post("/api/auth/register", json={"email": self.a_email, "display_name": "Alice", "password": "secret1"})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.b.post("/api/auth/register", json={"email": self.b_email, "display_name": "Bob", "password": "secret1"})
        self.assertEqual(r.status_code, 200, r.text)

    # -- helpers -----------------------------------------------------------
    def _pair(self, seat_pref="first"):
        """Alice posts a seek (seat_pref = who Alice plays), Bob accepts."""
        r = self.a.post("/api/seeks", json={"game_uid": self.game, "options": {}, "seat_pref": seat_pref})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.b.post(f"/api/seeks/{r.json()['id']}/accept")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["match_id"]

    def _mover(self, mid):
        for c in (self.a, self.b):
            v = c.get(f"/api/matches/{mid}").json()
            if v["my_turn"]:
                return c, v
        self.fail("nobody to move")

    def _sent_to(self, email):
        return [s for s in SENT if s[0] == email]

    # -- tests -------------------------------------------------------------
    def test_pairing_emails_the_creator_only_and_says_whose_move(self):
        self._pair("first")  # Alice moves first
        self.assertEqual(len(SENT), 1)
        to, subject, body = SENT[0]
        self.assertEqual(to, self.a_email)
        self.assertIn("Bob accepted", subject)
        self.assertIn("It's your move first", body)
        self.assertIn("https://example.test/?match=", body)

        SENT.clear()
        self._pair("second")  # Bob moves first
        self.assertEqual([s[0] for s in SENT], [self.a_email])
        self.assertIn("Bob moves first", SENT[0][2])

    def test_quickpair_emails_the_waiting_player(self):
        r = self.a.post("/api/quickpair", json={"game_uid": self.game, "options": {}})
        self.assertFalse(r.json()["paired"])
        self.assertEqual(SENT, [])
        r = self.b.post("/api/quickpair", json={"game_uid": self.game, "options": {}})
        self.assertTrue(r.json()["paired"])
        self.assertEqual([s[0] for s in SENT], [self.a_email])

    def test_move_emails_the_other_player_once_per_turn(self):
        mid = self._pair("first")
        SENT.clear()
        c, v = self._mover(mid)
        self.assertIs(c, self.a)
        r = c.post(f"/api/matches/{mid}/move", json={"move": v["legal_moves"][0]})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([s[0] for s in SENT], [self.b_email])
        self.assertTrue(SENT[0][1].startswith("Your turn"))
        # The mover never emails themself; Bob's reply emails Alice.
        SENT.clear()
        c, v = self._mover(mid)
        self.assertIs(c, self.b)
        c.post(f"/api/matches/{mid}/move", json={"move": v["legal_moves"][0]})
        self.assertEqual([s[0] for s in SENT], [self.a_email])

    def test_final_move_sends_result_not_your_turn(self):
        mid = self._pair("first")
        # Play X to a win: X at 0,0 1,0 2,0 ; O elsewhere.
        seq = ["0,0", "0,1", "1,0", "1,1", "2,0"]
        for mv in seq:
            c, v = self._mover(mid)
            self.assertIn(mv, v["legal_moves"])
            c.post(f"/api/matches/{mid}/move", json={"move": mv})
        v = self.a.get(f"/api/matches/{mid}").json()
        self.assertTrue(v["terminal"])
        last = SENT[-1]
        self.assertEqual(last[0], self.b_email)
        self.assertTrue(last[1].startswith("You lost"), last[1])
        self.assertNotIn("Your turn", last[1])

    def test_resign_emails_the_opponent_as_winner(self):
        mid = self._pair("first")
        SENT.clear()
        self.b.post(f"/api/matches/{mid}/resign")
        self.assertEqual(len(SENT), 1)
        self.assertEqual(SENT[0][0], self.a_email)
        self.assertIn("You won", SENT[0][1])
        self.assertIn("Bob resigned", SENT[0][1])

    def test_timeout_emails_both_players(self):
        mid = self._pair("first")
        SENT.clear()
        with dbmod.SessionLocal() as db:
            m = db.get(Match, mid)
            m.updated_at = datetime.utcnow() - timedelta(days=G.MOVE_DEADLINE_DAYS + 1)
            db.commit()
        r = self.b.get("/api/cron/tick")
        self.assertEqual(r.json()["forfeited"], 1)
        by = {s[0]: s[1] for s in SENT}
        self.assertIn("ran out of time to move", by[self.a_email])  # Alice (to move) forfeited
        self.assertIn("You won", by[self.b_email])
        # Tick again: nothing new.
        SENT.clear()
        self.b.get("/api/cron/tick")
        self.assertEqual(SENT, [])

    def test_deadline_reminder_once_per_turn(self):
        mid = self._pair("first")
        SENT.clear()
        with dbmod.SessionLocal() as db:
            m = db.get(Match, mid)
            m.updated_at = datetime.utcnow() - timedelta(days=G.MOVE_DEADLINE_DAYS, hours=-6)
            db.commit()
        self.b.get("/api/cron/tick")
        self.assertEqual(len(SENT), 1)
        self.assertEqual(SENT[0][0], self.a_email)
        self.assertIn("left to move", SENT[0][1])
        self.assertIn("about 6 hour", SENT[0][2])
        # Lobby loads also run the sweep, but the reminder is deduped per turn.
        self.a.get("/api/matches")
        self.b.get("/api/cron/tick")
        self.assertEqual(len(SENT), 1)
        with dbmod.SessionLocal() as db:
            kinds = [n.kind for n in db.query(Notification).filter_by(match_id=mid)]
        self.assertEqual(sorted(kinds), ["paired", "reminder"])

    def test_bot_matches_never_email(self):
        r = self.a.post("/api/matches", json={"game_uid": self.game, "options": {}, "opponent": "bot", "seat": "first", "bot_iterations": 5})
        mid = r.json()["match_id"]
        v = self.a.get(f"/api/matches/{mid}").json()
        self.a.post(f"/api/matches/{mid}/move", json={"move": v["legal_moves"][0]})
        self.a.post(f"/api/matches/{mid}/advance")
        self.assertEqual(SENT, [])
        self.assertIsNone(G.match_deadline(dbmod.SessionLocal().get(Match, mid)))


if __name__ == "__main__":
    unittest.main()
