---
name: chrome-extensions
description: >
  Build, install and verify a personal Chrome extension that does something on the
  local machine (write a file, run a script) when its toolbar button is clicked.
  Covers the Manifest V3 extension + native-messaging host pattern, pinning the
  extension ID with a "key", registering the host under HKCU (no admin), the one
  manual "Load unpacked" step and why automation cannot do it, and how to test the
  real Chrome round trip yourself without clicking the toolbar. Trigger on "chrome
  extension", "browser button that saves to a file", "native messaging", "clip the
  page to a file", "load unpacked", "extension shows a red !".
status: active
last_validated: 2026-10-03
---

# Chrome extensions that touch the local machine

Reference implementation (working, verified 2026-10-03):
`D:\c\arxiv_id_lists\chrome_clipper\` — "Save to llm.txt": one click prepends the
page title + URL to `C:\Users\user\Documents\wiki\data science\llm\llm.txt`.
Copy it as the starting point.

```
chrome_clipper/
  extension/manifest.json        MV3, "key" pins the ID, permission nativeMessaging
  extension/background.js        toolbar click -> sendNativeMessage -> badge + / = / !
  extension/selftest.html|.js    same call as the click, result reported to disk
  com.user.llm_txt_clipper.json  native-host manifest (path + allowed_origins)
  llm_txt_clip_host.bat          launcher Chrome executes (needs .exe/.bat, not .py)
  llm_txt_clip_host.py           the host: read framed JSON, do the work, reply
  host_launch.log                every launch + reply (debugging evidence)
  clipped.log                    backup copy of every entry written
```

## 1. The architecture, and why

An extension cannot write files. It can talk to a **native-messaging host**: a local
program Chrome starts per message, speaking framed JSON on stdin/stdout.

- No server, nothing running in the background — Chrome launches the host on demand.
- Registration is a key under **HKCU**, so **no admin rights** are needed.
- Rejected: a local HTTP server (another long-lived process to babysit), Playwright
  (separate throwaway Chromium profile — nothing installed there reaches the real
  Chrome), `--load-extension` (removed from branded Chrome), registry "external
  extensions" (Web Store `update_url` only, or HKLM policy = admin).

## 2. Pin the extension ID BEFORE loading

The host's `allowed_origins` must name the extension ID. An unpacked extension's ID
otherwise depends on its folder path, so pin it with a `key` in manifest.json:

```python
import base64, hashlib
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
der = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key() \
        .public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
key    = base64.b64encode(der).decode()                       # -> manifest "key"
ext_id = "".join("abcdefghijklmnop"[int(c, 16)]
                 for c in hashlib.sha256(der).hexdigest()[:32])  # -> allowed_origins
```

The private key is not needed for an unpacked extension; do not keep it.
Verify after loading: the card on chrome://extensions shows the same ID, or read it
from disk: `User Data\Default\Secure Preferences` -> `extensions.settings.<id>.path`.

**Permissions: `["nativeMessaging", "activeTab"]` — both.** Without `activeTab` (or
`tabs`), `action.onClicked` hands you a tab whose `url` and `title` are EMPTY. The
click still reaches the host, so it looks like "nothing happens" while the log shows
`'detail': 'empty url'` (2026-10-03: shipped without it; a selftest that passes the
URL in itself cannot catch this — the click path is the only thing that does).

## 3. Host manifest + registry (HKCU, no admin)

```json
{ "name": "com.user.llm_txt_clipper", "type": "stdio",
  "path": "D:\\c\\arxiv_id_lists\\chrome_clipper\\llm_txt_clip_host.bat",
  "allowed_origins": ["chrome-extension://<ext_id>/"] }
```
```
reg add "HKCU\Software\Google\Chrome\NativeMessagingHosts\com.user.llm_txt_clipper" /ve /t REG_SZ /d "<full path to that .json>" /f
```

`path` must be an .exe or .bat — the .bat just runs `python.exe "%~dp0host.py" %*`.
Chrome passes `chrome-extension://<id>/ --parent-window=<n>` as arguments.

## 4. The host (Python)

```
read:  n = struct.unpack("<I", stdin.read(4)); msg = json.loads(stdin.read(n))
reply: data = json.dumps(reply).encode(); stdout.write(struct.pack("<I", len(data)) + data)
```

- Use `sys.stdin.buffer` / `sys.stdout.buffer` (binary). NOTHING else may print to
  stdout — any stray line corrupts the framing. Log to a file instead.
- Log every launch and every reply to a file (`host_launch.log`). That file is what
  separates "Chrome never started the host" (registration/ID problem) from "host
  started and failed" (code problem). Without it a red "!" is undiagnosable.
- Catch everything and still send a reply with the error text, so the extension can
  show it instead of "Native host has exited".
- Host .py changes take effect on the NEXT call. manifest.json / background.js
  changes need an extension reload — do it yourself, no operator click: selftest.js
  calls `chrome.runtime.reload()` when opened with `?reload=1`, then reopen the
  selftest without it and confirm `chrome.runtime.getManifest()` version/permissions
  in the logged result. Bump `version` on every manifest edit so the reload is provable.

Dedupe on IDENTITY, not on the raw URL string: the same arXiv paper arrives as
abs/pdf/html, with `v1`/`v2` and `#S3` anchors (2604.05278 was re-added as
`html/...v1#S3` while `html/...v1` was present). Match arXiv on the paper id with
digit-boundary lookarounds (so `2604.0527` does not match `2604.05278`), and other
URLs with the `#fragment` and trailing slash stripped.

File-writing specifics from the reference host: follow the file's own
line endings (CRLF), preserve a BOM, write atomically (temp file + `os.replace`), and
append a copy to `clipped.log` — an editor holding unsaved changes can save over a
prepended entry, and the log keeps it recoverable.

## 5. The ONE manual step: Load unpacked (operator does it, ~30 s)

Automation cannot do this: "Load unpacked" opens a native Windows folder picker, and
`chrome://` pages are blocked for browser automation. Make it painless:

```powershell
Set-Clipboard -Value 'D:\...\extension'        # path ready to paste
Start-Process chrome.exe 'chrome://extensions' # may land on Settings instead
```

Instructions that actually worked (the operator got lost on the vaguer version):
1. If Chrome shows **Settings**, click **Extensions** in the left sidebar (bottom,
   just above "About Chrome") — Developer mode lives on that page, not Settings.
2. **Developer mode** switch: top-right of the Extensions page.
3. **Load unpacked**: first button, top-left (appears once Developer mode is on).
4. In the folder dialog: paste into the **Folder:** box at the bottom (Ctrl+V), then
   **Select Folder**.
5. Pin it: puzzle-piece icon -> pin.

## 6. Test it YOURSELF — do not hand an untested button to the operator

Operator, 2026-10-03: "you need to test this shit yourself." Testing the host by
piping framed JSON from Python is necessary but NOT sufficient — it skips Chrome.
The toolbar button cannot be clicked by automation, so test Chrome's side this way:

1. Put a `selftest.html` + `selftest.js` in the extension making the same
   `chrome.runtime.sendNativeMessage` call as the click (payload from `?url=&title=`).
   Files in an unpacked extension are served from disk, so new files need NO reload.
2. Open it from the shell (the claude-in-chrome navigate tool refuses
   `chrome-extension://` URLs; Start-Process does not):
   `Start-Process chrome.exe 'chrome-extension://<id>/selftest.html?url=...&title=...'`
3. Have selftest.js send its result — `{id, sent, lastError, reply}` — back to the
   host as a second message, which the host writes to `host_launch.log`. Now Chrome's
   view of the round trip is on disk and checkable. Screenshots are unreliable (Chrome
   may be on another monitor or behind the terminal).
4. Battery: empty url (round trip, no file change), a URL already present
   (`duplicate`, file untouched), a sentinel URL (`added`) — then remove the sentinel
   by stripping exactly the bytes prepended, and confirm the file's first line is the
   original one again. Allow ~5-8 s per page open; the add page was slow and looked
   like a miss at 5 s.
5. What still needs the operator: one real toolbar click. Clear `host_launch.log`
   first so that click's entry is unambiguous.

## Failure decoding

| Symptom | Meaning | Check |
|---|---|---|
| badge "!" + "Specified native messaging host not found" | registry key or manifest path wrong | `reg query HKCU\...\NativeMessagingHosts\<name>` |
| "Access to the specified native messaging host is forbidden" | extension ID not in `allowed_origins` | ID on the card vs the host json |
| "Native host has exited" / no reply | host crashed or printed to stdout | `host_launch.log` — no line = never launched |
| launch line present, no reply line | exception before reply | wrap main in try/except, log it |
| click logged, `'detail': 'empty url'`, `--parent-window=0` | no `activeTab` permission — tab.url/title empty | add it, bump version, `selftest.html?reload=1` |
| works from selftest, not from toolbar | background.js stale, or the selftest supplied what the click path lacks | reload; then compare the two log entries |
