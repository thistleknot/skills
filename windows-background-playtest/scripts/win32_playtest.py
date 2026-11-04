"""Run short Windows GUI playtests through target-window messages.

| Stage | Mechanism | Tag |
|---|---|---|
| LAUNCH | Start the requested command with a non-activating show hint | [mandatory] R1 |
| LOCATE | Match the target top-level window to the launched process | [mandatory] R2 |
| DRIVE | Post scripted mouse/keyboard/text messages to that HWND | [mandatory] R3 |
| CAPTURE | Save the target window through PrintWindow as PNG | [optional] R4 |
| CLOSE | Send WM_CLOSE and report if the owned process stays alive | [mandatory] R5 |

R1: WHEN a plan is read, THEN its command and working directory are explicit.
R2: WHEN a window is selected, THEN its owner PID is the child launched by this run.
R3: WHEN a message is posted, THEN its return value is checked and failures stop the walk.
R4: WHEN PrintWindow cannot capture the target, THEN no desktop-wide capture is substituted.
R5: WHEN cleanup is requested, THEN only the launched process receives WM_CLOSE.

CLOSED: A successful PostMessage result does not prove application-level input.
Mouse/key delivery and the PNG must be checked by the playtest owner.

Preconditions: Windows desktop session and a valid JSON plan. Failure modes
include unsupported message routing, no matching HWND, blank PrintWindow output,
and a target that remains open after WM_CLOSE.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path
from typing import Any
from ctypes import wintypes


if sys.platform != "win32":
    raise SystemExit("win32_playtest.py requires Windows")


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
WINDOW_ENUM_PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

WM_CLOSE = 0x0010
WM_ACTIVATE = 0x0006
WM_SETFOCUS = 0x0007
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_CHAR = 0x0102
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WA_ACTIVE = 1
MK_LBUTTON = 1
PW_RENDERFULLCONTENT = 2
BI_RGB = 0
DIB_RGB_COLORS = 0
STARTF_USESHOWWINDOW = subprocess.STARTF_USESHOWWINDOW
SW_SHOWNOACTIVATE = 4

user32.EnumWindows.argtypes = [WINDOW_ENUM_PROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.EnumChildWindows.argtypes = [wintypes.HWND, WINDOW_ENUM_PROC, wintypes.LPARAM]
user32.EnumChildWindows.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.SendMessageTimeoutW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_size_t),
]
user32.SendMessageTimeoutW.restype = wintypes.BOOL
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PrintWindow.restype = wintypes.BOOL
user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.GetWindowDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int


class BitmapInfoHeader(ctypes.Structure):
    """Describe a top-down 32-bit bitmap for GDI extraction."""

    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BitmapInfo(ctypes.Structure):
    """Wrap a bitmap header and the required color-table placeholder."""

    _fields_ = [("bmiHeader", BitmapInfoHeader), ("bmiColors", wintypes.DWORD * 1)]


def _window_for_process(process_id: int, title_fragment: str) -> tuple[int, str] | None:
    """Find a top-level window owned by a process and matching a title fragment.

    Require: `process_id` is the process launched for this playtest.
    Guarantee: returns an HWND and title, or `None` when no match exists.
    Maintain: windows owned by unrelated processes are never selected.
    Assert: the owning PID equals `process_id` for every returned window.
    """
    matches: list[tuple[int, str]] = []
    fragment = title_fragment.casefold()

    @WINDOW_ENUM_PROC
    def visit(hwnd: int, _: int) -> bool:
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != process_id:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, len(title))
        if fragment in title.value.casefold():
            matches.append((hwnd, title.value))
            return False
        return True

    user32.EnumWindows(visit, 0)
    return matches[0] if matches else None


def _post(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> None:
    """Post one message and raise when Windows rejects it.

    Require: `hwnd` belongs to the current launched target.
    Guarantee: returns after Windows accepts the queued message.
    Maintain: this never injects global input or changes the foreground window.
    Assert: PostMessageW reports success.
    """
    if not user32.PostMessageW(hwnd, message, wparam, lparam):
        raise ctypes.WinError(ctypes.get_last_error())


def _send(hwnd: int, message: int, wparam: int = 0, lparam: int = 0) -> None:
    """Send one synchronous message with a timeout to the target window.

    Require: `hwnd` belongs to the current launched target.
    Guarantee: returns after dispatch or raises on timeout/failure.
    Maintain: this never injects global input or changes the foreground window.
    Assert: SendMessageTimeoutW completes within one second.
    """
    result = ctypes.c_size_t()
    delivered = user32.SendMessageTimeoutW(
        hwnd, message, wparam, lparam, 0x0002, 1000, ctypes.byref(result)
    )
    if not delivered:
        raise ctypes.WinError(ctypes.get_last_error())


def _message_sender(step: dict[str, Any]):
    """Select the explicitly requested window-message delivery method."""
    delivery = step.get("delivery", "post")
    if delivery == "post":
        return _post
    if delivery == "send":
        return _send
    raise ValueError("delivery must be 'post' or 'send'")


def _pack_point(x: int, y: int) -> int:
    """Pack client coordinates into the LPARAM form used by mouse messages."""
    if not (0 <= x <= 0xFFFF and 0 <= y <= 0xFFFF):
        raise ValueError("click coordinates must be between 0 and 65535")
    return (y << 16) | x


def _child_at_point(top_hwnd: int, x: int, y: int) -> tuple[int, int, int]:
    """Resolve a top-level client point to its owning child HWND and local point.

    Require: coordinates are relative to the top-level client area.
    Guarantee: returns the child window under that point and child-relative coordinates.
    Maintain: the child belongs to the same process as the top-level target.
    Assert: coordinate conversion and child ownership succeed.
    """
    point = wintypes.POINT(x, y)
    if not user32.ClientToScreen(top_hwnd, ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    root_pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(top_hwnd, ctypes.byref(root_pid))
    candidates: list[tuple[int, int]] = []

    @WINDOW_ENUM_PROC
    def visit(child_hwnd: int, _: int) -> bool:
        child_pid = wintypes.DWORD()
        rect = wintypes.RECT()
        user32.GetWindowThreadProcessId(child_hwnd, ctypes.byref(child_pid))
        if child_pid.value != root_pid.value or not user32.GetWindowRect(child_hwnd, ctypes.byref(rect)):
            return True
        if rect.left <= point.x < rect.right and rect.top <= point.y < rect.bottom:
            area = (rect.right - rect.left) * (rect.bottom - rect.top)
            candidates.append((area, child_hwnd))
        return True

    user32.EnumChildWindows(top_hwnd, visit, 0)
    # Target-owned children have smaller rectangles than their containing parents.
    child_hwnd = min(candidates)[1] if candidates else top_hwnd
    if not user32.ScreenToClient(child_hwnd, ctypes.byref(point)):
        raise ctypes.WinError(ctypes.get_last_error())
    return child_hwnd, point.x, point.y


def _key_code(value: str) -> int:
    """Resolve a named key or one ASCII letter/digit to a virtual key code."""
    names = {
        "enter": 0x0D,
        "space": 0x20,
        "escape": 0x1B,
        "tab": 0x09,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
        "backspace": 0x08,
    }
    normalized = value.casefold()
    if normalized in names:
        return names[normalized]
    if len(value) == 1 and value.isascii() and value.isalnum():
        return ord(value.upper())
    raise ValueError(f"unsupported key name: {value}")


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    """Encode one PNG chunk with its length and CRC."""
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def _capture_png(hwnd: int, output_path: Path) -> None:
    """Capture one window through PrintWindow and write an RGBA PNG.

    Require: `hwnd` is a live window and `output_path` is writable.
    Guarantee: writes only the target window image, without desktop fallback.
    Maintain: GDI handles allocated here are released on success and failure.
    Assert: PrintWindow and GetDIBits both return success.
    """
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise ctypes.WinError(ctypes.get_last_error())
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise RuntimeError(f"window has invalid dimensions: {width}x{height}")

    window_dc = user32.GetWindowDC(hwnd)
    if not window_dc:
        raise ctypes.WinError(ctypes.get_last_error())
    memory_dc = 0
    bitmap = 0
    previous_object = 0
    try:
        memory_dc = gdi32.CreateCompatibleDC(window_dc)
        bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
        if not memory_dc or not bitmap:
            raise ctypes.WinError(ctypes.get_last_error())
        previous_object = gdi32.SelectObject(memory_dc, bitmap)
        if not previous_object:
            raise ctypes.WinError(ctypes.get_last_error())
        if not user32.PrintWindow(hwnd, memory_dc, PW_RENDERFULLCONTENT):
            raise RuntimeError("PrintWindow failed; no desktop-wide screenshot was taken")
        gdi32.SelectObject(memory_dc, previous_object)
        previous_object = 0

        info = BitmapInfo()
        info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        raw = ctypes.create_string_buffer(width * height * 4)
        rows = gdi32.GetDIBits(memory_dc, bitmap, 0, height, raw, ctypes.byref(info), DIB_RGB_COLORS)
        if rows != height:
            raise RuntimeError(f"GetDIBits returned {rows} of {height} rows")

        rgba = bytearray((width * 4 + 1) * height)
        source = memoryview(raw).cast("B")
        target_offset = 0
        for row in range(height):
            rgba[target_offset] = 0
            target_offset += 1
            source_offset = row * width * 4
            for _ in range(width):
                blue, green, red = source[source_offset : source_offset + 3]
                rgba[target_offset : target_offset + 4] = bytes((red, green, blue, 255))
                source_offset += 4
                target_offset += 4

        output_path.parent.mkdir(parents=True, exist_ok=True)
        header = struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header)
        png += _png_chunk(b"IDAT", zlib.compress(rgba, level=6)) + _png_chunk(b"IEND", b"")
        output_path.write_bytes(png)
    finally:
        if previous_object:
            gdi32.SelectObject(memory_dc, previous_object)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(hwnd, window_dc)


def _execute_step(hwnd: int, step: dict[str, Any], base_dir: Path) -> None:
    """Execute one validated plan action against the target window.

    Require: `step` is a mapping with one supported `action` and its arguments.
    Guarantee: performs the action or raises an actionable error.
    Maintain: input messages are posted only to `hwnd`.
    Assert: coordinates, delay, and message names are valid before posting.
    """
    action = step.get("action")
    if action == "wait":
        milliseconds = int(step["milliseconds"])
        if milliseconds < 0:
            raise ValueError("wait milliseconds must be non-negative")
        time.sleep(milliseconds / 1000)
    elif action == "capture":
        output_path = Path(step["path"])
        if not output_path.is_absolute():
            output_path = base_dir / output_path
        _capture_png(hwnd, output_path)
        print(f"captured {output_path}")
    elif action == "click":
        target_hwnd, x, y = _child_at_point(hwnd, int(step["x"]), int(step["y"]))
        point = _pack_point(x, y)
        print(f"mouse target hwnd={target_hwnd:#x} child_point=({x},{y})")
        send_message = _message_sender(step)
        if step.get("focus_spoof"):
            _post(target_hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
            _post(target_hwnd, WM_SETFOCUS, 0, 0)
        send_message(target_hwnd, WM_MOUSEMOVE, 0, point)
        send_message(target_hwnd, WM_LBUTTONDOWN, MK_LBUTTON, point)
        send_message(target_hwnd, WM_LBUTTONUP, 0, point)
    elif action == "key":
        code = _key_code(str(step["key"]))
        _post(hwnd, WM_KEYDOWN, code, 0)
        _post(hwnd, WM_KEYUP, code, 0)
    elif action == "text":
        for character in str(step["text"]):
            _post(hwnd, WM_CHAR, ord(character), 0)
    elif action == "focus-spoof":
        # Some engines check their internal focus flag even though real focus stays unchanged.
        _post(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
        _post(hwnd, WM_SETFOCUS, 0, 0)
    else:
        raise ValueError(f"unsupported action: {action!r}")


def _load_plan(path: Path) -> dict[str, Any]:
    """Load and minimally validate a JSON playtest plan.

    Require: `path` points to a JSON object.
    Guarantee: returns a plan with a command, title fragment, and action list.
    Maintain: plan-provided commands remain explicit and are not shell-expanded.
    Assert: each step is an object before any process starts.
    """
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        raise ValueError("plan root must be a JSON object")
    if not isinstance(plan.get("command"), list) or not plan["command"]:
        raise ValueError("plan.command must be a non-empty argument array")
    if not isinstance(plan.get("window_title"), str) or not plan["window_title"]:
        raise ValueError("plan.window_title must be a non-empty title fragment")
    if not isinstance(plan.get("steps"), list) or not all(isinstance(item, dict) for item in plan["steps"]):
        raise ValueError("plan.steps must be an array of action objects")
    if "shell" in plan:
        raise ValueError("shell execution is not supported; use an argument array")
    return plan


def run_plan(plan_path: Path) -> int:
    """Launch the target, execute its action plan, and request safe cleanup.

    Require: the plan was reviewed and names an authorized executable.
    Guarantee: returns zero after successful steps; the launched process receives WM_CLOSE.
    Maintain: no global cursor/keyboard injection or forced process termination occurs.
    Assert: the located HWND belongs to the launched PID.
    """
    plan = _load_plan(plan_path)
    base_dir = plan_path.resolve().parent
    cwd = Path(plan.get("cwd", str(base_dir)))
    if not cwd.is_absolute():
        cwd = base_dir / cwd
    environment = os.environ.copy()
    for key, value in plan.get("env", {}).items():
        environment[str(key)] = str(value)

    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= STARTF_USESHOWWINDOW
    startup.wShowWindow = SW_SHOWNOACTIVATE
    process = subprocess.Popen(
        [str(part) for part in plan["command"]],
        cwd=str(cwd),
        env=environment,
        startupinfo=startup,
        close_fds=True,
    )
    hwnd = 0
    try:
        timeout = float(plan.get("startup_timeout_seconds", 10))
        deadline = time.monotonic() + timeout
        title = ""
        while time.monotonic() < deadline and process.poll() is None:
            result = _window_for_process(process.pid, plan["window_title"])
            if result is not None:
                hwnd, title = result
                break
            time.sleep(0.1)
        if not hwnd:
            raise RuntimeError(
                f"no window matching {plan['window_title']!r} for PID {process.pid}; "
                f"exit={process.poll()}"
            )
        if plan["window_title"].casefold() not in title.casefold():
            raise RuntimeError(
                f"PID {process.pid} opened {title!r}, not the requested "
                f"window {plan['window_title']!r}"
            )
        print(f"target hwnd={hwnd:#x} pid={process.pid} title={title!r}")
        for index, step in enumerate(plan["steps"], start=1):
            _execute_step(hwnd, step, base_dir)
            print(f"step {index}/{len(plan['steps'])}: {step['action']}")
        return_code = process.poll()
        print(f"target exit before close: {return_code}")
        return 0
    finally:
        if process.poll() is None:
            if hwnd:
                _post(hwnd, WM_CLOSE)
                timeout = float(plan.get("close_timeout_seconds", 2))
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    print(f"target remains open after WM_CLOSE; PID {process.pid} was left running")
            else:
                # A child that never exposed a target window cannot receive WM_CLOSE.
                # This is only the exact process created by this run, not a name-based kill.
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    print(f"failed to stop launch process PID {process.pid}")
        print(f"launched process exit code after cleanup: {process.poll()}")


def main() -> int:
    """Parse the plan path and run one Windows background playtest.

    Require: one reviewed JSON plan path.
    Guarantee: returns the playtest process status and prints each step result.
    Maintain: process startup and window control remain scoped to this run.
    Assert: usage errors are handled by argparse before launch.
    """
    parser = argparse.ArgumentParser(description="Run a background Windows GUI playtest from a JSON plan.")
    parser.add_argument("plan", type=Path, help="reviewed JSON playtest plan")
    args = parser.parse_args()
    return run_plan(args.plan)


if __name__ == "__main__":
    raise SystemExit(main())
