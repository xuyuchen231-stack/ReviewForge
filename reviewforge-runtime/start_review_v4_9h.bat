@echo off
cd /d "%~dp0"
chcp 65001 >nul
py reviewforge_v4.py preflight
py reviewforge_v4.py run --hours 9 --minimum 60
pause
