---
name: diagnostic-scanner
description: Language-aware diagnostic scanning. Invokes compilers/linters, captures errors and warnings, groups by severity, and generates fix prompts. Use for automated code quality checks, diagnostic summaries, or CI/CD quality gates.
status: active
last_validated: 2026-05-04
supersedes: []
validation_method: session
---
# diagnostic-scanner Skill

Language-aware diagnostic scanning. Invokes appropriate compilers/linters, captures errors and warnings, groups by severity/category, and generates fix prompts. Produces normalized markdown artifact with embedded JSON metadata.

## Trigger Conditions

Invoke when:
- Running automated code quality checks on a project
- Preparing diagnostic summary for LLM-based fix generation
- Auditing test compilation (--include-tests)
- Building quality gates for CI/CD workflows

## Contract

**Require** (preconditions):
- Valid project directory with language detection possible (marker or 8+ files)
- Language-appropriate tools available in PATH (swiftc, mypy, go vet, etc.)
- User has read access to all project files

**Guarantee** (postconditions):
- Output: Markdown artifact with normalized errors/warnings grouped by severity and category
- Includes fix prompt ready for LLM consumption
- All tool output is parsed and normalized (line, severity, code, message)
- Test compilation results (if --include-tests) are reported separately

**Maintain** (invariants):
- Error/warning counts are accurate
- Severity levels are consistently applied (error > warning > info)
- File paths are canonical (relative to project root)

**Assert** (checkpoints):
- All tools exit successfully or diagnostics are captured
- Severity classification is applied to every finding
- Output markdown is well-formed

## Configuration

```python
# Scan with defaults
scanner.scan(
    project_path="/path/to/project",
    include_tests=False,
    ignore_patterns=["docs/**", "vendor/**"]
)

# Scan including test compilation
scanner.scan(
    project_path="/path/to/project",
    include_tests=True,
    max_analyze_bytes=500000
)
```

## Tool Selection by Language

| Language | Tools Invoked |
|----------|---|
| Python | mypy, pylint, black (check) |
| Go | go vet, golangci-lint (if available) |
| Rust | cargo check, cargo clippy |
| Swift | swiftc -typecheck |
| Java (Maven) | mvn clean compile (+ test-compile if --include-tests) |
| Java (Gradle) | gradle check (+ testClasses if --include-tests) |
| TypeScript/JavaScript | tsc, eslint |

## Usage in Agentic Workflows

**Pattern 1: Quality Gate**
```python
# Scan → check error count → gate merge
result = scanner.scan(repo_path)
if result.error_count > 0:
    return FAILED
```

**Pattern 2: Fix Generation**
```python
# Scan → extract fix prompt → send to LLM
result = scanner.scan(repo_path)
fixes = llm.generate_fixes(result.fix_prompt)
```

**Pattern 3: CI Integration**
```python
# Scan on each commit
result = scanner.scan(repo_path)
emit_github_check_run(
    status="completed",
    conclusion="success" if result.error_count == 0 else "failure",
    output=result.markdown
)
```

## Output Schema

```markdown
# Diagnostic Scan Report

## Overview
- **Language**: Python
- **Errors**: N
- **Warnings**: N
- **Infos**: N
- **Scan Time**: 2.3s

## Errors
### src/api.py:42 (TypeError)
\`\`\`
Expected str, got int
\`\`\`
**Fix Prompt**: Use str() to convert...

### [Additional errors...]

## Warnings
### src/utils.py:89 (UnusedImport)
Line 89: \`import os\`

### [Additional warnings...]

## Test Compilation
- ✅ Tests compile successfully (or ❌ Tests failed)
- **Test Count**: 34
- **Test Errors**: 0

## Metadata
\`\`\`json
{
  "artifact_type": "diagnostic",
  "language": "python",
  "error_count": N,
  "warning_count": N,
  "info_count": N,
  "severity": "error|warning|info",
  "timestamp": "ISO8601"
}
\`\`\`

## Provenance
\`\`\`json
{
  "tools_run": ["mypy src/", "pylint src/"],
  "test_compilation": "pytest --collect-only",
  "ignore_patterns": ["docs/**"]
}
\`\`\`
```

## Related Skills

- `validation` — For interpreting diagnostic results
- `checklist` — For structured violation cataloging
- `code` — For error classification and fix strategies
- `debugging` — For root cause analysis

## Worked Examples

**Example 1: Python Type Errors**
Input: Flask app with typing issues
Output: 3 errors (type mismatches), 12 warnings (unused imports, style)
Fix Prompt: Ready for mypy-focused fix generation

**Example 2: Go Build Errors**
Input: Microservice with API changes
Output: 5 errors (undefined symbols), 8 warnings (ineffective code)
Fix Prompt: Ready for go vet recommendations

## Failure Modes

| Failure | Cause | Recovery |
|---------|-------|----------|
| Tool not found | Compiler/linter not in PATH | Install tool or skip category |
| Parse error | Unexpected tool output format | Log and continue with partial results |
| Test compilation fails | Missing dependencies or broken tests | Report separately; don't fail entire scan |
| Permission denied | Read access denied | Skip file, log warning |
<!-- consolidation:see-also:start -->
## See Also
[[code-extraction]]  [[test-planner]]  [[doc-synthesizer]]
<!-- consolidation:see-also:end -->
