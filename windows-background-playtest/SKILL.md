---
name: windows-background-playtest
description: >
  Test Windows desktop applications and games without human input or taking
  foreground focus. Launch a target, drive its window through posted messages
  when supported, and capture window screenshots. Use for repeatable UI walks,
  smoke tests, and background soak runs. This uses a real desktop window; use
  true headless APIs or browser automation when the target supports them.
---

# Windows Background Playtest

Use this workflow to run an application-owned UI through a background Windows
window, with no physical mouse or keyboard input. “Headless” in this skill means
hands-off and focus-preserving: a desktop session and target window still exist,
and the application may still play audio.

| Stage | Mechanism | Tag |
|---|---|---|
| TARGET | Identify the executable, startup state, window, and user-visible goal | [mandatory] |
| LAUNCH | Start only the requested process without foreground activation | [mandatory] |
| DRIVE | Send window-scoped input through the target's supported message path | [mandatory] |
| OBSERVE | Capture target-window images and check app state or logs | [mandatory] |
| CLEANUP | Close only the process started by this run and retain evidence | [mandatory] |

R1: WHEN the target supports a programmatic interface or native test harness,
THEN use it before synthesizing desktop input.
R2: WHEN sending or posting input messages, THEN first prove that the target
receives that message type with one small action and an observable result.
R3: WHEN a run is backgrounded, THEN do not use global cursor or keyboard input.
R4: WHEN screenshots are needed, THEN capture the target window by handle and do
not silently substitute a full-desktop capture.
R5: WHEN a target rejects posted input or needs foreground-only input, THEN
report that boundary and stop before using global input.
R6: WHEN a run ends or fails, THEN record the process result and preserve its
last useful screenshot and logs before cleanup.

CLOSED: A window handle and successful `PostMessage` return are not proof that
the application processed the input. Verify an observable state change. A
background window is not a true headless process. Never use `SendInput`,
PyAutoGUI, or another global-input method as an automatic fallback.

Preconditions: Windows, an interactive desktop session, and permission to run
the target application. The target must expose a window and process a Windows
message queue for this method. Failures include missing windows, message paths
ignored by the application/framework, unsupported window capture, modal dialogs,
and app-specific state or timing assumptions.

## Choose the control path

1. Prefer the application's API, command protocol, UI automation provider, or
   existing test harness when it exercises the user-visible behavior needed.
2. Otherwise launch the target with a non-activating show mode and identify its
   top-level HWND by the launched PID plus a title or another stable property.
3. Post input to the top-level HWND or the target-owned child HWND under the
   requested client coordinate. The helper resolves child HWNDs without asking
   the desktop which window is under the physical cursor. Windows message
   delivery differs by toolkit and engine: a target may accept `WM_LBUTTONDOWN/UP`
   on a child, while SDL, raw-input, browser, and anti-cheat paths may ignore or
   reinterpret them. Calibrate one action before writing a long scenario.
4. If keyboard input is ignored, test the target's documented focus/message
   requirements. Do not call `SetForegroundWindow` or synthesize global input
   under this skill. If the application requires foreground focus, report the
   limit or switch to its own automation interface.
5. Use `PrintWindow` with `PW_RENDERFULLCONTENT` for window-only screenshots
   when supported. A successful API return can still yield a blank image; inspect
   the actual capture. Prefer target-provided screenshots or a documented
   window-capture API when `PrintWindow` is unsupported.

## Run a scripted walk

The included `scripts/win32_playtest.py` uses only the Python standard library.
It launches the target executable in a JSON plan with a non-activating startup
hint, finds that process's window, sends or posts a short list of
clicks/keys/text, captures PNG window images, and requests closure only from its own process.
Pass the final executable directly; launcher shims can spawn a different PID
whose window this helper intentionally will not control. Read the script's
`--help` and plan example above before use.

Example plan:

```json
{
  "command": ["C:/Python/python.exe", "-m", "my_app"],
  "cwd": "C:/work/my_app",
  "window_title": "My Application",
  "startup_timeout_seconds": 10,
  "steps": [
    {"action": "capture", "path": "artifacts/00-start.png"},
    {"action": "click", "x": 140, "y": 24},
    {"action": "wait", "milliseconds": 250},
    {"action": "capture", "path": "artifacts/01-started.png"}
  ]
}
```

Run it with:

```powershell
python "$HOME/.skills/windows-background-playtest/scripts/win32_playtest.py" plan.json
```

Plans contain commands, so inspect the plan before executing it. Coordinates are
client-area pixels for the target window. Use fixed waits only for short,
known transitions; prefer an app-specific state check when one exists.

## Evidence and failure handling

- Keep the scenario short and discriminating: baseline, one action, visible
  result, and a failure or terminal case when relevant.
- Check both the screenshot and an independent signal such as process exit,
  application log, accessible control state, save file, or test assertion.
- If a message call succeeds but state does not change, classify delivery as
  unproven; do not add retries or switch to physical input without evidence.
- On crashes, retain the exit code, crash dump/log, exact command, plan, and
  last screenshot. Reproduce the smallest failed step before extending the walk.
- Stop or bound a soak run by turns, elapsed time, or a specific checkpoint.
  Do not leave an application process running after the task unless it is an
  intended user-facing service.

## Boundaries

- This skill does not make a GUI application truly windowless. For service-side
  CI with no interactive desktop, prefer unit/integration APIs or a supported
  virtual display.
- It does not promise that posted mouse or keyboard messages work for every
  toolkit. Each target needs its own measured input adapter and test evidence.
- Never modify the target binary, inject into another process, or alter global
  input settings as an implicit way to make a scenario pass.
- If startup fails before the target exposes a window, the helper terminates
  only the direct process it started; it never kills by process name.
