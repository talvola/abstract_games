"""Capacity safeguards: the shared bot CPU gate, the anonymous bot endpoint's
rate limit, and the cached game catalogue (see server/games.py BOT_CONCURRENCY).

Run:  .venv/bin/python -m unittest server.tests.test_capacity -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

_TMP = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["AGP_RATE_LIMIT_BOT"] = "100000"

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient  # noqa: E402

from server import app as appmod, db as dbmod, games as G, ratelimit  # noqa: E402


class CapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dbmod.init_db()
        cls.c = TestClient(appmod.app)

    def _new(self, uid="tic_tac_toe"):
        r = self.c.post(f"/api/games/{uid}/new", json={"options": {}})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_stateless_bot_returns_a_legal_move(self):
        d = self._new()
        r = self.c.post("/api/games/tic_tac_toe/bot", json={"state": d["state"], "iterations": 50})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn(r.json()["move"], d["view"]["legal_moves"])

    def test_bot_endpoint_is_rate_limited_per_ip(self):
        d = self._new()
        old = ratelimit.LIMITS.get("bot")
        try:
            ratelimit.LIMITS["bot"] = 2
            ratelimit.reset()
            codes = [self.c.post("/api/games/tic_tac_toe/bot",
                                 json={"state": d["state"], "iterations": 5}).status_code
                     for _ in range(3)]
            self.assertEqual(codes, [200, 200, 429])
        finally:
            ratelimit.LIMITS["bot"] = old
            ratelimit.reset()

    def test_game_list_is_cached_per_registry_generation(self):
        r1 = self.c.get("/api/games")
        self.assertEqual(r1.status_code, 200)
        body = r1.json()
        self.assertIn("move_deadline_days", body)
        self.assertIn("email", body)
        self.assertEqual(len(body["games"]), len(appmod.registry.entries))
        self.assertTrue(any(g["uid"] == "chess" for g in body["games"]))
        cached = appmod._games_cache["body"]
        self.assertEqual(self.c.get("/api/games").content, cached)       # served from cache
        # A reload (upload path) swaps the entries dict ⇒ the cache rebuilds.
        appmod._games_cache["entries"] = None
        self.assertEqual(json.loads(self.c.get("/api/games").content), body)

    def test_bot_gate_serialises_thinking_and_shrinks_budget_under_queue(self):
        running, peak, budgets, lock = [0], [0], [], threading.Lock()

        class FakeBot:
            def __init__(self, rng, iterations, max_time):
                self.max_time = max_time

            def select(self, game, state):
                with lock:
                    running[0] += 1
                    peak[0] = max(peak[0], running[0])
                    budgets.append(self.max_time)
                time.sleep(0.15)
                with lock:
                    running[0] -= 1
                return "x"

        real = G.MCTSBot
        G.MCTSBot = FakeBot
        try:
            threads = [threading.Thread(target=G.bot_move, args=(None, None, 10)) for _ in range(4)]
            for t in threads:
                t.start()
                time.sleep(0.02)          # let each queue up behind the first
            for t in threads:
                t.join()
        finally:
            G.MCTSBot = real
        self.assertEqual(peak[0], G.BOT_CONCURRENCY)          # never more than the cap
        self.assertEqual(budgets[0], G.BOT_MAX_TIME)          # nobody waiting ⇒ full budget
        self.assertLess(budgets[1], G.BOT_MAX_TIME)           # queued ⇒ shorter budget
        self.assertTrue(all(b >= min(G.BOT_MIN_TIME, G.BOT_MAX_TIME) for b in budgets))
        self.assertEqual(G._bot_waiting, 0)                   # counter doesn't leak


if __name__ == "__main__":
    unittest.main()
