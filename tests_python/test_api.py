from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pastehappy.queue_store import QueueStore
from pastehappy.web import create_app


class FakeWorker:
    def status(self): return {"state": "idle", "currentJob": None, "currentStep": "Idle", "lastError": None}
    def start(self, _options): return True
    def pause(self): pass
    def resume(self): pass
    def stop(self): pass
    def clear_queue(self): return {"cleared": 1}
    def skip_current(self): return None


class FakeBrowser:
    headless = False
    is_open = False
    def exists(self): return False
    async def login(self, _headless): return {"opened": True}
    def call(self, coroutine, timeout=None):
        coroutine.close()
        return {"opened": True}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        (root / "dist").mkdir()
        (root / "dist/index.html").write_text("<h1>PasteHappy</h1>", encoding="utf-8")
        store = QueueStore(root / "queue.json").init()
        app = create_app(store=store, worker=FakeWorker(), browser=FakeBrowser(), root=root)
        app.testing = True
        self.client = app.test_client()

    def tearDown(self):
        self.temporary.cleanup()

    def test_queue_api(self):
        response = self.client.post("/api/queue/import", json={
            "csv": "group,url,post\nOne,https://facebook.com/groups/1,Hi",
        })
        self.assertEqual(response.status_code, 201)
        job = self.client.get("/api/queue").get_json()[0]
        self.assertEqual(job["groupName"], "One")
        self.assertEqual(self.client.post(f"/api/queue/{job['id']}/skip").get_json()["status"], "skipped")
        self.assertEqual(self.client.post(f"/api/queue/{job['id']}/retry").get_json()["status"], "pending")

    def test_status_and_frontend(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        response.close()
        status = self.client.get("/api/status").get_json()
        self.assertEqual(status["state"], "idle")
        self.assertFalse(status["browser"]["open"])


if __name__ == "__main__":
    unittest.main()
