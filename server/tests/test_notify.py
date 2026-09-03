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
# Every test registers users from the same fake IP; keep the limiter out of the
# way except in the test that exercises it.
for _b in ("REGISTER", "LOGIN", "SEEK", "MATCH", "MESSAGE", "FORGOT"):
    os.environ[f"AGP_RATE_LIMIT_{_b}"] = "100000"

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from server import app as appmod, db as dbmod, events, games as G, notify, ratelimit  # noqa: E402
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

    def test_public_seek_view_for_invite_links(self):
        r = self.a.post("/api/seeks", json={"game_uid": self.game, "options": {}, "seat_pref": "first"})
        sid = r.json()["id"]
        anon = TestClient(appmod.app)
        v = anon.get(f"/api/seeks/{sid}")
        self.assertEqual(v.status_code, 200, v.text)
        self.assertEqual(v.json()["creator_name"], "Alice")
        self.assertEqual(v.json()["game_uid"], self.game)
        self.assertFalse(v.json()["mine"])
        self.assertTrue(self.a.get(f"/api/seeks/{sid}").json()["mine"])
        self.b.post(f"/api/seeks/{sid}/accept")
        self.assertEqual(anon.get(f"/api/seeks/{sid}").status_code, 410)
        self.assertEqual(anon.get("/api/seeks/nope").status_code, 410)

    def test_rate_limit_and_caps(self):
        ratelimit.LIMITS["login"] = 3
        ratelimit.reset()
        try:
            anon = TestClient(appmod.app)
            codes = [anon.post("/api/auth/login", json={"email": self.a_email, "password": "wrong"}).status_code for _ in range(4)]
            self.assertEqual(codes, [401, 401, 401, 429])
            r = anon.post("/api/auth/login", json={"email": self.a_email, "password": "secret1"})
            self.assertEqual(r.status_code, 429)  # even a correct password: the IP is throttled
            self.assertIn("Retry-After", r.headers)
        finally:
            ratelimit.LIMITS["login"] = 100000
            ratelimit.reset()
        # Open-seek cap
        for _ in range(appmod.MAX_OPEN_SEEKS):
            self.assertEqual(self.a.post("/api/seeks", json={"game_uid": self.game, "options": {}, "seat_pref": "first"}).status_code, 200)
        r = self.a.post("/api/seeks", json={"game_uid": self.game, "options": {}, "seat_pref": "first"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("open challenges", r.json()["detail"])
        r = self.a.post("/api/quickpair", json={"game_uid": self.game, "options": {"size": 99}})
        self.assertEqual(r.status_code, 400)
        for sk in self.a.get("/api/seeks").json()["seeks"]:
            if sk["mine"]:
                self.a.delete(f"/api/seeks/{sk['id']}")
        # Bot-match cap
        mk = lambda: self.b.post("/api/matches", json={"game_uid": self.game, "options": {}, "opponent": "bot", "seat": "first", "bot_iterations": 5})
        for _ in range(appmod.MAX_ACTIVE_BOT_MATCHES):
            self.assertEqual(mk().status_code, 200)
        r = mk()
        self.assertEqual(r.status_code, 400)
        self.assertIn("vs the computer", r.json()["detail"])

    def test_account_settings(self):
        r = self.a.post("/api/auth/account", json={"display_name": "  Alicia "})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["display_name"], "Alicia")
        self.assertEqual(self.a.get("/api/auth/me").json()["display_name"], "Alicia")
        # Renames propagate to open seeks and active matches.
        mid = self._pair("first")
        sid = self.a.post("/api/seeks", json={"game_uid": self.game, "options": {}, "seat_pref": "first"}).json()["id"]
        self.a.post("/api/auth/account", json={"display_name": "Alice2"})
        self.assertEqual(self.b.get(f"/api/seeks/{sid}").json()["creator_name"], "Alice2")
        self.assertIn("Alice2", [p["name"] for p in self.b.get(f"/api/matches/{mid}").json()["players"]])
        self.a.delete(f"/api/seeks/{sid}")
        # Password change needs the current password.
        r = self.a.post("/api/auth/account", json={"current_password": "nope", "new_password": "newpass1"})
        self.assertEqual(r.status_code, 400)
        r = self.a.post("/api/auth/account", json={"current_password": "secret1", "new_password": "newpass1"})
        self.assertEqual(r.status_code, 200, r.text)
        fresh = TestClient(appmod.app)
        self.assertEqual(fresh.post("/api/auth/login", json={"email": self.a_email, "password": "secret1"}).status_code, 401)
        self.assertEqual(fresh.post("/api/auth/login", json={"email": self.a_email, "password": "newpass1"}).status_code, 200)

    def test_password_reset_flow(self):
        anon = TestClient(appmod.app)
        # No mailer → honest 503, nothing sent.
        r = anon.post("/api/auth/forgot", json={"email": self.a_email})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(SENT, [])
        notify.SMTP_HOST = "smtp.test"  # pretend a mailer is configured (send_email is still captured)
        try:
            # Unknown address: same answer, no email (no account enumeration).
            self.assertEqual(anon.post("/api/auth/forgot", json={"email": "nobody@x.test"}).status_code, 200)
            self.assertEqual(SENT, [])
            self.assertEqual(anon.post("/api/auth/forgot", json={"email": self.a_email.upper()}).status_code, 200)
            self.assertEqual(len(SENT), 1)
            self.assertIn("Reset your", SENT[0][1])
            import re
            token = re.search(r"#/reset/(\S+)", SENT[0][2]).group(1)
            self.assertEqual(anon.post("/api/auth/reset", json={"token": "garbage", "password": "newpass2"}).status_code, 400)
            r = anon.post("/api/auth/reset", json={"token": token, "password": "newpass2"})
            self.assertEqual(r.status_code, 200, r.text)
            self.assertEqual(r.json()["display_name"], "Alice")
            self.assertEqual(anon.get("/api/auth/me").json()["email"], self.a_email)  # signed in by the reset
            # Old password dead, new one works, token is single-use.
            fresh = TestClient(appmod.app)
            self.assertEqual(fresh.post("/api/auth/login", json={"email": self.a_email, "password": "secret1"}).status_code, 401)
            self.assertEqual(fresh.post("/api/auth/login", json={"email": self.a_email, "password": "newpass2"}).status_code, 200)
            self.assertEqual(fresh.post("/api/auth/reset", json={"token": token, "password": "newpass3"}).status_code, 400)
        finally:
            notify.SMTP_HOST = None

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
