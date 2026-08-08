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
cd /d "%~dp0"
python run.py window
if errorlevel 1 (
  echo.
  echo Chronicler Deck exited with an error -- see the output above.
  pause
)
