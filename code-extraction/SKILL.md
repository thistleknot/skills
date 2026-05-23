---
name: code-extraction
description: Extract source files and configs into a normalized, copy-paste-ready artifact for LLM consumption. Use when preparing a codebase for LLM context, generating documentation from live source, or creating a project snapshot.
status: active
last_validated: 2026-05-04
supersedes: []
validation_method: session
---
# code-extraction Skill

Extract source files + configs into a normalized, copy-paste-ready artifact for LLM consumption. Follows docling extraction philosophy: recursive file collection → semantic grouping → markdown + JSON metadata output.

## Trigger Conditions

Invoke when:
- You need to prepare a codebase for LLM context (megaprompt pattern)
- Building a comprehensive code artifact for review or analysis
- Generating documentation from live source code
- Creating a copy-paste-friendly project snapshot for offline LLM use

## Contract

**Require** (preconditions):
- Valid local filesystem path pointing to a project root
- Project must have recognizable markers (Package.swift, package.json, go.mod, Cargo.toml, pom.xml, pyproject.toml) or ≥8 recognizable source files

**Guarantee** (postconditions):
- Output: Single markdown artifact with embedded JSON metadata
- Artifact contains directory tree, source file sections (grouped by type), and config files
- Files are truncated/summarized if they exceed --max-file-bytes limit
- All ignore patterns are respected

**Maintain** (invariants):
- File tree structure is preserved in output markdown
- Line counts and file sizes are accurate
- Language detection is correct (inferred from file extensions or package markers)

**Assert** (checkpoints):
- Project detection passes (marker found or 8+ source files)
- All file paths are accessible and readable
- Output markdown is well-formed (no unclosed code blocks)

## Configuration

```python
# Extract with defaults
code_extraction.extract(
    project_path="/path/to/project",
    ignore_patterns=["build", "dist", "__pycache__", "node_modules"],
    max_file_bytes=50000,
    include_tests=True
)

# Custom ignore patterns
code_extraction.extract(
    project_path="/path/to/project",
    ignore_patterns=["docs/generated/**", ".venv/**"],
    max_file_bytes=100000
)
```

## Usage in Agentic Workflows

**Pattern 1: Pre-Processing for Summarization**
```python
# Extract codebase → pass to summarization LLM
artifact = code_extraction.extract(repo_path)
summary = llm.summarize(artifact.markdown)
```

**Pattern 2: Code Review Preparation**
```python
# Extract → embed in review context
artifact = code_extraction.extract(repo_path)
review_context = f"{artifact.markdown}\n\n## Review Notes\n..."
```

**Pattern 3: Test Plan Generation**
```python
# Extract → feed to test-planner skill
artifact = code_extraction.extract(repo_path)
test_plan = test_planner.analyze(artifact)
```

## Implementation Notes

- **Language Detection**: Infers from file extensions (py→Python, js→JavaScript, etc.)
- **Project Detection**: Checks for language markers first; falls back to source file count (8+)
- **File Grouping**: Organizes by semantic type (source, test, config, doc)
- **Truncation**: Large files are truncated; preserves first N lines with ellipsis indicator
- **Ignore Patterns**: Glob-based filtering (supports **, *, ?, -)

## Output Schema

```markdown
# Code Extraction Report

## Project Overview
- **Language**: [Detected language]
- **Package Manager**: [pip|npm|cargo|go|maven|gradle]
- **Source Files**: N
- **Test Files**: N
- **Config Files**: N

## Directory Tree
[Tree with line counts]

## Source Files
### [File 1]
\`\`\`[lang]
[content]
\`\`\`

### [File 2]
...

## Configuration Files
### [Config file]
\`\`\`[format]
[content]
\`\`\`

## Metadata
\`\`\`json
{
  "artifact_type": "code_extraction",
  "language": "python",
  "file_count": N,
  "total_lines": N,
  "test_count": N,
  "config_count": N,
  "timestamp": "ISO8601"
}
\`\`\`
```

## Related Skills

- `codebase-knowledge-graph` — Deeper AST analysis and dependency extraction
- `documentation` — For curating and formatting extracted content
- `test-planner` — Downstream consumer for test plan generation

## Worked Examples

**Example 1: Python Project**
Input: `/home/user/myproject` (Flask app with tests)
Output: Markdown artifact with 24 source files, 8 test files, 3 config files
Metadata: language=python, file_count=24, test_count=8

**Example 2: Go Project**
Input: `/home/user/goproj` (CLI tool)
Output: Markdown artifact with 12 source files, minimal tests
Metadata: language=go, file_count=12, test_count=2

## Failure Modes

| Failure | Cause | Recovery |
|---------|-------|----------|
| Project not detected | No markers + <8 source files | Pass --force or add marker file |
| File not readable | Permission denied or symlink loop | Skip file, log warning |
| Large file truncated | Exceeds --max-file-bytes | Adjust limit or review truncated version |
| Invalid markdown | Unclosed code block | Report and halt; user reviews output |
<!-- consolidation:see-also:start -->
## See Also
[[auto-ingest]]  [[code]]  [[pdf-extraction]]
<!-- consolidation:see-also:end -->
