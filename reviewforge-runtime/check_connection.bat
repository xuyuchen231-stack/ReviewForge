@echo off
cd /d "%~dp0"
py check_connection.py
if errorlevel 1 (
  echo.
  echo Connection test failed. See message above.
) else (
  echo.
  echo Configuration and API connection successful.
)
pause
