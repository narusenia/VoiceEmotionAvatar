@echo off
REM Build the VEA .unitypackage into dist\ (no Unity install required).
cd /d "%~dp0"
python scripts\build_unitypackage.py %*
pause
