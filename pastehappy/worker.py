from __future__ import annotations

import asyncio
import logging
import threading
from collections import deque
from datetime import datetime, timezone

from .clipboard import copy_to_system_clipboard
LOGGER = logging.getLogger("pastehappy.worker")


class QueueWorker:
    def __init__(self, *, store, browser, default_job_delay: int, max_jobs_per_run: int):
        self.store = store
        self.browser = browser
        self.defaults = {"delayMs": default_job_delay, "maxJobs": max_jobs_per_run}
        self.mode = "idle"
        self.current_job = None
        self.current_step = "Idle"
        self.last_error = None
        self.options = {}
        self.future = None
        self.skip_requested: set[str] = set()
        self.lock = threading.RLock()
        self.logs = deque(maxlen=500)
        self.log_sequence = 0

    def status(self) -> dict:
        with self.lock:
            return {
                "logs": list(self.logs),
                "state": self.mode,
                "currentJob": dict(self.current_job) if self.current_job else None,
                "currentStep": self.current_step,
                "lastError": self.last_error,
            }

    def start(self, options: dict | None = None) -> bool:
        with self.lock:
            if self.future and not self.future.done():
                return False
            self.options = {
                "delayMs": self.defaults["delayMs"], "maxJobs": self.defaults["maxJobs"],
                "copyClipboard": False, "membershipAnswers": [], "acceptGroupRules": False, "joinBeforePost": False, "composerTimeoutMs": 15000, "cooldownMs": 0, "stopOnFailure": False, "stopOnCheckpoint": True,
                **(options or {}),
            }
            timeout = self.options["composerTimeoutMs"]
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1000 <= timeout <= 120000:
                raise ValueError("Composer timeout must be between 1 and 120 seconds.")
            if not isinstance(self.options["joinBeforePost"], bool):
                raise ValueError("Join before posting must be a boolean.")
            answers = self.options["membershipAnswers"]
            if not isinstance(answers, list) or any(not isinstance(item, dict) or not isinstance(item.get("question"), str) or not item["question"].strip() or not isinstance(item.get("answer"), str) or not item["answer"].strip() for item in answers):
                raise ValueError("Membership answers must contain nonempty question and answer strings.")
            if not isinstance(self.options["acceptGroupRules"], bool):
                raise ValueError("Accept group rules must be a boolean.")
            self.last_error = None
            if "headless" in self.options:
                self.browser.set_headless(bool(self.options["headless"]))
            self.mode = "running"
            self._set_step("Worker started")
            self.future = self.browser.submit(self._run())
            return True

    def pause(self) -> None:
        with self.lock:
            if self.future and not self.future.done():
                self.mode = "paused"
                self._set_step("Pause requested")

    def resume(self) -> None:
        with self.lock:
            if self.future and not self.future.done() and self.mode == "paused":
                self.mode = "running"
                self._set_step("Worker resumed")

    def stop(self) -> None:
        with self.lock:
            self.mode = "stopped"
            self._set_step("Stop requested")

    def clear_queue(self) -> dict:
        self.stop()
        with self.lock:
            self.current_job = None
            self._set_step("Queue cleared")
            self.skip_requested.clear()
        self.browser.call(self.browser.close())
        return self.store.clear()

    def skip_current(self) -> dict | None:
        with self.lock:
            if not self.future or self.future.done() or not self.current_job:
                return None
            job_id = self.current_job["id"]
            self.skip_requested.add(job_id)
            self._set_step("Skipping current group...")
        skipped = self.store.transition(job_id, "skipped")
        self.browser.call(self.browser.close())
        return skipped

    async def _run(self) -> None:
        processed = 0
        try:
            while self._mode() != "stopped" and processed < max(0, int(self.options["maxJobs"])):
                while self._mode() == "paused":
                    await asyncio.sleep(0.25)
                if self._mode() == "stopped":
                    break
                job = self.store.claim_next()
                if not job:
                    break
                with self.lock:
                    self.current_job = job
                    self._set_step("Starting group...")
                LOGGER.info("Starting job %s", job["id"])
                skipped = False
                try:
                    if self.options.get("copyClipboard", False):
                        self._set_step("Copying post text to clipboard...")
                        if not await asyncio.to_thread(copy_to_system_clipboard, job["postText"]):
                            self._set_step("Clipboard unavailable; filling composer directly")
                    await self.browser.post_job(job, self._set_step, join_before_post=self.options["joinBeforePost"], composer_timeout_ms=self.options["composerTimeoutMs"], membership_answers=self.options["membershipAnswers"], accept_group_rules=self.options["acceptGroupRules"])
                    if self._consume_skip(job["id"]):
                        skipped = True
                        LOGGER.info("Job %s skipped", job["id"])
                    else:
                        self.store.transition(job["id"], "posted")
                        self._set_step("Post marked posted")
                except Exception as error:
                    if self._consume_skip(job["id"]):
                        skipped = True
                    else:
                        code = getattr(error, "code", "BROWSER_ERROR")
                        security = bool(getattr(error, "security", False))
                        skipped = code in {"COMPOSER_NOT_FOUND", "JOIN_PENDING"}
                        status = "skipped" if skipped else "uncertain" if code == "POST_UNCERTAIN" else "blocked" if security else "failed"
                        with self.lock:
                            self.last_error = str(error)
                        self.store.transition(job["id"], status, {"lastError": str(error)})
                        self._set_step(f"{status}: {error}")
                        LOGGER.exception("Job %s ended with %s", job["id"], status)
                        if (self.options["stopOnFailure"] and not skipped) or (security and self.options["stopOnCheckpoint"]):
                            with self.lock:
                                self.mode = "stopped"
                            break
                processed += 1
                if self._mode() == "running" and not skipped:
                    delay = max(float(self.options["delayMs"]), float(self.options["cooldownMs"])) / 1000
                    self._set_step(f"Waiting {max(0, delay):g} seconds before next group...")
                    deadline = asyncio.get_running_loop().time() + max(0, delay)
                    while self._mode() == "running" and asyncio.get_running_loop().time() < deadline:
                        await asyncio.sleep(min(0.1, deadline - asyncio.get_running_loop().time()))
        finally:
            with self.lock:
                if self.mode != "stopped":
                    self.mode = "idle"
                self.current_job = None
                self._set_step("Worker stopped" if self.mode == "stopped" else "Run complete")

    async def shutdown(self) -> None:
        self.stop()
        future = self.future
        if future and not future.done():
            future.cancel()
        await self.browser.shutdown()

    def _mode(self) -> str:
        with self.lock:
            return self.mode

    def _set_step(self, step: str) -> None:
        with self.lock:
            self.current_step = step
            self.log_sequence += 1
            self.logs.append({"id": self.log_sequence, "time": datetime.now(timezone.utc).isoformat(), "message": step, "group": self.current_job.get("groupName") if self.current_job else None})
        LOGGER.info("%s", step)

    def _consume_skip(self, job_id: str) -> bool:
        with self.lock:
            if job_id in self.skip_requested:
                self.skip_requested.remove(job_id)
                return True
            return False
