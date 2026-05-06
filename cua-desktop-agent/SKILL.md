---
name: cua-desktop-agent
description: Autonomous desktop automation via vision-language model (VLM) perception loop. Use when a task requires visual verification of desktop state, autonomous retry until a correct result, or working with applications that lack APIs (games, legacy software, QA testing where screenshots are the ground truth).
status: active
last_validated: 2026-05-02
supersedes: []
validation_method: session
---
# CUA Desktop Agent Skill

## Purpose
Autonomous desktop automation via vision-language model (VLM) perception loop. The agent sees the screen, decides actions, executes them, and verifies results — enabling self-correcting workflows without human-in-the-loop.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Loop (ReAct)                       │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Screenshot  │───▶│ VLM Analysis │───▶│ Action Plan   │  │
│  │ (mss)       │    │ (qwen3-vl:2b)│    │ (CUA format)  │  │
│  └─────────────┘    └──────────────┘    └───────┬───────┘  │
│       ▲                                         │          │
│       │                                   ┌─────▼───────┐  │
│       │                                   │ Execute     │  │
│       │                                   │ (pyautogui) │  │
│       │                                   └─────┬───────┘  │
│       │                                   ┌─────▼───────┐  │
│       └───────────────────────────────────│ Verify      │  │
│          (screenshot to confirm)          │ (VLM check) │  │
│                                           └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Screenshot Capture (`mss`)
- Fast screen capture (10-30ms per frame)
- Returns PIL Image or raw bytes
- Supports multi-monitor, region capture

### 2. Vision Model (`qwen3-vl:2b` via Ollama)
- Multimodal: accepts image + text prompt
- Outputs structured action descriptions or verification results
- Runs locally — no API keys, no latency from network

### 3. Action Executor (`pyautogui`)
- Mouse: move, click, drag, scroll
- Keyboard: type, hotkey (Alt+Tab, Ctrl+C, etc.)
- Coordinate-based or image-template matching

### 4. CUA Protocol (Computer Use Agent)
Based on [trycua/cua](https://github.com/trycua/cua):
- **Actions**: `click(x, y)`, `type(text)`, `hotkey(keys)`, `scroll(direction)`, `wait(seconds)`
- **Observation**: screenshot + optional OCR/element detection
- **Reasoning**: VLM produces "thought → action → expected outcome"
- **Verification**: post-action screenshot compared to expected outcome

### 5. Sandbox (Optional)
- VM isolation (VirtualBox, VMware)
- Container with X11/Wayland forwarding
- Restricted user session with limited permissions

## Stack

| Layer | Tool | Purpose |
|-------|------|---------|
| Capture | `mss` | Fast screenshots |
| Vision | `ollama qwen3-vl:2b` | Screen understanding |
| Control | `pyautogui` | Mouse/keyboard actions |
| Loop | Custom ReAct | Plan → Act → Verify |
| Runtime | Python 3.10+ | Execution environment |

## Use Cases

1. **QA Automation** — Test game mod changes, verify UI elements appear
2. **Desktop Workflow** — Repetitive tasks across applications
3. **Self-Healing Loops** — Agent retries until success, logs failures
4. **Regression Testing** — Visual diff comparison across versions

## Key Design Decisions

- **Local-first**: All processing on-device, no cloud dependency
- **Small model**: qwen3-vl:2b runs on consumer hardware (~2GB VRAM)
- **Loop with verification**: Never trust a single action — always confirm
- **Non-blocking**: Agent runs in separate process, doesn't hijack host session
- **Sandbox recommended**: Untrusted action execution should be isolated

## When to Use This Skill

- Task requires visual verification of desktop state
- Need autonomous retry until correct result
- Working with applications that lack APIs (games, legacy software)
- QA testing where screenshots are the ground truth

## When NOT to Use

- Task can be done via API/CLI (use those instead)
- Requires guaranteed safety (sandbox is optional, not enforced)
- Real-time responsiveness needed (VLM inference adds 1-3s per step)

## Implementation Notes

- `pyautogui` has a known build issue with `pyscreeze` on Windows — may need `pip install pyautogui==0.9.53` or pre-built wheels
- Ollama must be running (`ollama serve`) before agent starts
- Screen resolution affects coordinate accuracy — calibrate per environment
- Consider adding OCR (Tesseract) for text-based verification alongside vision
<!-- consolidation:see-also:start -->
## See Also
[[headless-browser-verification]]  [[openspec-workflow]]  [[agentic-harness]]  [[validation-artifacts]]  [[react-agent]]
<!-- consolidation:see-also:end -->
