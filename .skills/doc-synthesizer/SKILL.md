---
name: doc-synthesizer
description: Code analysis, dependency visualization, and optional URI fetch/crawl. Produces AST-based documentation with Mermaid diagrams for module dependencies and data flow. Use when generating project docs, architecture diagrams, or onboarding artifacts.
status: active
last_validated: 2026-05-04
supersedes: []
validation_method: session
---
# doc-synthesizer Skill

Code analysis + dependency visualization + optional URI fetch/crawl. Produces AST-based documentation with Mermaid diagrams showing module dependencies, data flow, and external integrations. Outputs markdown artifact with embedded JSON metadata.

## Trigger Conditions

Invoke when:
- Generating comprehensive project documentation from code
- Visualizing module dependencies and data flow
- Creating onboarding/overview documentation for new team members
- Building architecture diagrams from live codebase

## Contract

**Require** (preconditions):
- Valid project directory with language detection
- AST parsing tools available (ast module for Python, equivalent for other languages)
- Optional: URI fetch/crawl requires internet access

**Guarantee** (postconditions):
- Output: Markdown artifact with project overview, module tree, dependency graphs, and Mermaid diagrams
- Diagrams generated in Mermaid format (not ASCII UML, not PlantUML)
- All module dependencies extracted and visualized
- External integrations (DB, FS, HTTP) identified and labeled
- JSON metadata includes module count, dep count, data sources

**Maintain** (invariants):
- Dependency graph is acyclic or circular deps are flagged
- Data flow diagrams are accurate (entry points → resources)
- Module summaries are extracted from docstrings or code hints

**Assert** (checkpoints):
- Project structure is parseable (no syntax errors block analysis)
- All modules are reachable from project root
- Mermaid diagrams are well-formed (no unclosed nodes)

## Configuration

```python
# Local analysis only
synth.synthesize(
    project_path="/path/to/project",
    include_io=True,
    include_endpoints=True
)

# With URI fetch/crawl
synth.synthesize(
    project_path="/path/to/project",
    fetch_uris=["https://docs.example.com/api"],
    crawl_depth=2,
    allow_domains=["docs.example.com"]
)

# Custom diagram options
synth.synthesize(
    project_path="/path/to/project",
    diagram_format="mermaid",
    max_nodes=100
)
```

## Diagram Types

| Diagram | Purpose | Shows |
|---------|---------|-------|
| **Dependency Graph** | Module → module relationships | Import chains, circular deps |
| **Data Flow** | Entry points → resources | HTTP → DB, FS, external APIs |
| **Component Diagram** | Packages + external deps | Architecture overview |

## Usage in Agentic Workflows

**Pattern 1: Onboarding Documentation**
```python
# Generate documentation → deliver to new team member
doc = synth.synthesize(repo_path)
send_to_slack(doc.markdown + "\n\nStart here: " + doc.entry_points[0])
```

**Pattern 2: Architecture Review**
```python
# Synthesize → analyze for issues (circular deps, tight coupling)
doc = synth.synthesize(repo_path)
circular = doc.circular_dependencies
tight_coupling = doc.high_fan_in_modules
```

**Pattern 3: Integration Discovery**
```python
# Identify external services
doc = synth.synthesize(repo_path)
for source in doc.data_sources:
    if source.type == "HTTP":
        endpoints.append(source.url)
```

## Output Schema

```markdown
# Documentation Synthesis Report

## Project Overview
**Language**: Python  
**Purpose**: A flexible REST API framework for building microservices.

## Directory Structure
\`\`\`
project/
├── api/
│   ├── __init__.py
│   ├── server.py (192 lines)
│   ├── routes.py (256 lines)
│   └── middleware.py (89 lines)
├── models/
│   ├── __init__.py
│   ├── user.py (78 lines)
│   └── database.py (145 lines)
├── tests/
│   └── test_api.py
├── README.md
└── requirements.txt
\`\`\`

## Module Dependencies
\`\`\`mermaid
graph LR
    A[api.server] --> B[models.database]
    A --> C[api.routes]
    A --> D[api.middleware]
    C --> B
    B --> E[sqlalchemy]
    A --> F[fastapi]
    C --> F
\`\`\`

## Data Flow
\`\`\`mermaid
graph TB
    Client["HTTP Client"]
    Client -->|GET /users| API["api.server"]
    API -->|query| DB["PostgreSQL"]
    DB -->|result| API
    API -->|200 JSON| Client
\`\`\`

## Module Summaries

### api/server.py
- **Purpose**: FastAPI application entry point
- **Entry Points**: create_app() → FastAPI
- **Dependencies**: fastapi, api.middleware
- **Key Classes**: AppConfig

### models/database.py
- **Purpose**: SQLAlchemy ORM + session management
- **Entry Points**: Session, engine
- **Dependencies**: sqlalchemy, models.user
- **External Data**: PostgreSQL

### [Additional modules...]

## External Dependencies
- fastapi (web framework)
- sqlalchemy (ORM)
- pydantic (validation)
- pytest (testing)

## Data Sources
| Source | Type | Purpose |
|--------|------|---------|
| PostgreSQL | Database | User + order storage |
| Redis | Cache | Session caching |
| Stripe API | HTTP | Payment processing |

## Metadata
\`\`\`json
{
  "artifact_type": "documentation",
  "language": "python",
  "module_count": 6,
  "external_deps": 4,
  "data_sources": 3,
  "diagram_format": "mermaid",
  "timestamp": "ISO8601"
}
\`\`\`

## Provenance
\`\`\`json
{
  "analysis_method": "AST parse + import extraction",
  "crawled_uris": [],
  "includes_io": true,
  "circular_dependencies": false
}
\`\`\`
```

## Related Skills

- `codebase-knowledge-graph` — Deeper dependency and structure analysis
- `documentation` — For artifact curation and formatting
- `architecture` — For module/component mapping
- `deep-research` — For URI fetch/crawl augmentation

## Worked Examples

**Example 1: Microservice**
Input: Go microservice with 12 modules
Output: Dependency graph, data flow (HTTP → PostgreSQL → Redis), 3 entry points
Diagrams: Mermaid (graph LR for deps, graph TB for data flow)

**Example 2: Python Package**
Input: NumPy-like computation library
Output: Module tree, 8 external deps (numpy, scipy), no external IO
Diagrams: Pure dependency graph (no data flow to external services)

## Failure Modes

| Failure | Cause | Recovery |
|---------|-------|----------|
| Syntax error blocks parsing | Invalid code in project | Report file + line, skip module |
| Circular dependency detected | Modules import each other | Flag in artifact, document cycle |
| URI fetch fails | Network error or invalid URL | Log warning, continue with local analysis |
| Mermaid syntax error | Too many nodes or malformed deps | Reduce max_nodes or simplify diagram |
<!-- consolidation:see-also:start -->
## See Also
[[code]]  [[simplify]]  [[checklist]]
<!-- consolidation:see-also:end -->
