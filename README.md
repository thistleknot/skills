# .skills — the retrievable skill store

## Current consolidation

## Current consolidation

2026-10-31: Open the [Obsidian skill map](.skills/consolidation/skill-map.canvas), [reviewed dispositions](.skills/consolidation/merge_verdicts.md), and [current correlation screen](.skills/consolidation/merge_report.md).

[debugging](.skills/debugging/SKILL.md) owns the root-cause protocol; [debugging-and-error-recovery](.skills/debugging-and-error-recovery/SKILL.md) retains its invocation as a redirect, with the original guidance preserved in [the source archive](.skills/debugging/references/error-recovery-2026-10-30.md).

[pi-config](.skills/pi-config/SKILL.md) owns Pi model configuration; [pi-ollama-config](.skills/pi-ollama-config/SKILL.md) retains its invocation as a redirect, with its original archived by the canonical skill.


Put every non-always-on skill here as `<name>/SKILL.md` (frontmatter `name` +
`description` required — the description is the retrieval unit). Nothing here
is discovered by Claude Code: this directory has no SKILL.md at its top level,
nested ones sit two levels below the skills root, and discovery is one level
deep. Skills here are reachable only through the retrieve-skills gate.

Keep skills that are @-imported from CLAUDE.md/AGENTS.md OUT of this store
(they live in their natural `~/.claude/skills/<name>/` location) — @-import
already injects their body every session; indexing them too would
double-inject.

After changes: `curl -X POST 127.0.0.1:8765/reindex` or
`python3 ../retrieve-skills/indexer.py`.