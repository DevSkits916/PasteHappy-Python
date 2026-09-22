from __future__ import annotations

import re
from collections.abc import Callable


class AutomationError(RuntimeError):
    def __init__(self, code: str, message: str, *, security: bool = False):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.security = security


CHECKPOINT = re.compile(r"checkpoint|confirm your identity|account temporarily locked|security check", re.I)
CAPTCHA = re.compile(r"captcha|enter the characters you see", re.I)


async def first_visible(page, locators, timeout_ms: int = 8000):
    if not isinstance(locators, list):
        locators = [locators]
    elapsed = 0
    while elapsed < timeout_ms:
        for matches in locators:
            for index in range(await matches.count()):
                locator = matches.nth(index)
                try:
                    if await locator.is_visible():
                        return locator
                except Exception:
                    pass
        await page.wait_for_timeout(250)
        elapsed += 250
    return None


async def first_enabled(page, locators, timeout_ms: int = 8000):
    elapsed = 0
    while elapsed < timeout_ms:
        for matches in locators:
            for index in range(await matches.count()):
                locator = matches.nth(index)
                try:
                    if await locator.is_visible() and await locator.is_enabled():
                        return locator
                except Exception:
                    pass
        await page.wait_for_timeout(250)
        elapsed += 250
    return None


def _normalized(value: str) -> str:
    return " ".join(value.split())


async def enter_post_text(page, editor, text: str) -> None:
    await editor.fill(text, timeout=10000)
    for _ in range(12):
        try:
            if _normalized(await editor.inner_text(timeout=1000)) == _normalized(text):
                return
        except Exception:
            pass
        await page.wait_for_timeout(250)
    raise AutomationError("POST_TEXT_MISMATCH", "The composer text did not match the queued post. Submission was stopped.")


async def post_to_facebook(page, job: dict, on_step: Callable[[str], None] = lambda _step: None) -> dict:
    submitted = False
    try:
        on_step("Opening Facebook group...")
        await page.goto(job["groupUrl"], wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(1500)
        body = await page.locator("body").inner_text(timeout=10000)
        if CHECKPOINT.search(f"{page.url} {body}"):
            raise AutomationError("CHECKPOINT_DETECTED", "Facebook requires a security check.", security=True)
        if CAPTCHA.search(body):
            raise AutomationError("CAPTCHA_DETECTED", "Facebook displayed a CAPTCHA.", security=True)
        login = await first_visible(page, [
            page.locator('input[name="email"]'),
            page.get_by_role("button", name=re.compile(r"log in", re.I)),
        ], 1000)
        if login:
            raise AutomationError("LOGIN_REQUIRED", "Open Browser / Login and sign in first.", security=True)
        if re.search(r"content isn't available|page isn't available", body, re.I):
            raise AutomationError("GROUP_NOT_FOUND", "The group is unavailable or inaccessible.")
        on_step("Finding composer...")
        trigger = await first_visible(page, [
            page.get_by_role("button", name=re.compile(r"write something|create (a )?post|what['’]s on your mind", re.I)),
            page.get_by_text(re.compile(r"write something|what['’]s on your mind", re.I), exact=False),
        ])
        if not trigger:
            raise AutomationError("COMPOSER_NOT_FOUND", "Could not locate the group composer.")
        await trigger.click()
        dialog = page.get_by_role("dialog")
        editor = await first_visible(page, dialog.locator('[contenteditable="true"]:not([aria-label^="Comment" i]):not([aria-placeholder^="Comment" i])'))
        if not editor:
            raise AutomationError("COMPOSER_NOT_FOUND", "Composer opened but its text field was not found.")
        on_step("Entering post text...")
        await enter_post_text(page, editor, job["postText"])
        post_button = await first_enabled(page, [dialog.get_by_role("button", name=re.compile(r"^(post|publish)$", re.I))])
        if not post_button:
            raise AutomationError("POST_BUTTON_NOT_FOUND", "Post button was not enabled after entering the text.")
        on_step("Submitting post...")
        await post_button.click()
        submitted = True
        on_step("Verifying post...")
        try:
            dialog_visible = await editor.is_visible()
        except Exception:
            dialog_visible = False
        try:
            text_visible = await page.get_by_text(job["postText"][:80], exact=False).first.is_visible()
        except Exception:
            text_visible = False
        if dialog_visible and not text_visible:
            raise AutomationError("POST_UNCERTAIN", "Submission was clicked but confirmation could not be verified.")
        return {"status": "posted"}
    except AutomationError:
        raise
    except Exception as error:
        if submitted:
            raise AutomationError("POST_UNCERTAIN", f"Browser error after submission: {error}") from error
        raise
