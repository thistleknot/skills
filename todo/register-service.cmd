@echo off
:: ONE-TIME: Run as Administrator to register todo-mcp as a Windows Service.
:: Right-click > Run as administrator

set NSSM=C:\Users\user\.pi\bin\nssm.exe
set SVC=todo-mcp
set PYTHON=F:\Python\mcp\todo\Scripts\python.exe
set APPDIR=C:\Users\user\.mcp\todo

%NSSM% stop %SVC% >nul 2>&1
%NSSM% remove %SVC% confirm >nul 2>&1
timeout /t 2 /nobreak >nul

%NSSM% install %SVC% %PYTHON% "todo_mcp.py --port 8056"
if %ERRORLEVEL% neq 0 (echo FAILED: Are you running as Administrator? & pause & exit /b 1)

%NSSM% set %SVC% AppDirectory %APPDIR%
%NSSM% set %SVC% AppEnvironmentExtra PYTHONIOENCODING=utf-8 PYTHONUTF8=1 SSLKEYLOGFILE= HOME=C:\Users\user USERPROFILE=C:\Users\user
%NSSM% set %SVC% AppExit Default Restart
%NSSM% set %SVC% AppRestartDelay 3000
%NSSM% set %SVC% AppStdout %APPDIR%\service_stdout.log
%NSSM% set %SVC% AppStderr %APPDIR%\service_stderr.log
%NSSM% set %SVC% AppStdoutCreationDisposition 4
%NSSM% set %SVC% AppStderrCreationDisposition 4
%NSSM% set %SVC% AppRotateFiles 1
%NSSM% set %SVC% AppRotateBytes 5242880
%NSSM% set %SVC% DisplayName "Todo MCP"
%NSSM% set %SVC% Description "Todo MCP server on :8056. Auto-restarts on crash."
%NSSM% set %SVC% Start SERVICE_AUTO_START

%NSSM% start %SVC%

echo.
echo === Done: todo-mcp service registered and started ===
echo Verify: curl http://127.0.0.1:8056/health
pause
