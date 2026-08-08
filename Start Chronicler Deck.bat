@echo off
REM Start Chronicler Deck.bat -- COWORK_BRIEF_unified_app.md Task 5.
REM
REM A shortcut, not a frozen binary (deliberate; PyInstaller is its own round
REM and its own class of pain -- see the brief). Double-click this file, or
REM make a desktop shortcut that points at it.
REM
REM Uses "python", not "pythonw", ON PURPOSE: if the window fails to open (no
REM GTK/Qt backend), the fallback is a printed loopback URL and a running
REM server -- "never a silent exit" only holds if a console is actually here
REM to print into. pythonw would swallow that fallback silently, which is
REM exactly the failure mode this line exists to avoid.
REM
REM Prefers .venv\Scripts\python.exe over the bare "python" on PATH, ON
REM PURPOSE: double-clicking this file from Explorer opens a fresh cmd.exe
REM with no venv activated, so a bare "python" resolves to whatever is
REM first on the system PATH -- not necessarily the venv the FastAPI/
REM uvicorn/pywebview extras were installed into. A real install was
REM missed by exactly this: `pip install -e .[desktop]` inside an
REM activated .venv succeeded, but the shortcut still ran against a
REM different, unrelated Python that had none of it.
cd /d "%~dp0"
set "L5GN_PY=python"
if exist "%~dp0.venv\Scripts\python.exe" set "L5GN_PY=%~dp0.venv\Scripts\python.exe"
"%L5GN_PY%" run.py window
if errorlevel 1 (
  echo.
  echo Chronicler Deck exited with an error -- see the output above.
  echo Ran with: %L5GN_PY%
  pause
)
