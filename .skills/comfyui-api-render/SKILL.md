---
name: comfyui-api-render
description: >
  Run a ComfyUI workflow end-to-end via the HTTP API on the sd-worker build (feeding an
  input image for image-to-video), and iterate on the Docker build files until it works.
  Use when asked to headlessly render / test / prove a ComfyUI workflow (esp. subgraph
  workflows like LTX-2.5 GGUF i2v), send an image to a job via API, debug "missing node
  pack" / "Failed to fetch" / GGUF "CUDA error: invalid argument" (pig.py) crashes, or
  bake a node/flag/fix into sd-worker:latest. Covers: starting the container correctly,
  the ENTRYPOINT-drops-flags gotcha, flattening subgraph workflows to API prompt format,
  and the POST → node_errors → /history execution_error fix loop.
---

# ComfyUI API render + build iteration (sd-worker)

Prove a ComfyUI workflow works by actually rendering it via the API, and fix whatever
blocks it — in the workflow flatten OR in the Docker build files. **Done = a real output
file on disk** (`status_str: "success"` in `/history` AND the file present), never "should
work".

## The build (know this first)
- Production image: **`sd-worker:latest`**. Canonical repo: **`/home/user/ComfyUI/comfyui-dockerfiles/`**
  (NOT the parent dir). 3-stage build via `build.sh`:
  `Dockerfile.base → ml-base:cu126-pt26 → Dockerfile.custom_nodes → custom-nodes-ready:cu126-pt26
  → Dockerfile.comfyui → sd-worker:staging`, then `docker tag … sd-worker:latest`.
- Iterate on stage 3 only (fast, no full rebuild):
  `DOCKER_BUILDKIT=1 docker build -f Dockerfile.comfyui --build-arg BASE_IMAGE=custom-nodes-ready:cu126-pt26 -t sd-worker:staging comfyui-dockerfiles/`
  then `docker tag sd-worker:staging sd-worker:latest`.
- **torch is pinned 2.6.0+cu126** (Quadro P5200 / Pascal sm_61). Never bump it. Stage-3 steps
  that install anything must strip torch/torchvision/torchaudio from requirements and assert the
  pin holds. See `Dockerfile.comfyui` "Layer 2b".

### ⚠️ The ENTRYPOINT silently drops your flags
`Dockerfile.comfyui`'s `ENTRYPOINT` is exec-form and **hardcodes** `main.py`'s flags. Anything
you append (`docker run … sd-worker:latest bash -c "…main.py --foo"`) is passed as trailing args
and **ignored** — main.py runs with the ENTRYPOINT's flags, not yours. To actually set flags:
run with **`--entrypoint bash sd-worker:latest -c "…main.py …"`** (or edit the ENTRYPOINT).
Also: **`--normalvram` is not a real flag** (normal vram = no flag; valid: `--highvram/--lowvram/--novram`).

### ⚠️ GGUF partial-load crash on Pascal → needs --disable-pinned-memory
calcuis/gguf's `pig.py` `.to()` orphans ComfyUI 0.33's pinned-memory bookkeeping during GGUF
partial-load offload → `CUDA error: invalid argument` (upstream #10601/#10662). Fix: launch with
`--disable-pinned-memory` (baked into the ENTRYPOINT default as of 2026-08). Verify it's active:
the log has **no** `Enabled pinned memory` line and **no** `Tried to unpin tensor not pinned`.

## Start the container (proven-good launch)
```bash
docker rm -f comfyui 2>/dev/null
docker run -d --name comfyui --gpus all \
  --device /dev/dri/card0 --device /dev/dri/card1 \
  --device /dev/dri/renderD128 --device /dev/dri/renderD129 \
  -p 8188:8188 --entrypoint bash \
  -v /mnt/external/models:/default-comfyui-bundle/ComfyUI/models \
  -v /mnt/external/models/depth-anything/Depth-Anything-V2-Large:/default-comfyui-bundle/ComfyUI/custom_nodes/comfyui_controlnet_aux/ckpts/depth-anything/Depth-Anything-V2-Large \
  -v /mnt/external/models/lipsync:/default-comfyui-bundle/ComfyUI/custom_nodes/ComfyUI_wav2lip/Wav2Lip/checkpoints \
  -v /mnt/external/models/animatediff_models:/default-comfyui-bundle/ComfyUI/models/animatediff_models \
  -e PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  sd-worker:latest \
  -c "source /venv/bin/activate && mkdir -p /default-comfyui-bundle/ComfyUI/models/tensorrt/rife && python3 main.py --enable-manager-legacy-ui --enable-manager --listen --disable-cuda-malloc --reserve-vram 1.0 --use-pytorch-cross-attention --disable-pinned-memory"
```
Use `-d --name comfyui` (no `--rm`) so logs survive a crash; use `-it --rm` for interactive.
Wait for readiness and verify pinning is off:
```bash
until curl -s --max-time 2 http://localhost:8188/system_stats >/dev/null; do sleep 5; done
docker logs comfyui 2>&1 | grep -i "Enabled pinned memory" && echo "PINNING ON (bad)" || echo "pinning off (good)"
docker exec comfyui bash -lc "ps aux | grep main.py | grep -v grep"   # confirm YOUR flags are live
```
Sanity: `curl -s http://localhost:8188/object_info -o /tmp/oi.json` and grep it for the nodes you
need. A "Missing Node Packs" / `TypeError: Failed to fetch` in the browser is usually just a **dead
backend** (container stopped, stale tab) — start the container and hard-refresh before assuming a
node is missing.

## Send an image to the job
`LoadImage` reads from the container's `input/` dir. Copy the file in and reference it by basename:
```bash
docker cp /path/to/img.jpg comfyui:/default-comfyui-bundle/ComfyUI/input/
# then refetch object_info so the file shows in LoadImage's combo list
curl -s http://localhost:8188/object_info -o /tmp/oi.json
```
The workflow's `LoadImage` node's `image` widget must equal that basename.

## Flatten a subgraph workflow to API format
A saved `.json` containing `SubgraphNode` instances is UI format; `/prompt` needs the flattened
API graph. Use the bundled flattener on ONE branch (one subgraph instance → one output node):
```bash
# find the instance + output node ids: the SubgraphNode has type == a UUID in
# definitions.subgraphs[].id; the output node is e.g. SaveVideo fed from the instance's output.
python3 flatten_subgraph.py --workflow "WF.json" --oi /tmp/oi.json \
        --instance <subgraph-instance-node-id> --output <SaveVideo-node-id> --out api_prompt.json
```
Confirm loader files exist by grepping `/tmp/oi.json` for each `*Loader*` node's combo list
(GGUF/VAE/CLIP/upscaler filenames). Missing files fail the run immediately.

## Iterate to success
```bash
python3 run_api.py --prompt api_prompt.json --host http://localhost:8188 --timeout 1800
```
- **STRUCTURAL node_errors** (exit 4): the flatten is wrong. Read the message, fix `flatten_subgraph.py`
  (see gotchas below), regenerate, re-run.
- **EXECUTION_ERROR** (exit 3, from `/history`): a semantic/widget mismatch. Common: a mis-assigned
  INT (frames/fps/batch) causing tensor-shape mismatch. Inspect the offending node's inputs in
  `api_prompt.json` vs the graph's `widgets_values`, fix the flatten, re-run. ComfyUI **caches**
  unchanged upstream nodes within the session, so re-runs after fixing only the tail node finish fast.
- **SUCCESS** (exit 0): prints the output file. Confirm on disk:
  `docker exec comfyui bash -lc 'find /default-comfyui-bundle/ComfyUI/output -name "*.mp4" -newermt "-30 min" -printf "%p %s\n"'`
- Between attempts, clear stale queued jobs:
  `curl -s -X POST http://localhost:8188/interrupt; curl -s -X POST http://localhost:8188/queue -d '{"clear":true}'`

## Flatten gotchas (baked into flatten_subgraph.py)
- Slot names come from each node's OWN `inputs[]` array, not object_info order (dynamic nodes like
  `ComfyMathExpression` use names like `values.a`).
- Subgraph boundary: inner links use `origin_id=-10` (subgraph inputs) and `target_id=-20` (outputs);
  promoted widget values live in the instance node's `widgets_values` mapped to widget-type inputs.
- Combos assigned by option-membership (order-robust). Scalars positional in object_info order,
  **consuming converted-widget placeholders** that stay in `widgets_values`.
- Union scalar types (`"FLOAT,INT"`) must count as scalar widgets or later scalars misalign
  (this caused `LTXVEmptyLatentAudio.batch_size` = 25 → AV temporal mismatch; correct is 1).
- v3 DynamicCombo (`COMFY_DYNAMICCOMBO_V3`, e.g. `ResizeImageMaskNode.resize_type`, `SaveVideo.codec`):
  FLAT keys — `parent = "<option string>"` plus `parent.subinput = value`, NOT a nested dict.

## Iterate on the BUILD files (make a fix permanent)
When the fix belongs in the image, not just a running container:
- **Add a custom node pack**: add `owner/repo` to `comfyui-dockerfiles/custom_node_repos.txt` AND
  a stage-3 clone in `Dockerfile.comfyui` (mirror the LTXVideo / calcuis-gguf steps: clone, strip
  torch from any requirements, assert the torch pin). Rebuild stage 3, promote to latest.
- **Change a launch flag** (e.g. add `--disable-pinned-memory`): edit the ENTRYPOINT line in
  `Dockerfile.comfyui`. Remember trailing `bash -c` at `docker run` is ignored, so the ENTRYPOINT
  is the real source of truth.
- **Update a node to a compatible commit**: re-clone to a pinned ref in a stage-3 step and assert
  the workflow's imports resolve (mirror the ComfyUI-LTXVideo `ac4d998` step).
- Rebuild + promote:
  ```bash
  cd /home/user/ComfyUI/comfyui-dockerfiles
  DOCKER_BUILDKIT=1 docker build -f Dockerfile.comfyui --build-arg BASE_IMAGE=custom-nodes-ready:cu126-pt26 -t sd-worker:staging .
  docker tag sd-worker:staging sd-worker:latest
  ```

## Endpoints cheat sheet
- `GET /system_stats` — readiness / VRAM
- `GET /object_info` — node schemas + combo file lists (save to /tmp/oi.json)
- `POST /prompt` `{"prompt":<api graph>,"client_id":"x"}` — returns `prompt_id` + `node_errors`
- `GET /history/<prompt_id>` — `status.status_str` == `success`/`error`, `messages[execution_error]`, `outputs`
- `POST /interrupt`, `POST /queue {"clear":true}`, `POST /upload/image` (multipart) — alt to `docker cp`

## Files in this skill
- `flatten_subgraph.py` — UI/subgraph workflow → API prompt (one branch). Verified to reproduce the
  proven-good LTX-2.5 i2v prompt byte-for-byte (`--instance 459 --output 458`).
- `run_api.py` — POST + poll `/history`, prints node_errors / execution_error / success + output file.
