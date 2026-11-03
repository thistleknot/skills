@echo off
rem run-anneal.cmd - invoked by the mem-anneal scheduled task (runs as SYSTEM).
rem Evicts stale, under-recalled Chroma log bits and appends to logs\anneal.log.
setlocal
if not exist "%~dp0logs" mkdir "%~dp0logs"
echo ---- %date% %time% anneal ---->> "%~dp0logs\anneal.log"
"C:\Users\user\py310\Scripts\python.exe" "%~dp0mem.py" --memory-dir "C:\Users\user\memory-bank" anneal >> "%~dp0logs\anneal.log" 2>&1
