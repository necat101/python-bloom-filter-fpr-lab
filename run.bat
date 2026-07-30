@echo off
setlocal
cd /d "%~dp0"
python -m bloomfilter.runner %*
if errorlevel 1 exit /b 1
