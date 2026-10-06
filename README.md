<img width="1231" height="637" alt="Screenshot 2026-10-06 003414" src="https://github.com/user-attachments/assets/e0d6b673-48ef-4dce-b240-1b2114f14231" />




## Windows executable

Download `PasteHappy.exe` from [GitHub releases](https://github.com/DevSkits916/PasteHappy-Python/releases) and double-click it. The dashboard opens automatically. Keep the console window open; press Ctrl+C to stop. Python and Node.js are not required. Install Microsoft Edge or Google Chrome for Facebook automation, then log in manually through PasteHappy.




Maunal Mode

1. Open the main PasteHappy window.
2. Select **Import CSV**.
3. Review or edit the imported post text.
4. Choose **Copy & Open** for a row.
5. Paste and publish the message in Facebook.
6. Return to PasteHappy and choose **Mark Posted** or **Skip**.

Manual rows are stored in the current browser's `localStorage`. Clearing site data or changing browsers, profiles, or origins creates a different manual session.

## Automation mode

1. Select **Open Playwright Automation**.
2. Allow popups for PasteHappy if the second window is blocked.
3. Select **Import CSV** in the automation tab to import directly into its queue.
4. Alternatively, import and review rows in the manual window, then select **Queue Manual CSV**.
5. Configure the delay, cooldown, job limit, and stop behavior.
6. Complete the initial Facebook login in visible mode.
7. Select **Start**.

The automation window reads the manual session when it opens. Reload it after changing manual rows.

The manual queue and automation queue are separate. An automated result does not automatically change the matching manual row.

### Run controls

- **Start:** process pending jobs using the selected settings.
- **Pause:** pause before another job begins.
- **Resume:** continue a paused run.
- **Stop:** request that the worker stop.
- **Skip Current & Continue:** skip the active job and close its browser work.
- **Clear Automation Queue:** remove automation jobs and close the Playwright browser.

## Facebook login and headless mode

Use visible mode for the initial login:

1. Leave **Run browser headless** unchecked.
2. Select **Open Visible Browser / Login**.
3. Log in and complete any security prompts manually.
4. Leave the managed browser available while running a visible queue.

The worker uses Playwright’s installed Chromium by default. The session is saved under `.browser-profile` and reused. This directory contains sensitive account session data; never commit, upload, or share it.

After a successful visible login, you may close the Playwright browser, enable **Run browser headless**, and start a later queue. Mode changes are blocked while a managed browser is open.

Headless mode cannot complete interactive login, CAPTCHA, two-factor authentication, or checkpoints. It does not bypass Facebook security controls.

## Chrome extension: generate a Facebook groups CSV

https://github.com/DevSkits916/FBGroups2CSV



Created by [DevSkits916](https://github.com/DevSkits916).

Repository: [PasteHappy-Python](https://github.com/DevSkits916/PasteHappy-Python).
