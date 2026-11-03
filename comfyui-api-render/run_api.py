#!/usr/bin/env python3
"""
POST a flattened API prompt to ComfyUI and poll to completion.

Usage:
  python3 run_api.py --prompt api_prompt.json [--host http://localhost:8188] [--timeout 1800]

Prints, in order:
  * node_errors (structural validation) -> fix the flatten and re-run
  * execution_error (semantic, from /history) -> fix the offending node and re-run
  * success + the output file(s) reported by the terminal node

Exit codes: 0 success, 2 pig.py/CUDA crash (not seen once --disable-pinned-memory is on),
3 execution error, 4 structural node_errors, 5 timeout.
"""
import json, time, argparse, urllib.request, urllib.error

ap = argparse.ArgumentParser()
ap.add_argument("--prompt", required=True)
ap.add_argument("--host", default="http://localhost:8188")
ap.add_argument("--timeout", type=int, default=1800)
ap.add_argument("--client", default="skill-run")
A = ap.parse_args()

def post(path, obj):
    req = urllib.request.Request(A.host + path, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

def get(path):
    try:
        return json.loads(urllib.request.urlopen(A.host + path, timeout=30).read().decode())
    except Exception:
        return None

p = json.load(open(A.prompt))
resp = post("/prompt", {"prompt": p, "client_id": A.client})
ne = resp.get("node_errors", {})
if ne:
    print("STRUCTURAL node_errors:", len(ne))
    for k, v in ne.items():
        ct = p.get(k, {}).get("class_type", "?")
        for er in v.get("errors", []):
            print(f"  {k} ({ct}) [{er.get('extra_info',{}).get('input_name')}]: {er.get('details')}")
    raise SystemExit(4)
pid = resp.get("prompt_id")
print("queued", pid, "(0 node_errors) — polling…")

t0 = time.time()
while time.time() - t0 < A.timeout:
    h = get(f"/history/{pid}")
    if h:
        for v in h.values():
            st = v.get("status", {})
            if st.get("status_str") == "success":
                print("SUCCESS")
                for nid, out in v.get("outputs", {}).items():
                    for kind, items in out.items():
                        for it in (items or []):
                            if isinstance(it, dict) and it.get("filename"):
                                print(f"  {nid}: {it.get('subfolder','')}/{it['filename']}")
                raise SystemExit(0)
            for m in st.get("messages", []):
                if m[0] == "execution_error":
                    e = m[1]
                    print("EXECUTION_ERROR node", e.get("node_id"), e.get("node_type"))
                    print(" ", (e.get("exception_message") or "")[:400])
                    raise SystemExit(3)
    time.sleep(6)
print("TIMEOUT after", A.timeout, "s")
raise SystemExit(5)
