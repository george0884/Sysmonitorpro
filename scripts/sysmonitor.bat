@echo off
cd /d "%~dp0.."
python sysmonitorpro.py %*
if errorlevel 1 pause
