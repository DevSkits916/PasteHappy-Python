from __future__ import annotations

import asyncio
import os
import threading
from concurrent.futures import Future
from pathlib import Path

from playwright.async_api import async_playwright

from .facebook import post_to_facebook


class BrowserManager:
    def __init__(self, *, profile_path: Path, headless: bool, executable_path: str | None = None):
        self.profile_path = profile_path
        self.headless = headless
        self.executable_path = executable_path
        self.context = None
        self._playwright = None
        self._ready = threading.Event()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="pastehappy-browser", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("Playwright event loop did not start.")

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    def submit(self, coroutine) -> Future:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    def call(self, coroutine, timeout: float | None = 60):
        return self.submit(coroutine).result(timeout=timeout)

    def exists(self) -> bool:
        return self.profile_path.exists() and any(self.profile_path.iterdir())

    @property
    def is_open(self) -> bool:
        return self.context is not None

    def set_headless(self, value: bool) -> None:
        next_headless = bool(value)
        if self.is_open and self.headless != next_headless:
            raise RuntimeError("Close the current Playwright browser before changing headless mode.")
        self.headless = next_headless

    async def open(self):
        if self.context:
            return self.context
        if not self._playwright:
            self._playwright = await async_playwright().start()
        self.profile_path.mkdir(parents=True, exist_ok=True)
        executable = self.executable_path or self._system_chrome()
        options = {"headless": self.headless, "no_viewport": True, "args": ["--start-maximized"]}
        if executable:
            options["executable_path"] = executable
        self.context = await self._playwright.chromium.launch_persistent_context(str(self.profile_path), **options)
        self.context.on("close", lambda _context=None: setattr(self, "context", None))
        return self.context

    async def login(self, headless: bool | None = None) -> dict[str, bool]:
        if headless is not None:
            self.set_headless(headless)
        if self.headless:
            raise RuntimeError("Headless mode cannot be used for interactive Facebook login. Turn it off, log in, then enable it for a later run.")
        context = await self.open()
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        return {"opened": True}

    async def post_job(self, job: dict, on_step):
        context = await self.open()
        page = context.pages[0] if context.pages else await context.new_page()
        return await post_to_facebook(page, job, on_step)

    async def close(self) -> None:
        context, self.context = self.context, None
        if context:
            try:
                await context.close()
            except Exception:
                pass

    async def shutdown(self) -> None:
        await self.close()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    def stop_loop(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)

    @staticmethod
    def _system_chrome() -> str | None:
        if os.name != "nt":
            return None
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
        return next((str(path) for path in candidates if path.is_file()), None)
