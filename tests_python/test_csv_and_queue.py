from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pastehappy.csv_parser import parse_csv
from pastehappy.queue_store import QueueStore


class CsvTests(unittest.TestCase):
    def test_parses_aliases_and_quoted_newlines(self):
        rows = parse_csv('\ufeffname,link,message\nGroup,https://facebook.com/groups/1,"Hello, world\nAgain"')
        self.assertEqual(rows, [{
            "groupName": "Group", "groupUrl": "https://facebook.com/groups/1", "postText": "Hello, world\nAgain",
        }])


class QueueStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "queue.json"
        self.store = QueueStore(self.path).init()

    def tearDown(self):
        self.temporary.cleanup()

    def test_import_transition_duplicate_retry_and_clear(self):
        row = {"groupName": "One", "groupUrl": "https://facebook.com/groups/1/", "postText": "Hi"}
        self.assertEqual(self.store.import_rows([row])["created"], 1)
        self.assertEqual(self.store.import_rows([row])["duplicates"], 1)
        job = self.store.claim_next()
        self.assertEqual(job["status"], "processing")
        self.assertEqual(job["attempts"], 1)
        self.store.transition(job["id"], "uncertain", {"lastError": "verify"})
        self.assertEqual(self.store.retry(job["id"])["status"], "pending")
        self.assertEqual(self.store.clear(), {"cleared": 1})

    def test_recovers_processing_job(self):
        now = "2026-09-21T00:00:00Z"
        self.path.write_text(json.dumps({"version": 1, "jobs": [{
            "id": "1", "status": "processing", "groupName": "One", "groupUrl": "https://example.com",
            "postText": "Hi", "attempts": 1, "createdAt": now, "updatedAt": now,
            "postedAt": None, "lastError": None, "fingerprint": "x",
        }]}), encoding="utf-8")
        recovered = QueueStore(self.path).init().get("1")
        self.assertEqual(recovered["status"], "failed")
        self.assertIn("Application stopped", recovered["lastError"])


if __name__ == "__main__":
    unittest.main()
