<img width="1231" height="637" alt="Screenshot 2026-10-06 003414" src="https://github.com/user-attachments/assets/e0d6b673-48ef-4dce-b240-1b2114f14231" />


# PasteHappy + Playwright


PasteHappy is a mobile-friendly Facebook group posting assistant with two workspaces:

- **Manual window:** import a CSV, review or edit posts, copy text, open a group, and track progress.
- **Automation window:** queue the imported rows, configure pacing, run Playwright, and monitor results.

The application uses a Python backend with Flask, Waitress, and Python Playwright. The responsive interface is built with React, Vite, and Tailwind.

> Use PasteHappy only for content you are allowed to publish. Respect group rules and Facebook's terms. Facebook can change its UI or request security checks at any time. Review an `uncertain` result manually before retrying to avoid duplicate posts.

## Features

### Manual workspace

- CSV import and sample download
- Editable post text
- Copy & Open, Mark Posted, and Skip actions
- Search, status filters, shuffle, and temporary undo
- Browser-local session persistence
- Responsive desktop and mobile layouts

### Automation workspace

- Separate dashboard window
- Persistent JSON job queue
- Persistent Facebook browser profile
- Visible or headless Playwright operation
- Delay, cooldown, and maximum-job controls
- Pause, resume, stop, retry, skip, and clear actions
- Current job, step, attempts, and error reporting
- Duplicate protection and interrupted-job recovery

## Windows executable

Download `PasteHappy.exe` from [GitHub releases](https://github.com/DevSkits916/PasteHappy-Python/releases) and double-click it. The dashboard opens automatically. Keep the console window open; press Ctrl+C to stop. Python and Node.js are not required. Install Microsoft Edge or Google Chrome for Facebook automation, then log in manually through PasteHappy.

The executable saves its queue and Facebook profile under `%LOCALAPPDATA%\PasteHappy`. Existing source-folder data is preserved and is not automatically copied into this separate profile. Manual workspace data remains in your dashboard browser's local storage.

Build from source on Windows with `.\build.ps1`. The result is `releases\PasteHappy.exe`; build dependencies are in `requirements-build.txt`. The executable serves the dashboard on localhost only.

The Windows executable uses installed Edge or Chrome; source runs use Playwright Chromium. Release downloads include `SHA256SUMS.txt` for integrity verification. The v1.0.1 executable is unsigned because a trusted publisher certificate is not configured, so Windows may display a reputation warning.

To sign a future build with a trusted code-signing certificate installed in the current user's certificate store, run `.\build.ps1 -SigningCertificateThumbprint YOUR_CERTIFICATE_THUMBPRINT`. The build timestamps and verifies the signature before generating the checksum. Signing does not guarantee that a new download will immediately have SmartScreen reputation.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer to build the React frontend
- npm
- Git

## Windows installation

Open PowerShell:

```powershell
Set-Location ([Environment]::GetFolderPath("MyDocuments"))
git clone https://github.com/DevSkits916/PasteHappy-Python.git
Set-Location PasteHappy-Python

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium

npm install
npm run build
python app.py
```

Open <http://localhost:4173> and keep the PowerShell window running.

If PowerShell blocks the activation script, use the virtual environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
npm install
npm run build
.\.venv\Scripts\python.exe app.py
```

## Linux or WSL installation

```bash
git clone https://github.com/DevSkits916/PasteHappy-Python.git
cd PasteHappy-Python

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium

npm install
npm run build
python app.py
```

Visible login requires a working graphical desktop or WSLg session.

## Starting an existing installation

### One-click Windows launcher

Double-click `Deploy-and-Open-PasteHappy.bat` in the project folder. It will:

1. Create the Python virtual environment when needed.
2. Install the packages from `requirements.txt`.
3. Install the Playwright Chromium browser.
4. Install and build the web interface.
5. Start the Python server and open PasteHappy in your default browser.

Keep the minimized **PasteHappy Server** window running while using the app. Close that window or press `Ctrl+C` inside it to stop the server.

### Manual startup

```powershell
Set-Location "$env:USERPROFILE\Documents\PasteHappy-Python"
.\.venv\Scripts\python.exe app.py
```

The server listens on <http://localhost:4173> by default. Press `Ctrl+C` to stop it.

`npm start` is also available and runs `python app.py`, but the direct virtual-environment command guarantees the correct Python dependencies are used.

## Manual mode

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

### Statuses

| Status | Meaning |
| --- | --- |
| `pending` | Waiting to run |
| `processing` | Claimed by the worker |
| `posted` | Posting success was detected |
| `failed` | Browser or posting error |
| `blocked` | Login or security condition blocked progress |
| `uncertain` | Submission may have happened but could not be verified |
| `skipped` | Skipped by the user |

Failed, blocked, uncertain, and skipped jobs require an explicit retry.

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

The included [FBGroups2CSV.zip](FBGroups2CSV.zip) is the **Facebook Groups Exporter** Chrome extension. Its unpacked files are also available in [FBGroups2CSV/](FBGroups2CSV/).

### Install in Chrome

1. Download **FBGroups2CSV.zip** from this repository and extract it to a permanent folder. If you cloned or downloaded the whole repository, use its existing `FBGroups2CSV` folder instead.
2. Open `chrome://extensions` in Chrome and enable **Developer mode**.
3. Click **Load unpacked** and select the `FBGroups2CSV` folder containing `manifest.json` and `content.js`. Select the extracted folder, not the ZIP or the repository root.
4. Log in to Facebook in Chrome and open or refresh a Facebook Groups page. The **Groups Exporter** panel appears in the lower-right corner. You do not need to run PasteHappy to collect groups.

Keep the selected folder in place while the extension is installed. After replacing its files, click **Reload** on the extension card and refresh the Facebook tab.

### Collect groups and export CSV

1. Open a Facebook group listing or search Facebook for your topic and select the **Groups** results.
2. Click **Scan Visible** to collect group links currently loaded on the page. Scroll to load more results and scan again, or click **Auto-Scan (120s)** to scroll and scan automatically. **Auto duration** and **Scroll interval** adjust that run; click **Stop Auto-Scan** to stop early.
3. Optionally set **Min members** or **Active within** before collecting. Leave these at `0` and blank to collect without those restrictions; groups with unknown activity are excluded when an activity threshold is set. These collection filters do not remove previously saved groups. Use **Clear** first when starting a fresh collection.
4. Enable **Show list** to review results. **Sort list** controls export order, and **List filter** also limits which collected rows are exported. Groups are deduplicated by their group URL identifier, with a default limit of 5,000 collected groups.
5. Set **Format** to **CSV** and click **Export**. Chrome downloads a file named `fb-groups-YYYY-MM-DD-HH-MM-SS.csv`. **Copy** copies the selected export format to the clipboard instead.

The CSV contains `Group Name`, `Members`, `Members Num`, `Last Active`, `Privacy`, `Join Status`, `URL`, `Source URL`, and `Scanned At`. It uses UTF-8 with a BOM and quoted values for spreadsheet compatibility.

### Use the CSV in PasteHappy

PasteHappy recognizes the extension's `Group Name` and `URL` headings and ignores the extra metadata columns. The extension collects group details only; it does not generate post text.

Open the exported CSV in a spreadsheet editor, add a column named `Post`, and enter the message for each group. Save as CSV, then select **Import CSV** in PasteHappy. Alternatively, import into the manual workspace and edit each row's post text there before selecting **Queue Manual CSV**. Review names, URLs, and messages before posting.

With **Persist results** enabled, collected groups are saved in Facebook's site storage in that Chrome profile and can carry across pages and reloads. **Clear** removes the collected list. Closing the panel hides it until the page is refreshed. The extension runs on `www.facebook.com` and `m.facebook.com` URLs containing `groups`; if the panel is missing, refresh a matching page and check that the extension is enabled. Collection depends on the group links Facebook has loaded and its current page structure, so it is not guaranteed to find every group or every metadata field.

## CSV format

The importer supports UTF-8 BOMs, quoted commas, quoted newlines, and case-insensitive headings.

| Value | Accepted headings |
| --- | --- |
| Group | `Group Name`, `group_name`, `group`, `name` |
| URL | `Group URL`, `group_url`, `url`, `link` |
| Post | `Post Text`, `post_text`, `post`, `ad`, `ad text`, `message` |

```csv
Group Name,Group URL,Post
Example Community,https://www.facebook.com/groups/123456789/,"Hello neighbors"
```

## Development

Install both Python and frontend dependencies, then run:

```powershell
.\.venv\Scripts\Activate.ps1
npm run dev
```

Vite runs at <http://localhost:5173> and proxies `/api` to the Python server at <http://localhost:4173>.

| Command | Purpose |
| --- | --- |
| `python app.py` | Run the production Python server |
| `npm run dev` | Run Python and Vite development servers |
| `npm run dev:web` | Run only Vite |
| `npm run build` | Type-check and build the frontend |
| `npm test` | Run the Python test suite |
| `npm run preview` | Preview only the static frontend build |

## Configuration

The application reads environment variables directly. It does not automatically load `.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `4173` | HTTP port |
| `QUEUE_DATA_PATH` | `data/queue.json` | Persistent queue file |
| `BROWSER_PROFILE_PATH` | `.browser-profile` | Persistent Chromium profile |
| `PLAYWRIGHT_HEADLESS` | `false` | Initial browser mode |
| `PLAYWRIGHT_EXECUTABLE_PATH` | unset | Optional explicit browser executable override; defaults to Playwright Chromium |
| `DEFAULT_JOB_DELAY` | `15000` | Default delay in milliseconds |
| `MAX_JOBS_PER_RUN` | `10` | Default job limit |

PowerShell example:

```powershell
$env:PORT = "4173"
$env:PLAYWRIGHT_HEADLESS = "false"
.\.venv\Scripts\python.exe app.py
```

## Project structure

```text
app.py                    Python entry point
pastehappy/
  browser.py              Playwright lifecycle and persistent profile
  clipboard.py            Windows clipboard helper
  config.py               Environment configuration
  csv_parser.py           CSV normalization
  facebook.py             Facebook posting workflow
  queue_store.py          Atomic persistent queue
  web.py                  Flask API and frontend serving
  worker.py               Queue execution and controls
src/                      React frontend
public/                   Static assets
tests_python/             Python tests
requirements.txt          Python dependencies
data/                     Private runtime queue data
.browser-profile/         Private browser session data
dist/                     Generated frontend build
```

The older JavaScript backend is available in Git history. The current application starts from `app.py` and uses the `pastehappy` Python package.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/status` | Worker and browser status |
| GET | `/api/queue` | List jobs |
| GET | `/api/queue/:id` | Get a job |
| POST | `/api/queue/import` | Import CSV or normalized rows |
| POST | `/api/queue/start` | Start a run |
| POST | `/api/queue/pause` | Pause the worker |
| POST | `/api/queue/resume` | Resume the worker |
| POST | `/api/queue/stop` | Stop after current work yields |
| POST | `/api/queue/clear` | Clear jobs and close the browser |
| POST | `/api/queue/current/skip` | Skip the current job |
| POST | `/api/queue/:id/retry` | Retry a job |
| POST | `/api/queue/:id/skip` | Skip a job |
| POST | `/api/browser/login` | Open visible Facebook login |

## Deployment

Local Windows execution is recommended because the initial Facebook login requires an interactive browser.

`render.yaml` uses the Python runtime, installs `requirements.txt`, builds the React frontend, and installs Chromium. Hosted datacenter browsers may be challenged by Facebook, and the configured persistent disk stores the queue rather than the browser profile. Treat hosted automation as experimental.

Static hosting can serve the manual frontend, but it cannot run Flask, persist the backend queue, or launch Playwright.

Do not expose the Python server publicly without adding authentication and appropriate network controls.

## Troubleshooting

### Local connection refused

Start the Python server and keep its terminal open:

```powershell
.\.venv\Scripts\python.exe app.py
```

### Missing Python package

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Browser executable missing

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

### Automation backend offline

`npm run preview`, `npm run dev:web`, and static hosting do not start the Python API. Use `python app.py` or `npm run dev`.

### Automation window does not open

Allow popups for the PasteHappy origin and try again.

### Login, CAPTCHA, or checkpoint required

Stop the run, switch to visible mode, and resolve the prompt manually. Check the affected group before retrying.

### Uncertain posting result

Inspect the group manually before retrying. The submission may have succeeded.

### Browser profile locked

Close other browser instances using the PasteHappy profile, then restart the Python server.

## Validation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests_python -v
npm run build
```

The Python tests cover CSV normalization, queue persistence and recovery, duplicate handling, state transitions, API behavior, membership answers, composer deadlines, and worker continuation. Browser fixture tests use installed Edge/Chrome on Windows or Playwright Chromium; run `python -m playwright install chromium` if no browser is available.

## Security

- The local API has no authentication.
- Queue content is stored unencrypted in JSON.
- Facebook session data is stored in `.browser-profile`.
- Never commit profiles, credentials, `.env`, or private queue data.
- Use the application only on a trusted machine and network.
- Stop the server and managed browser when finished.

## Credits

Created by [DevSkits916](https://github.com/DevSkits916).

Repository: [PasteHappy-Python](https://github.com/DevSkits916/PasteHappy-Python).

## Joining groups and timeout

Enable **Join group before posting** to click Join Group before looking for the composer. Enter **Automatic membership answers** as one `question phrase = answer` per line. Matching is case-insensitive; the longest matching phrase wins. For multiple-choice questions use the exact option text. Optional rule acceptance handles checkboxes labelled as agreement/rules. Supported forms include labelled text fields, radio groups, native selects, and checkboxes. The worker fills supported matching questions and submits the join form automatically. It never invents missing answers. Unknown questions, unsupported forms, and administrator approval are recorded as skipped for follow-up. Answers are saved in dashboard browser local storage, not committed to the repository.

**Composer timeout** defaults to 15 seconds (1–120 configurable) and covers both locating the composer trigger and opening its text field. A timeout skips the group and continues even with Stop on failure enabled. Security checkpoints still honor the security stop setting. The **Current job** section appears at the top of the automation tab, with Start, Pause, Resume, Stop, and Clear Automation Queue directly below it. Worker events remain available through `/api/status`.

See [automation review](docs/automation-review.md) for prioritized findings and suggested features. Agreement answers default to `I agree` in the automation dashboard; edit or add question mappings as needed.

## Hosted Render deployment

The hosted service requires `DASHBOARD_PASSWORD`; sign in with username `pastehappy` and the configured password. The deployment saves initial credentials in an ignored local file under `data/`. Do not commit that file. `/healthz` is public for service health checks; the dashboard and API require authentication. Local source runs remain accessible without a password unless you set this variable.

The free Render service uses headless Chromium and ephemeral storage. Server queue and Facebook session data can be lost during restart, suspension, or redeploy. The manual workspace remains in the user's browser storage. Hosted visible login is unavailable; use the local app for interactive Facebook login and confirmed automation. For durable hosted queues/profiles, upgrade to a service with a persistent disk and configure both data and profile paths on that disk.

The worker uses event-driven visibility/enabled waits with no fixed opening or joining sleeps. Membership checks use the configured composer timeout as their total deadline. Configured inter-job delay/cooldown remain available and can be set to zero.

Clipboard mirroring is optional and off by default because Playwright fills the composer directly. When enabled, the clipboard call runs outside the browser event loop. Stop and Pause interrupt between-job pacing promptly.
