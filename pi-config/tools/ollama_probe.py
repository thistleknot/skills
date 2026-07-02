#!/usr/bin/env python3
"""
ollama_probe.py — read-only diagnostic for how an Ollama model behaves across
the two endpoints (native /api/chat vs OpenAI-compat /v1/chat/completions) on
the three axes that decide cross-harness compatibility:

  Axis 1  endpoint -> where does reasoning land? (native `thinking` vs /v1 `reasoning`
          vs leaked literal <think> in content)
  Axis 2  thinking activation -> does toggling think on/off actually move the split?
  Axis 3  roles + tools -> is `system` accepted, is `developer` accepted, do tool-calls format?

Pure stdlib. Does NOT modify anything. Usage:
    python ollama_probe.py <model-id> [<model-id> ...] [--host localhost:11434]
"""
import sys, json, time, urllib.request, urllib.error

HOST = "localhost:11434"
TIMEOUT = 240
NUM_PREDICT = 96  # cap generation so reasoning models don't run away; we only need WHERE output lands

PROMPT = "What is 17*23? Answer in one short sentence."
TOOL_PROMPT = "Use the add tool to compute 2 + 3."
ADD_TOOL = {
    "type": "function",
    "function": {
        "name": "add",
        "description": "Add two integers",
        "parameters": {
            "type": "object",
            "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
            "required": ["a", "b"],
        },
    },
}


def post(path, payload):
    url = f"http://{HOST}{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = json.loads(r.read().decode())
        return {"ok": True, "secs": round(time.time() - t0, 1), "body": body}
    except urllib.error.HTTPError as e:
        return {"ok": False, "secs": round(time.time() - t0, 1), "err": f"HTTP {e.code}", "detail": e.read().decode()[:200]}
    except Exception as e:
        return {"ok": False, "secs": round(time.time() - t0, 1), "err": str(e)[:200]}


def has_think_tag(s):
    return bool(s) and "<think>" in s


def native_chat(model, think, messages=None, tools=None):
    payload = {
        "model": model,
        "messages": messages or [{"role": "user", "content": PROMPT}],
        "stream": False,
        "think": think,
        "options": {"num_predict": NUM_PREDICT},
    }
    if tools:
        payload["tools"] = tools
    return post("/api/chat", payload)


def v1_chat(model, messages=None, tools=None, reasoning_effort=None):
    payload = {
        "model": model,
        "messages": messages or [{"role": "user", "content": PROMPT}],
        "stream": False,
        "max_tokens": NUM_PREDICT,
    }
    if tools:
        payload["tools"] = tools
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    return post("/v1/chat/completions", payload)


def summarize_native(r):
    if not r["ok"]:
        return f"ERR {r.get('err')}"
    msg = r["body"].get("message", {})
    thinking = msg.get("thinking")
    content = msg.get("content", "")
    tc = msg.get("tool_calls")
    parts = []
    parts.append(f"thinking_field={'Y(%d)' % len(thinking) if thinking else 'n'}")
    parts.append(f"content={'<empty>' if not content else str(len(content))+'c'}")
    parts.append(f"leak<think>={'Y' if has_think_tag(content) else 'n'}")
    if tc is not None:
        parts.append(f"tool_calls={len(tc)}")
    parts.append(f"{r['secs']}s")
    return " ".join(parts)


def summarize_v1(r):
    if not r["ok"]:
        return f"ERR {r.get('err')}"
    ch = r["body"].get("choices", [{}])[0]
    msg = ch.get("message", {})
    reasoning = msg.get("reasoning")
    content = msg.get("content", "")
    tc = msg.get("tool_calls")
    parts = []
    parts.append(f"reasoning_field={'Y(%d)' % len(reasoning) if reasoning else 'n'}")
    parts.append(f"content={'<empty>' if not content else str(len(content))+'c'}")
    parts.append(f"leak<think>={'Y' if has_think_tag(content) else 'n'}")
    if tc is not None:
        parts.append(f"tool_calls={len(tc)}")
    parts.append(f"finish={ch.get('finish_reason')}")
    parts.append(f"{r['secs']}s")
    return " ".join(parts)


def role_check(model, role):
    # cheap probe: does the endpoint accept this role without erroring?
    r = v1_chat(model, messages=[{"role": role, "content": "x"}, {"role": "user", "content": "hi"}])
    if r["ok"]:
        return "accepted"
    return r.get("err", "err")


def probe(model):
    print(f"\n===== {model} =====")
    print(f"[native /api/chat think=ON ] {summarize_native(native_chat(model, True))}")
    print(f"[native /api/chat think=OFF] {summarize_native(native_chat(model, False))}")
    print(f"[/v1 chat default          ] {summarize_v1(v1_chat(model))}")
    print(f"[/v1 chat reasoning=low    ] {summarize_v1(v1_chat(model, reasoning_effort='low'))}")
    print(f"[native tool-call          ] {summarize_native(native_chat(model, True, messages=[{'role':'user','content':TOOL_PROMPT}], tools=[ADD_TOOL]))}")
    print(f"[/v1 tool-call             ] {summarize_v1(v1_chat(model, messages=[{'role':'user','content':TOOL_PROMPT}], tools=[ADD_TOOL]))}")
    print(f"[role system /v1           ] {role_check(model, 'system')}")
    print(f"[role developer /v1        ] {role_check(model, 'developer')}")


def main():
    global HOST
    args = [a for a in sys.argv[1:]]
    if "--host" in args:
        i = args.index("--host")
        HOST = args[i + 1]
        del args[i:i + 2]
    if not args:
        print("usage: python ollama_probe.py <model-id> [model-id ...] [--host host:port]")
        sys.exit(1)
    print(f"host={HOST}  num_predict={NUM_PREDICT}  prompt={PROMPT!r}")
    for m in args:
        probe(m)


if __name__ == "__main__":
    main()
