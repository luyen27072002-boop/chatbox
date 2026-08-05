@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Creating Python environment...
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)

if not exist .venv\Scripts\python.exe (
  echo Could not create .venv. Install Python 3.12 and try again.
  pause
  exit /b 1
)

.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install packages.
  pause
  exit /b 1
)

if not exist .env copy .env.example .env >nul
.venv\Scripts\python.exe app.py
pause
