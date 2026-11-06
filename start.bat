@echo off
rem Windows launcher: double-click to rebuild dashboard.html, then open it in an Edge/Chrome app window.
rem Counterpart of start.sh (macOS). Build log: %TEMP%\claude-panel-build.log
rem The URL is built in open_panel.py, not here: a path with non-ASCII chars becomes %E4%BC%9A...
rem and cmd would swallow those percent sequences.
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python 3 not found. Install it from https://www.python.org/downloads/ ^(tick "Add to PATH"^).
  pause
  exit /b 1
)

rem Rebuild first; if it fails, still open the previously generated dashboard.
%PY% build.py >"%TEMP%\claude-panel-build.log" 2>&1
if errorlevel 1 echo Build failed, opening the previous dashboard. See "%TEMP%\claude-panel-build.log"

%PY% open_panel.py
if errorlevel 1 (
  echo dashboard.html could not be opened. See "%TEMP%\claude-panel-build.log"
  pause
  exit /b 1
)
