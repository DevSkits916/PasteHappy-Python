@echo off
setlocal
title PasteHappy Setup and Launcher

cd /d "%~dp0"

echo.
echo ========================================
echo   PasteHappy - Deploy and Open
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python was not found.
  echo Install Python 3.11 or newer, then run this file again.
  goto :failed
)

where npm >nul 2>nul
if errorlevel 1 (
  echo ERROR: npm was not found.
  echo Install the current Node.js LTS release, then run this file again.
  goto :failed
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating the Python environment...
  python -m venv .venv
  if errorlevel 1 goto :failed
) else (
  echo [1/5] Python environment is ready.
)

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"

echo [2/5] Installing Python dependencies...
"%PYTHON_EXE%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :failed

echo [3/5] Installing the Playwright browser...
"%PYTHON_EXE%" -m playwright install chromium
if errorlevel 1 goto :failed

echo [4/5] Installing and building the web interface...
call npm install --ignore-scripts
if errorlevel 1 goto :failed
call npm run build
if errorlevel 1 goto :failed

echo [5/5] Starting PasteHappy...
powershell.exe -NoProfile -Command "try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:4173/api/status' -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>nul
if not errorlevel 1 (
  echo PasteHappy is already running.
  goto :open_app
)

start "PasteHappy Server" /min "%PYTHON_EXE%" app.py

powershell.exe -NoProfile -Command "$deadline = (Get-Date).AddSeconds(30); while ((Get-Date) -lt $deadline) { try { $response = Invoke-WebRequest -Uri 'http://127.0.0.1:4173/api/status' -UseBasicParsing -TimeoutSec 2; if ($response.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1" >nul 2>nul
if errorlevel 1 (
  echo ERROR: PasteHappy did not start within 30 seconds.
  echo Check the minimized PasteHappy Server window for details.
  goto :failed
)

:open_app
echo Opening http://localhost:4173 ...
start "" "http://localhost:4173"
echo.
echo PasteHappy is ready. Keep the PasteHappy Server window running.
exit /b 0

:failed
echo.
echo Deployment failed. Review the error above, then run this file again.
pause
exit /b 1
