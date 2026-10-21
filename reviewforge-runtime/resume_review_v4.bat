@echo off
cd /d "%~dp0"
chcp 65001 >nul
py reviewforge_v4.py resume --minimum 60
pause
