# Megaprompt: CLI Tool Feature Extraction

This document consolidates the extracted features from the megaprompter CLI tool suite.
The feature analysis was performed via docling-style extraction (parse → normalize → markdown).

## Megaprompter CLI Suite Overview

The megaprompter project is a Swift-based CLI framework providing four integrated tools:

### 1. **megaprompt** — Context Assembly & Prompt Formatting
- **Purpose**: Collect codebase context and format it into structured prompts for LLM consumption
- **Input**: Project folder, optional file glob patterns
- **Output**: Markdown artifact with embedded file sections, metadata, and formatting hints
- **Key Features**:
  - Multi-language source file detection (Python, Go, Rust, Swift, Java, JS/TS, Kotlin)
  - File grouping by type (sources, tests, configs, docs)
  - Hierarchical tree building with truncation support
  - Non-UTF8 character stripping and LaTeX support
  - Clipboard export and filtering options

### 2. **megadiagnose** — Language-Aware Diagnostic Scanning
- **Purpose**: Invoke language-specific tools and normalize error/warning output
- **Input**: Project folder, tool filter (optional)
- **Output**: Structured violation catalog with severity levels and fix prompts
- **Supported Tools**:
  - Python: mypy (type checking, JSON output), pylint (code quality)
  - Go: go vet (built-in linter)
  - Rust: cargo check, cargo clippy
  - Swift: swiftc, swiftlint
  - JavaScript/TypeScript: eslint, tsc
  - Kotlin: kotlinc
- **Key Features**:
  - Tool auto-discovery (PATH + default locations)
  - Error parsing with BOM handling and XML escaping
  - Severity classification (critical, warning, note)
  - LLM-ready fix prompts per violation
  - Timeout enforcement per tool (30s default)

### 3. **megatest** — Coverage-Aware Test Planning
- **Purpose**: Analyze code coverage and generate test scenarios
- **Input**: Project folder, coverage data (optional)
- **Output**: Markdown test plan with green/yellow/red status flags
- **Key Features**:
  - Framework detection (pytest, go test, cargo test, Xcode, Jest)
  - Coverage assessment (green ≥80%, yellow 40-80%, red <40%)
  - Scenario generation by test level (smoke, unit, integration, e2e, regression)
  - Regression subject detection via git diff
  - Lean analyzer for test-sparse projects
  - Kotlin special handling (less aggressive assessment)

### 4. **megadoc** — AST-Based Documentation & Diagramming
- **Purpose**: Generate project documentation with Mermaid diagrams
- **Input**: Project folder, optional URI/scope constraints
- **Output**: Markdown with embedded dependency graphs, data flow, UML models
- **Key Features**:
  - AST parsing (Python focus; Swift/Go/Kotlin via markers)
  - Import graph extraction with external classification
  - Mermaid graph generation (cluster, sequence, class, state, use-case)
  - UML model extraction (HTTP methods, async arrow detection)
  - Purpose guessing from code structure
  - LaTeX/Lean support and non-UTF8 filtering
  - Node limit enforcement to prevent runaway graphs

## Extracted Skills & Integration

The four tools in megaprompter map directly to four new skills in the `thistleknot/skills` library:

| Megaprompter Tool | Extracted Skill | Purpose |
|---|---|---|
| megaprompt | `code-extraction` | Extract source files + configs into markdown artifact (docling-style) |
| megadiagnose | `diagnostic-scanner` | Language-aware tool invocation and error normalization |
| megatest | `test-planner` | Coverage-aware test plan generation with regression detection |
| megadoc | `doc-synthesizer` | AST-based documentation with Mermaid diagrams |

## Implementation Details

All four skills follow the **docling-style extraction pattern**:
1. **Parse**: Analyze project structure, detect language, collect artifacts
2. **Normalize**: Standardize into semantic blocks (sections, code listings, tables)
3. **Markdown + JSON**: Output human-readable markdown with embedded JSON metadata for machine parsing

### Shared Foundation (`utils.py`)
- Project detection via marker files or 8+ source files
- Language classification (Python, Go, Rust, Swift, Java, JS/TS, Kotlin, Kotlin)
- File content truncation (default 8KB per file)
- Markdown artifact formatting (headers, code fences, tables)
- Pydantic schema validation for output artifacts

### Configuration Convention
All skills use a configuration dict at module init:
```python
{
    "max_artifact_lines": 5000,
    "max_file_bytes": 8192,
    "supported_languages": ["python", "go", "rust", "swift", "java", "javascript", "typescript", "kotlin"],
    "error_severity_threshold": "warning",
    "timeout_seconds": 30,
}
```

## Integration with Skill Graph

All four skills are registered in the execution/ branch of the skill graph (README.md):

- **code-extraction**: Feeds `codebase-knowledge-graph`, `documentation`, LLM context assembly
- **diagnostic-scanner**: Feeds `validation` and `code` for violation handling
- **test-planner**: Feeds `tdd-agent` and `validation` for coverage verification
- **doc-synthesizer**: Feeds `documentation`, `codebase-knowledge-graph`, architecture review

## Phase 2 Extensions

Planned enhancements (not implemented in Phase 1):
- Go, Rust, Swift, Java full AST parsing (Phase 1: markers only)
- Real pytest/go test/cargo test discovery and coverage parsing
- URI fetching and crawling in doc-synthesizer
- Caching layer for repeated runs
- Integration testing on large real-world projects

## References

- **Docling Paper**: Docling: https://github.com/ds4sd/docling
- **Phase 1 Implementation**: Implemented in Python, Markdown+Mermaid output, tested on mock projects
- **Shared Utils**: `code-extraction/utils.py` (also copied to diagnostic-scanner/, test-planner/, doc-synthesizer/)
