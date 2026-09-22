from __future__ import annotations

import asyncio
import logging
import threading

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

    def status(self) -> dict:
        with self.lock:
            return {
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
                "cooldownMs": 0, "stopOnFailure": False, "stopOnCheckpoint": True,
                **(options or {}),
            }
            if "headless" in self.options:
                self.browser.set_headless(bool(self.options["headless"]))
            self.mode = "running"
            self.future = self.browser.submit(self._run())
            return True

    def pause(self) -> None:
        with self.lock:
            if self.future and not self.future.done():
                self.mode = "paused"

    def resume(self) -> None:
        with self.lock:
            if self.future and not self.future.done() and self.mode == "paused":
                self.mode = "running"

    def stop(self) -> None:
        with self.lock:
            self.mode = "stopped"

    def clear_queue(self) -> dict:
        self.stop()
        with self.lock:
            self.current_job = None
            self.current_step = "Queue cleared"
            self.skip_requested.clear()
        self.browser.call(self.browser.close())
        return self.store.clear()

    def skip_current(self) -> dict | None:
        with self.lock:
            if not self.future or self.future.done() or not self.current_job:
                return None
            job_id = self.current_job["id"]
            self.skip_requested.add(job_id)
            self.current_step = "Skipping current group..."
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
                    self.current_step = "Starting job..."
                LOGGER.info("Starting job %s", job["id"])
                skipped = False
                try:
                    self._set_step("Copying post text to clipboard...")
                    if not copy_to_system_clipboard(job["postText"]):
                        LOGGER.warning("Job %s could not copy text; the composer will still be filled directly.", job["id"])
                    await self.browser.post_job(job, self._set_step)
                    if self._consume_skip(job["id"]):
                        skipped = True
                        LOGGER.info("Job %s skipped", job["id"])
                    else:
                        self.store.transition(job["id"], "posted")
                        LOGGER.info("Job %s marked posted", job["id"])
                except Exception as error:
                    if self._consume_skip(job["id"]):
                        skipped = True
                    else:
                        code = getattr(error, "code", "BROWSER_ERROR")
                        security = bool(getattr(error, "security", False))
                        status = "uncertain" if code == "POST_UNCERTAIN" else "blocked" if security else "failed"
                        with self.lock:
                            self.last_error = str(error)
                        self.store.transition(job["id"], status, {"lastError": str(error)})
                        LOGGER.exception("Job %s failed", job["id"])
                        if self.options["stopOnFailure"] or (security and self.options["stopOnCheckpoint"]):
                            with self.lock:
                                self.mode = "stopped"
                            break
                processed += 1
                if self._mode() == "running" and not skipped:
                    delay = max(float(self.options["delayMs"]), float(self.options["cooldownMs"])) / 1000
                    await asyncio.sleep(max(0, delay))
        finally:
            with self.lock:
                if self.mode != "stopped":
                    self.mode = "idle"
                self.current_job = None

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
        LOGGER.info("%s", step)

    def _consume_skip(self, job_id: str) -> bool:
        with self.lock:
            if job_id in self.skip_requested:
                self.skip_requested.remove(job_id)
                return True
            return False
