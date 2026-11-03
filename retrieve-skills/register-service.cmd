@echo off
:: ============================================================
:: ONE-TIME SETUP: Run as Administrator to register skill-router
:: Right-click this file > "Run as administrator"
:: ============================================================

set NSSM=C:\Users\user\.pi\bin\nssm.exe
set SVC=skill-router
set PYTHON=F:\Python\mcp\retrieve-skills\Scripts\python.exe
set PYTHONW=F:\Python\mcp\retrieve-skills\Scripts\pythonw.exe
set APPDIR=C:\Users\user\.skills\retrieve-skills

:: Clean slate
%NSSM% stop %SVC% >nul 2>&1
%NSSM% remove %SVC% confirm >nul 2>&1
timeout /t 2 /nobreak >nul

:: Install
%NSSM% install %SVC% %PYTHON% "server.py"
if %ERRORLEVEL% neq 0 (echo FAILED: Are you running as Administrator? & pause & exit /b 1)

:: Configure
%NSSM% set %SVC% AppDirectory %APPDIR%
%NSSM% set %SVC% AppEnvironmentExtra PYTHONIOENCODING=utf-8 PYTHONUTF8=1 SSLKEYLOGFILE= SKILL_STORE=C:\Users\user\.skills HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HOME=F:\hf_cache\huggingface HOME=C:\Users\user USERPROFILE=C:\Users\user NLTK_DATA=c:\users\user\py310\nltk_data
%NSSM% set %SVC% AppExit Default Restart
%NSSM% set %SVC% AppRestartDelay 5000
%NSSM% set %SVC% AppStdout %APPDIR%\service_stdout.log
%NSSM% set %SVC% AppStderr %APPDIR%\service_stderr.log
%NSSM% set %SVC% AppStdoutCreationDisposition 4
%NSSM% set %SVC% AppStderrCreationDisposition 4
%NSSM% set %SVC% AppRotateFiles 1
%NSSM% set %SVC% AppRotateBytes 5242880
%NSSM% set %SVC% DisplayName "Skill Router MCP"
%NSSM% set %SVC% Description "Retrieve-skills MCP server on :8765. Auto-restarts on crash."
%NSSM% set %SVC% Start SERVICE_AUTO_START

:: Also register the health probe as a Scheduled Task (every 5 min)
schtasks /delete /tn "skill-router-probe" /f >nul 2>&1
schtasks /create /tn "skill-router-probe" /tr "\"%PYTHONW%\" \"%APPDIR%\health_probe.py\"" /sc minute /mo 5 /ru "user" /f

:: Start the service
%NSSM% start %SVC%

echo.
echo ============================================================
echo  DONE. Service "skill-router" registered and started.
echo  Health probe scheduled every 5 minutes.
echo.
echo  Verify now:
echo    curl http://127.0.0.1:8765/health
echo  Verify probe:
echo    schtasks /query /tn skill-router-probe
echo ============================================================
pause
