# Canonical todo-mcp process entrypoint for the current-user supervisor.
# Task Scheduler owns restart policy.
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:HOME = "C:\Users\user"
$env:USERPROFILE = "C:\Users\user"

Set-Location "C:\Users\user\.mcp\todo"
& "F:\Python\mcp\todo\Scripts\python.exe" "todo_mcp.py"
exit $LASTEXITCODE
