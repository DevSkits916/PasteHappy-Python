from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

STATES = {"pending", "processing", "posted", "failed", "blocked", "uncertain", "skipped"}
RETRYABLE = {"failed", "blocked", "uncertain", "skipped"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class QueueStore:
    def __init__(self, file_path: Path | str):
        self.file_path = Path(file_path)
        self.state = {"version": 1, "jobs": []}
        self.lock = threading.RLock()

    def init(self) -> "QueueStore":
        with self.lock:
            if self.file_path.exists():
                loaded = json.loads(self.file_path.read_text(encoding="utf-8"))
                self.state.update(loaded)
            for job in self.state["jobs"]:
                if job["status"] == "processing":
                    job.update(status="failed", lastError="BROWSER_ERROR: Application stopped while processing.", updatedAt=_now())
            self._persist()
        return self

    def list(self) -> list[dict]:
        with self.lock:
            return deepcopy(self.state["jobs"])

    def get(self, job_id: str) -> dict | None:
        with self.lock:
            job = self._find(job_id)
            return deepcopy(job) if job else None

    def import_rows(self, rows: list[dict]) -> dict[str, int]:
        created = duplicates = 0
        with self.lock:
            for row in rows:
                if not row.get("groupUrl") or not row.get("postText"):
                    continue
                fingerprint = _fingerprint(row)
                if any(job["fingerprint"] == fingerprint and job["status"] != "skipped" for job in self.state["jobs"]):
                    duplicates += 1
                    continue
                now = _now()
                self.state["jobs"].append({
                    "id": str(uuid.uuid4()), "groupName": row.get("groupName") or row["groupUrl"],
                    "groupUrl": row["groupUrl"], "postText": row["postText"], "status": "pending",
                    "attempts": 0, "createdAt": now, "updatedAt": now, "postedAt": None,
                    "lastError": None, "fingerprint": fingerprint,
                })
                created += 1
            self._persist()
            return {"created": created, "duplicates": duplicates, "total": len(self.state["jobs"])}

    def transition(self, job_id: str, status: str, patch: dict | None = None) -> dict | None:
        if status not in STATES:
            raise ValueError(f"Invalid queue status: {status}")
        with self.lock:
            job = self._find(job_id)
            if not job:
                return None
            job.update(patch or {})
            job.update(status=status, updatedAt=_now())
            if status == "posted" and not job.get("postedAt"):
                job["postedAt"] = job["updatedAt"]
            self._persist()
            return deepcopy(job)

    def claim_next(self) -> dict | None:
        with self.lock:
            job = next((item for item in self.state["jobs"] if item["status"] == "pending"), None)
            if not job:
                return None
            return self.transition(job["id"], "processing", {"attempts": job["attempts"] + 1, "lastError": None})

    def retry(self, job_id: str) -> dict | None:
        with self.lock:
            job = self._find(job_id)
            if not job:
                return None
            if job["status"] not in RETRYABLE:
                raise ValueError(f"Cannot retry a {job['status']} job")
            return self.transition(job_id, "pending", {"lastError": None, "postedAt": None})

    def skip(self, job_id: str) -> dict | None:
        return self.transition(job_id, "skipped")

    def clear(self) -> dict[str, int]:
        with self.lock:
            cleared = len(self.state["jobs"])
            self.state["jobs"] = []
            self._persist()
            return {"cleared": cleared}

    def _find(self, job_id: str) -> dict | None:
        return next((item for item in self.state["jobs"] if item["id"] == job_id), None)

    def _persist(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        os.replace(temporary, self.file_path)


def _fingerprint(row: dict) -> str:
    url = row["groupUrl"].strip().rstrip("/").lower()
    text = row["postText"].strip()
    return hashlib.sha256(f"{url}\0{text}".encode()).hexdigest()
