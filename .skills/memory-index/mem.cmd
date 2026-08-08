@echo off
rem mem.cmd - run the memory-index CLI from anywhere.
rem Locates mem.py next to this script (%~dp0) and uses the py310 interpreter
rem that has chromadb/ollama. Override with MEM_PYTHON; falls back to PATH python.
setlocal
if defined MEM_PYTHON (
  set "PY=%MEM_PYTHON%"
) else if exist "C:\Users\user\py310\Scripts\python.exe" (
  set "PY=C:\Users\user\py310\Scripts\python.exe"
) else (
  set "PY=python"
)
"%PY%" "%~dp0mem.py" %*
exit /b %ERRORLEVEL%
