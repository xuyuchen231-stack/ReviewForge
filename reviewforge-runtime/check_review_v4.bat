@echo off
cd /d "%~dp0"
chcp 65001 >nul
py reviewforge_v4.py preflight
if exist workspace\reports\final_audit.json py reviewforge_v4.py audit --minimum 60
pause
