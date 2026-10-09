"""Removing a match from your lobby (DELETE /api/matches/{id}).

Until 2026-10-08 the route hard-deleted the match while only `moves` cascaded,
so on Postgres (which enforces foreign keys) every RATED game — rating changes
and notifications reference the match — answered 500. SQLite tests never saw it
because SQLite ignored foreign keys; server/db.py now turns them on, so these
tests fail on the old code exactly as production did.

Run:  .venv/bin/python -m unittest server.tests.test_match_delete -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

if "server.db" not in sys.modules:
    _TMP = tempfile.mkdtemp()
    os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["AGP_EMAIL_SYNC"] = "1"
os.environ.pop("AGP_SMTP_HOST", None)

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from server import app as appmod, db as dbmod, notify, ratelimit  # noqa: E402
from server.models import (  # noqa: E402
    Match, MatchHide, MatchRatingChange, Message, MoveRecord, Notification,
)


def _count(model, mid):
    with dbmod.SessionLocal() as s:
        return s.query(model).filter(model.match_id == mid).count()


class MatchDeleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbmod.init_db()
        notify.send_email = lambda *a, **k: None
        for b in ratelimit.LIMITS:
            ratelimit.LIMITS[b] = 100000

    def test_sqlite_enforces_foreign_keys_like_postgres(self):
        if dbmod.engine.dialect.name != "sqlite":
            self.skipTest("postgres always enforces them")
        with dbmod.engine.connect() as c:
            self.assertEqual(c.exec_driver_sql("PRAGMA foreign_keys").scalar(), 1)

    def _register(self, tag):
        c = TestClient(appmod.app)
        n = datetime.utcnow().strftime("%H%M%S%f")
        r = c.post("/api/auth/register", json={"email": f"{tag}{n}@x.test",
                                                "display_name": tag, "password": "secret1"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def _lobby_ids(self, c):
        r = c.get("/api/matches")
        self.assertEqual(r.status_code, 200, r.text)
        return {m["id"] for m in r.json()["matches"]}

    def _human_match(self):
        a, b = self._register("Alice"), self._register("Bob")
        r = a.post("/api/seeks", json={"game_uid": "tic_tac_toe", "options": {}, "seat_pref": "first"})
        r = b.post(f"/api/seeks/{r.json()['id']}/accept")
        self.assertEqual(r.status_code, 200, r.text)
        mid = r.json()["match_id"]
        self.assertEqual(a.post(f"/api/matches/{mid}/messages", json={"body": "gl"}).status_code, 200)
        return a, b, mid

    def test_finished_rated_game_vs_a_person_is_hidden_not_destroyed(self):
        a, b, mid = self._human_match()
        self.assertEqual(a.post(f"/api/matches/{mid}/resign").status_code, 200)
        # The rows that made the old hard delete 500 on Postgres.
        self.assertEqual(_count(MatchRatingChange, mid), 2)
        self.assertGreater(_count(Notification, mid), 0)

        r = a.delete(f"/api/matches/{mid}")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertNotIn(mid, self._lobby_ids(a))          # gone from Alice's lobby
        self.assertIn(mid, self._lobby_ids(b))             # still in Bob's
        self.assertEqual(b.get(f"/api/matches/{mid}").status_code, 200)   # replay/profile link
        self.assertEqual(_count(MatchRatingChange, mid), 2)                # history intact
        self.assertEqual(_count(Message, mid), 1)
        self.assertEqual(a.delete(f"/api/matches/{mid}").status_code, 200)  # idempotent
        self.assertEqual(_count(MatchHide, mid), 1)

        self.assertEqual(b.delete(f"/api/matches/{mid}").status_code, 200)
        self.assertNotIn(mid, self._lobby_ids(b))
        with dbmod.SessionLocal() as s:
            self.assertIsNotNone(s.get(Match, mid))

    def test_live_game_vs_a_person_must_be_resigned_first(self):
        a, _, mid = self._human_match()
        self.assertEqual(a.delete(f"/api/matches/{mid}").status_code, 400)
        self.assertIn(mid, self._lobby_ids(a))

    def test_strangers_cannot_remove_a_match(self):
        _, _, mid = self._human_match()
        self.assertEqual(self._register("Eve").delete(f"/api/matches/{mid}").status_code, 403)

    def test_bot_game_is_deleted_with_all_its_rows(self):
        a = self._register("Solo")
        r = a.post("/api/matches", json={"game_uid": "tic_tac_toe", "opponent": "bot", "seat": "first"})
        self.assertEqual(r.status_code, 200, r.text)
        mid = r.json()["match_id"]
        legal = a.get(f"/api/matches/{mid}").json()["legal_moves"]
        self.assertEqual(a.post(f"/api/matches/{mid}/move", json={"move": legal[0]}).status_code, 200)
        self.assertEqual(a.post(f"/api/matches/{mid}/advance").status_code, 200)
        self.assertEqual(a.post(f"/api/matches/{mid}/messages", json={"body": "hi"}).status_code, 200)
        self.assertGreater(_count(MoveRecord, mid), 0)

        r = a.delete(f"/api/matches/{mid}")
        self.assertEqual(r.status_code, 200, r.text)
        with dbmod.SessionLocal() as s:
            self.assertIsNone(s.get(Match, mid))
        for model in (MoveRecord, Message, Notification, MatchRatingChange, MatchHide):
            self.assertEqual(_count(model, mid), 0, model.__name__)


if __name__ == "__main__":
    unittest.main()
