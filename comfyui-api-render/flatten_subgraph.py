#!/usr/bin/env python3
"""
Flatten one branch of a ComfyUI UI/subgraph workflow into API ("prompt") format.

ComfyUI's /prompt endpoint needs the flattened API graph; a saved .json workflow that
contains SubgraphNodes is in UI format and must be flattened first (the frontend normally
does this via graphToPrompt). This reproduces that for ONE subgraph-instance branch so a
headless API render is possible.

Usage:
  python3 flatten_subgraph.py \
      --workflow "WF.json" --oi object_info.json \
      --instance 459 --output 458 --out api_prompt.json

  --instance : top-level node id of the SubgraphNode instance to flatten (e.g. the i2v box)
  --output   : top-level output node id that consumes the instance's output (e.g. SaveVideo)
  --oi       : object_info.json  (curl -s http://HOST:8188/object_info -o object_info.json)

Then POST api_prompt.json to /prompt, read node_errors (structural) and, if it queues,
/history/<prompt_id> for execution_error (semantic). Fix and repeat until status==success.

Known widget gotchas this handles (learned the hard way):
  * slot names come from each node's OWN inputs[] array, NOT object_info order
    (dynamic-input nodes like ComfyMathExpression use names such as "values.a")
  * combos assigned by option-membership (order-robust for custom nodes)
  * scalars assigned positionally in object_info order, CONSUMING converted-widget
    placeholders that remain in widgets_values
  * union scalar types ("FLOAT,INT") count as scalar widgets for placeholder alignment
  * v3 DynamicCombo (COMFY_DYNAMICCOMBO_V3, e.g. ResizeImageMaskNode.resize_type,
    SaveVideo.codec) uses FLAT keys: parent="<option string>" + "parent.subinput"=value
"""
import json, argparse

ap = argparse.ArgumentParser()
ap.add_argument("--workflow", required=True)
ap.add_argument("--oi", required=True)
ap.add_argument("--instance", type=int, required=True, help="top-level SubgraphNode instance id")
ap.add_argument("--output", type=int, required=True, help="top-level output node id (e.g. SaveVideo)")
ap.add_argument("--out", default="api_prompt.json")
A = ap.parse_args()

d = json.load(open(A.workflow)); oi = json.load(open(A.oi))
top = {n["id"]: n for n in d["nodes"]}
top_links = {l[0]: l for l in d["links"]}
SKIP = {"Note", "MarkdownNote"}

def oi_inputs(ct):
    inp = oi.get(ct, {}).get("input", {}); out = []
    for grp in ("required", "optional"):
        for name, spec in inp.get(grp, {}).items():
            out.append((name, spec))
    return out
def is_combo(spec): return isinstance(spec[0], list) or spec[0] == "COMBO"
def combo_opts(spec):
    if isinstance(spec[0], list): return spec[0]
    if spec[0] == "COMBO" and len(spec) > 1 and isinstance(spec[1], dict):
        return spec[1].get("options", [])
    return []
def is_scalar(spec):
    t = spec[0]
    if not isinstance(t, str): return False
    parts = [x.strip() for x in t.split(",")]
    return len(parts) >= 1 and all(x in ("INT","FLOAT","STRING","BOOLEAN","NUMBER") for x in parts)

def assign_widgets(ct, slot_names, wv, node_inputs):
    wv = list(wv or []); specs = oi_inputs(ct); used = [False]*len(wv)
    # combos by membership (consume even if converted-to-slot)
    for name, spec in specs:
        if not is_combo(spec): continue
        for i, v in enumerate(wv):
            if not used[i] and v in combo_opts(spec):
                used[i] = True
                if name not in slot_names: node_inputs[name] = v
                break
    # v3 DynamicCombo: option-key string (flat) + prefixed sub-inputs
    for name, spec in specs:
        if spec[0] != "COMFY_DYNAMICCOMBO_V3": continue
        opts = {o.get("key"): o for o in (spec[1].get("options", []) if len(spec) > 1 else [])}
        for i, v in enumerate(wv):
            if not used[i] and v in opts:
                used[i] = True
                if name not in slot_names:
                    node_inputs[name] = v
                    for subname, subspec in opts[v].get("inputs", {}).get("required", {}).items():
                        for j in range(len(wv)):
                            if not used[j]:
                                sv = wv[j]
                                if subspec[0] == "INT":
                                    try: sv = int(sv)
                                    except: pass
                                elif subspec[0] == "FLOAT":
                                    try: sv = float(sv)
                                    except: pass
                                node_inputs[f"{name}.{subname}"] = sv; used[j] = True; break
                break
    # scalars positional in object_info order (consumes converted placeholders)
    rem = [i for i in range(len(wv)) if not used[i]]; ri = 0
    for name, spec in specs:
        if not is_scalar(spec): continue
        if ri < len(rem):
            v = wv[rem[ri]]; ri += 1
            if spec[0] == "INT":
                try: v = int(v)
                except: pass
            elif spec[0] == "FLOAT":
                try: v = float(v)
                except: pass
            if name not in slot_names: node_inputs[name] = v

# ---- resolve the subgraph instance ----
inst = top[A.instance]
sg = [s for s in d.get("definitions", {}).get("subgraphs", []) if s["id"] == inst["type"]][0]
sgn = {n["id"]: n for n in sg["nodes"]}
sg_links = sg["links"]  # dicts: id, origin_id, origin_slot, target_id, target_slot, type
inst_in = {ii["name"]: ii for ii in inst.get("inputs", [])}
wv_inst = list(inst.get("widgets_values", []))
wired = {l["origin_slot"] for l in sg_links if l["origin_id"] == -10}  # -10 = subgraph input boundary
def sg_is_widget(si): return si.get("type") in ("STRING","INT","FLOAT","BOOLEAN","COMBO")

resolved = {}; wvi = 0
for idx, si in enumerate(sg["inputs"]):
    ext = inst_in.get(si["name"]); has_ext = ext is not None and ext.get("link") is not None
    if has_ext:
        l = top_links[ext["link"]]; resolved[idx] = ("LINK", [l[1], l[2]])
        if sg_is_widget(si) and idx in wired and wvi < len(wv_inst): wvi += 1
    elif sg_is_widget(si) and idx in wired:
        if wvi < len(wv_inst): resolved[idx] = ("LIT", wv_inst[wvi]); wvi += 1

BASE = A.instance * 1000
def nid(i): return str(BASE + i)

inbound = {}
for l in sg_links:
    k = (l["target_id"], l["target_slot"])
    if l["origin_id"] == -10: inbound[k] = ("BND", l["origin_slot"])
    elif l["origin_id"] == -20: pass  # -20 = subgraph output boundary
    else: inbound[k] = ("N", [nid(l["origin_id"]), l["origin_slot"]])

prompt = {}
SUBKEY = {"scale longer dimension":"longer_size","scale shorter dimension":"shorter_size",
          "scale by multiplier":"multiplier","scale width":"width","scale height":"height",
          "scale total pixels":"megapixels","scale to multiple":"multiple"}
for iid, n in sgn.items():
    ct = n.get("type")
    if ct in SKIP or n.get("mode") in (2, 4): continue
    node_inputs = {}
    for si, inp in enumerate(n.get("inputs", []) or []):
        k = (iid, si)
        if k in inbound:
            src = inbound[k]; nm = inp.get("name")
            if src[0] == "N": node_inputs[nm] = src[1]
            else:
                r = resolved.get(src[1])
                if r is None: continue
                node_inputs[nm] = [str(r[1][0]), r[1][1]] if r[0] == "LINK" else r[1]
    assign_widgets(ct, set(node_inputs), n.get("widgets_values"), node_inputs)
    prompt[nid(iid)] = {"class_type": ct, "inputs": node_inputs}

# ---- top-level feeder nodes referenced by resolved external LINKs ----
def add_top(tid, seen):
    if tid in seen: return
    seen.add(tid)
    n = top.get(tid)
    if n is None or n.get("type") in SKIP: return
    ct = n.get("type"); node_inputs = {}
    for si, inp in enumerate(n.get("inputs", []) or []):
        if inp.get("link") is not None:
            l = top_links[inp["link"]]; node_inputs[inp.get("name")] = [str(l[1]), l[2]]
    assign_widgets(ct, set(node_inputs), n.get("widgets_values"), node_inputs)
    prompt[str(tid)] = {"class_type": ct, "inputs": node_inputs}
    for inp in n.get("inputs", []) or []:
        if inp.get("link") is not None: add_top(top_links[inp["link"]][1], seen)
seen = set()
for r in resolved.values():
    if r[0] == "LINK": add_top(r[1][0], seen)

# ---- output node (e.g. SaveVideo): its VIDEO/IMAGE input <- subgraph output ----
out_src = None
for l in sg_links:
    if l["target_id"] == -20: out_src = [nid(l["origin_id"]), l["origin_slot"]]
onode = top[A.output]; oct = onode["type"]; node_inputs = {}
for inp in onode.get("inputs", []) or []:
    nm = inp.get("name")
    if inp.get("link") is not None and inp["link"] in top_links:
        l = top_links[inp["link"]]
        # the link from the instance -> this input becomes the subgraph's real output
        node_inputs[nm] = out_src if l[1] == A.instance else [str(l[1]), l[2]]
assign_widgets(oct, set(node_inputs), onode.get("widgets_values"), node_inputs)
prompt[str(A.output)] = {"class_type": oct, "inputs": node_inputs}

json.dump(prompt, open(A.out, "w"), indent=1)
print(f"wrote {A.out}: {len(prompt)} nodes | output {oct} <- {out_src}")
