#!/usr/bin/env bash
# Detached start + health gate for skill-router. PID recorded in router.pid.
# Stop with: kill "$(cat router.pid)"  (explicit PID, never name-based kills)
set -euo pipefail
cd "$(dirname "$0")"
PORT="${SKILL_ROUTER_PORT:-8765}"

if [ -f router.pid ] && kill -0 "$(cat router.pid)" 2>/dev/null; then
  echo "already running (pid $(cat router.pid))"
  exit 0
fi

# Pin the interpreter: bare `python3` resolves to the WindowsApps Store stub,
# which exits immediately with "Python was not found".
PYTHON="${SKILL_ROUTER_PYTHON:-/c/Users/user/py310/Scripts/python.exe}"
if [ ! -x "$PYTHON" ]; then
  echo "interpreter not found: $PYTHON" >&2
  exit 1
fi

nohup "$PYTHON" server.py >> server.log 2>&1 &
echo $! > router.pid

for _ in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" > /dev/null 2>&1; then
    echo "skill-router up on 127.0.0.1:${PORT} (pid $(cat router.pid))"
    curl -fsS "http://127.0.0.1:${PORT}/health"; echo
    exit 0
  fi
  sleep 1
done
echo "health check failed after 60s; see server.log" >&2
exit 1
