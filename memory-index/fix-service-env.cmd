@echo off
set NSSM=C:\Users\user\.pi\bin\nssm.exe
%NSSM% stop mem-server
timeout /t 2 /nobreak >nul
%NSSM% set mem-server AppParameters "C:\Users\user\.skills\memory-index\mem_server.py"
%NSSM% set mem-server AppDirectory "C:\Users\user\.skills\memory-index"
%NSSM% set mem-server AppEnvironmentExtra PYTHONIOENCODING=utf-8 PYTHONUTF8=1 MEM_DIR=C:\Users\user\memory-bank HOME=C:\Users\user USERPROFILE=C:\Users\user
timeout /t 1 /nobreak >nul
%NSSM% start mem-server
timeout /t 3 /nobreak >nul
%NSSM% status mem-server
%NSSM% get mem-server AppEnvironmentExtra
pause
