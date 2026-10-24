@echo off
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
python -u autonomous_review.py --hours 9 %*
if errorlevel 1 echo Run stopped. Read the error above; progress is saved when available.
pause
