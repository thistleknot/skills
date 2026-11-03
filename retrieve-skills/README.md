# retrieve-skills

CURRENT disposition: the canonical runtime is `C:\Users\user\.skills\retrieve-skills`, the skill store is `C:\Users\user\.skills`, and the SQLite index is `C:\Users\user\.skills\retrieve-skills\index.db`. One current-user Scheduled Task named `retrieve-skills` owns the persistent FastMCP HTTP process at `http://127.0.0.1:8765/mcp`, with restart-on-failure enabled. NSSM remains the preferred supervisor, but installing its service requires an elevated token unavailable to this repair session. The legacy `start.ps1` watcher is not part of active supervision.

## Runtime

- `server.py` exposes `retrieve_skills` and `read_skill` over Streamable HTTP plus `/health`, `/route`, and `/reindex`.
- `router_core.py` owns skill discovery, the SQLite index, recall, reranking, gating, and session deduplication.
- `model_backends.py` owns embedding and reranking backends.
- `indexer.py` rebuilds or incrementally updates the canonical index.
- `hook.py` is the fail-open prompt hook client.

## Preferred NSSM service configuration

The following configuration is ready to apply from an elevated shell; it could not be installed from the current non-administrator session.

```text
Service:             retrieve-skills
Application:         F:\Python\mcp\retrieve-skills\Scripts\python.exe
AppParameters:       server.py
AppDirectory:        C:\Users\user\.skills\retrieve-skills
Startup:             Automatic
Environment:
  PYTHONIOENCODING=utf-8
  PYTHONUTF8=1
  HOME=C:\Users\user
  USERPROFILE=C:\Users\user
  HF_HOME=F:\hf_cache\huggingface
  SKILL_STORE=C:\Users\user\.skills
  SKILL_ROUTER_DB=C:\Users\user\.skills\retrieve-skills\index.db
  SKILL_ROUTER_PORT=8765
  SKILL_ROUTER_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
  SKILL_ROUTER_RERANK=none
  HF_HUB_OFFLINE=1
  TRANSFORMERS_OFFLINE=1
```

## Active supervisor configuration

```text
Scheduled Task:       retrieve-skills
Execute:              C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe
Arguments:            -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "C:\Users\user\.skills\retrieve-skills\launch.ps1"
WorkingDirectory:     C:\Users\user\.skills\retrieve-skills
Trigger:              Current-user logon
Restart:              999 attempts, one-minute interval
Multiple instances:   IgnoreNew
```

## Operations

Rebuild the index with the service stopped or through `POST /reindex` while it is running. Confirm liveness with `GET http://127.0.0.1:8765/health`. A client that retained a session across a server restart must reconnect once and initialize a fresh Streamable HTTP session.
