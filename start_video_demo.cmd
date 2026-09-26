@echo off
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 was not found. Install Python, then reopen this file.
  pause
  exit /b 1
)
python gui\server.py --engine-only
if errorlevel 1 pause
