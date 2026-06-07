# CTP2 Image Patching Workflow

**Load this skill when** the task involves patching CTP2 game images using CSV/schema parsing for units, city improvements, and terrain, followed by observer validation.

## Workflow Sequence (strict order)

1. **One mutation-oriented patcher task** on `patch_ctp2_images.py` — do NOT explore project structure, do NOT re-discover files. Use these known lanes:
   - CSV lanes: `Scenarios\mom\tools\momjr_csv\*.csv` (units.csv, improvements.csv, tileimp.csv)
   - Image lanes: `Scenarios\*\scen0000\default\graphics\pictures\*`, `ctp2_data\default\graphics\pictures\*`
   - At most one gamedata reference file

2. **Run the patcher** — `python .\patch_ctp2_images.py` from workspace root. Do NOT run `ls`, `dir`, `Get-ChildItem`, or CSV/schema listing before the run command.

3. **If run fails with `NameError: name 'missing_details' is not defined`:**
   - Make `patch_images()` return exactly one `missing_details`
   - Update `main()` to unpack exactly four return values
   - Rerun `python .\patch_ctp2_images.py`
   - Do NOT inspect CSV schemas first — the bug is the return-value/unpack path
   - Do NOT delegate generic retries like `Fix NameError in patcher script`

4. **If patcher edits but does NOT run the script:** next step must force the run via handyman or debugger. Do not send patcher back into another reasoning cycle first.

5. **If `patch_images()` already returns a single `missing_details` and `main()` already unpacks four values:** do not edit that return path. Rerun only.

6. **If file contains duplicated return** (`..., missing_details, missing_details`): normalize to one trailing `missing_details`, then rerun.

7. **Debugger handles failures** — route concrete errors back to patcher/fixer for exact fixes.

8. **Observer spot-checks 5 translations:**
   - After patcher run summary, delegate one bounded handyman pass to select 5 random `.tga` paths from target graphics directories
   - Convert `.tga` to `.png` previews via Python + Pillow (one bounded handyman command)
   - Delegate observer with the 5 `.png` paths

## Hard Rules

- Only one discovery/inventory pass of the known lanes. If empty, return BLOCKED.
- Only one mutation turn on `patch_ctp2_images.py` per error class. After the fix, run the script.
- After any mutation, the next step is run, then debug, then observe. No re-reading, re-discovering, or re-planning.
- If scout returns `PRESENT:` but cannot fill the full contract, do NOT call scout again. Route to handyman or fixer using the best concrete paths already known.
- Do not call memory-bank tools, todo tools, or scout during this workflow. Work only from current workspace.
- Oracle/planner is forbidden as a first hop and forbidden as a restatement hop. Start with handyman or fixer.
- After the first bounded inventory of the known lanes completes, the only valid next agents are fixer, debugger, or observer.