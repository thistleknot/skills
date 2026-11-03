# Canonical retrieve-skills process entrypoint for the current-user supervisor.
# This is intentionally not a watcher: Task Scheduler owns restart policy.
$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$env:HOME = "C:\Users\user"
$env:USERPROFILE = "C:\Users\user"
$env:SKILL_STORE = "C:\Users\user\.skills"
$env:SKILL_ROUTER_DB = "C:\Users\user\.skills\retrieve-skills\index.db"
$env:SKILL_ROUTER_PORT = "8765"
$env:SKILL_ROUTER_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
$env:SKILL_ROUTER_RERANK = "none"
$env:HF_HOME = "F:\hf_cache\huggingface"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"

Set-Location "C:\Users\user\.skills\retrieve-skills"
& "F:\Python\mcp\retrieve-skills\Scripts\python.exe" "server.py"
exit $LASTEXITCODE
