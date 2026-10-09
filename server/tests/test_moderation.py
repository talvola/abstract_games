"""Chat moderation through the real routes: report a message, block/unblock a
user (TestClient + a throw-away SQLite DB, same pattern as test_notify).

Run:  .venv/bin/python -m unittest server.tests.test_moderation -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Never touch a real DB: point at a temp SQLite unless another test module
# already imported `server` (then its temp DB is reused, which is equally fine).
if "server.db" not in sys.modules:
    _TMP = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["AGP_EMAIL_SYNC"] = "1"
os.environ.setdefault("AGP_BASE_URL", "https://example.test")  # test_notify asserts it
os.environ.pop("AGP_SMTP_HOST", None)
for _b in ("REGISTER", "LOGIN", "SEEK", "MATCH", "MESSAGE", "FORGOT", "REPORT"):
    os.environ[f"AGP_RATE_LIMIT_{_b}"] = "100000"

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from server import app as appmod, db as dbmod, notify, ratelimit  # noqa: E402
from server.models import MessageReport, UserBlock  # noqa: E402

SENT: list[tuple[str, str, str]] = []


def _capture(to, subject, body):
    SENT.append((to, subject, body))


class ModerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbmod.init_db()
        notify.send_email = _capture
        # LIMITS is computed at import; if another test module imported
        # `server` first our env var was too late, so set it directly.
        for b in ratelimit.LIMITS:
            ratelimit.LIMITS[b] = 100000

    def setUp(self):
        SENT.clear()
        os.environ.pop("AGP_REPORT_EMAIL", None)
        n = datetime.utcnow().strftime("%H%M%S%f")
        self.a, self.a_id = self._register(f"a{n}@x.test", "Alice")
        self.b, self.b_id = self._register(f"b{n}@x.test", "Bob")
        self.c, self.c_id = self._register(f"c{n}@x.test", "Carol")  # a spectator
        # Alice and Bob play tic-tac-toe; each says something.
        r = self.a.post("/api/seeks", json={"game_uid": "tic_tac_toe", "options": {}, "seat_pref": "first"})
        self.assertEqual(r.status_code, 200, r.text)
        r = self.b.post(f"/api/seeks/{r.json()['id']}/accept")
        self.assertEqual(r.status_code, 200, r.text)
        self.mid = r.json()["match_id"]
        SENT.clear()  # drop the pairing email
        for c, text in ((self.a, "hello"), (self.b, "you are terrible"), (self.a, "rude")):
            r = c.post(f"/api/matches/{self.mid}/messages", json={"body": text})
            self.assertEqual(r.status_code, 200, r.text)

    def _register(self, email, name):
        c = TestClient(appmod.app)
        r = c.post("/api/auth/register", json={"email": email, "display_name": name, "password": "secret1"})
        self.assertEqual(r.status_code, 200, r.text)
        return c, r.json()["id"]

    def _msgs(self, client):
        r = client.get(f"/api/matches/{self.mid}/messages")
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()["messages"]

    def _bob_msg_id(self):
        [m] = [m for m in self._msgs(self.c) if m["user_id"] == self.b_id]
        return m["id"]

    def _db(self):
        return dbmod.SessionLocal()

    # -- report ------------------------------------------------------------
    def test_messages_carry_ids(self):
        msgs = self._msgs(self.c)
        self.assertEqual([m["body"] for m in msgs], ["hello", "you are terrible", "rude"])
        self.assertTrue(all(isinstance(m["id"], int) for m in msgs))

    def test_report_creates_row_and_emails_report_address(self):
        os.environ["AGP_REPORT_EMAIL"] = "mod@x.test"
        mid = self._bob_msg_id()
        r = self.a.post(f"/api/messages/{mid}/report", json={"reason": "  insulting  "})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json(), {"ok": True, "already_reported": False})
        with self._db() as db:
            rows = db.query(MessageReport).filter_by(message_id=mid).all()
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual((row.reporter_id, row.author_id, row.match_id, row.body, row.reason),
                             (self.a_id, self.b_id, self.mid, "you are terrible", "insulting"))
        self.assertEqual(len(SENT), 1)
        to, subject, body = SENT[0]
        self.assertEqual(to, "mod@x.test")
        self.assertIn("Alice reported Bob", subject)
        self.assertIn("you are terrible", body)
        self.assertIn("insulting", body)
        self.assertIn(self.mid, body)

    def test_report_without_recipient_only_logs(self):
        mid = self._bob_msg_id()
        r = self.a.post(f"/api/messages/{mid}/report")  # no body at all: reason optional
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(SENT, [])  # AGP_REPORT_EMAIL unset -> logged, not emailed
        with self._db() as db:
            self.assertEqual(db.query(MessageReport).filter_by(message_id=mid).count(), 1)

    def test_duplicate_report_is_idempotent(self):
        os.environ["AGP_REPORT_EMAIL"] = "mod@x.test"
        mid = self._bob_msg_id()
        self.assertFalse(self.a.post(f"/api/messages/{mid}/report", json={"reason": "x"}).json()["already_reported"])
        r = self.a.post(f"/api/messages/{mid}/report", json={"reason": "again"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["already_reported"])
        self.assertEqual(len(SENT), 1)  # one email, not two
        # A DIFFERENT reporter is a separate report.
        self.assertFalse(self.c.post(f"/api/messages/{mid}/report").json()["already_reported"])
        with self._db() as db:
            self.assertEqual(db.query(MessageReport).filter_by(message_id=mid).count(), 2)

    def test_report_edge_cases(self):
        mid = self._bob_msg_id()
        self.assertEqual(self.b.post(f"/api/messages/{mid}/report").status_code, 400)  # own message
        self.assertEqual(self.a.post("/api/messages/99999999/report").status_code, 404)
        anon = TestClient(appmod.app)
        self.assertEqual(anon.post(f"/api/messages/{mid}/report").status_code, 401)

    def test_report_is_rate_limited(self):
        mid = self._bob_msg_id()
        old = ratelimit.LIMITS["report"]
        try:
            ratelimit.LIMITS["report"] = 2
            ratelimit.reset()
            codes = [self.a.post(f"/api/messages/{mid}/report").status_code for _ in range(3)]
            self.assertEqual(codes, [200, 200, 429])
        finally:
            ratelimit.LIMITS["report"] = old
            ratelimit.reset()

    # -- block -------------------------------------------------------------
    def test_block_hides_messages_from_blocker_only_and_unblock_restores(self):
        r = self.a.post(f"/api/users/{self.b_id}/block")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual([m["body"] for m in self._msgs(self.a)], ["hello", "rude"])
        # Others (the blocked user, a spectator, an anonymous reader) still see everything.
        for c in (self.b, self.c, TestClient(appmod.app)):
            self.assertEqual(len(self._msgs(c)), 3)
        # Listed, idempotent.
        self.assertEqual(self.a.post(f"/api/users/{self.b_id}/block").status_code, 200)
        blocks = self.a.get("/api/blocks").json()["blocks"]
        self.assertEqual([(b["user_id"], b["name"]) for b in blocks], [(self.b_id, "Bob")])
        with self._db() as db:
            self.assertEqual(db.query(UserBlock).filter_by(blocker_id=self.a_id).count(), 1)
        # Unblock restores.
        r = self.a.delete(f"/api/users/{self.b_id}/block")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(self._msgs(self.a)), 3)
        self.assertEqual(self.a.get("/api/blocks").json()["blocks"], [])
        self.assertEqual(self.a.delete(f"/api/users/{self.b_id}/block").status_code, 200)  # idempotent

    def test_cannot_block_self_or_nobody(self):
        self.assertEqual(self.a.post(f"/api/users/{self.a_id}/block").status_code, 400)
        self.assertEqual(self.a.post("/api/users/99999999/block").status_code, 404)

    def test_block_routes_need_login(self):
        anon = TestClient(appmod.app)
        self.assertEqual(anon.post(f"/api/users/{self.b_id}/block").status_code, 401)
        self.assertEqual(anon.delete(f"/api/users/{self.b_id}/block").status_code, 401)
        self.assertEqual(anon.get("/api/blocks").status_code, 401)

    def test_block_hides_seeks_and_prevents_pairing(self):
        game = "connect_four"
        r = self.b.post("/api/seeks", json={"game_uid": game, "options": {}, "seat_pref": "random"})
        self.assertEqual(r.status_code, 200, r.text)
        seek_id = r.json()["id"]
        self.assertIn(seek_id, [s["id"] for s in self.a.get("/api/seeks").json()["seeks"]])
        self.a.post(f"/api/users/{self.b_id}/block")
        # Hidden from the blocker (and the blocked user doesn't see the blocker's).
        self.assertNotIn(seek_id, [s["id"] for s in self.a.get("/api/seeks").json()["seeks"]])
        self.assertIn(seek_id, [s["id"] for s in self.c.get("/api/seeks").json()["seeks"]])
        # Quick-pair never matches the pair, in either direction.
        r = self.a.post("/api/quickpair", json={"game_uid": game, "options": {}})
        self.assertFalse(r.json()["paired"], r.text)
        a_seek = r.json()["seek_id"]
        self.assertEqual(self.b.post(f"/api/seeks/{a_seek}/accept").status_code, 404)
        # Clean up so seek caps / other tests aren't affected.
        self.a.delete(f"/api/seeks/{a_seek}")
        self.b.delete(f"/api/seeks/{seek_id}")


if __name__ == "__main__":
    unittest.main()
