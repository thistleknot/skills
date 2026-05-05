---
name: test-planner
description: Coverage-aware test plan generation. Identifies testable subjects, analyzes existing coverage, proposes scenarios by level (smoke/unit/integration/e2e/regression), and flags coverage status. Use when planning test suites or identifying coverage gaps.
status: active
last_validated: 2026-05-04
supersedes: []
validation_method: session
---
# test-planner Skill

Coverage-aware test plan generation. Identifies testable subjects, analyzes existing test coverage, proposes concrete scenarios by level (smoke/unit/integration/e2e/regression), and flags coverage status (green/yellow/red). Produces markdown artifact with embedded JSON metadata.

## Trigger Conditions

Invoke when:
- Planning comprehensive test suite for a project
- Identifying coverage gaps (red/yellow/green status)
- Detecting regression test needs (git diff-based)
- Building test prioritization by coverage level

## Contract

**Require** (preconditions):
- Valid project directory with language detection
- Test discovery tools available (pytest, go test, cargo test, etc.)
- Optional: git repository for regression detection

**Guarantee** (postconditions):
- Output: Markdown artifact with testable subjects ranked by coverage status
- Coverage status: 🟢 GREEN (DONE), 🟡 YELLOW (PARTIAL), 🔴 RED (MISSING)
- Each subject has concrete scenario proposals by test level
- Regression subjects flagged if git refs provided
- JSON metadata includes coverage metrics

**Maintain** (invariants):
- Coverage status is accurate (matches actual test discovery)
- Scenario proposals are concrete and actionable
- Regression detection only triggers on changed subjects

**Assert** (checkpoints):
- Test discovery completes successfully
- All subjects are classified with coverage status
- Regression analysis (if enabled) compares valid git refs

## Configuration

```python
# Basic test plan
planner.generate_plan(
    project_path="/path/to/project",
    levels=["smoke", "unit", "integration"]
)

# With regression detection
planner.generate_plan(
    project_path="/path/to/project",
    regression_since="origin/main",
    levels=["smoke", "unit", "integration", "regression"]
)

# Custom regression range
planner.generate_plan(
    project_path="/path/to/project",
    regression_range="HEAD~3..HEAD",
    levels=["regression"]
)
```

## Test Levels

| Level | Scope | Examples |
|-------|-------|----------|
| **smoke** | Happy path only | Successful login, valid GET request |
| **unit** | Isolated function + edge cases | All branches, boundary values, error paths |
| **integration** | Module interactions | API + database, auth + permissions |
| **e2e** | Full workflow | User registration → login → action → logout |
| **regression** | Changed subjects only | Re-verify previous passing scenarios |

## Coverage Status

| Status | Meaning | Action |
|--------|---------|--------|
| 🟢 GREEN | Adequate tests found | Non-regression scenarios suppressed |
| 🟡 YELLOW | Some coverage exists | Suggestions kept, prioritized |
| 🔴 RED | No tests found | Full scenario suggestions provided |

## Usage in Agentic Workflows

**Pattern 1: Coverage Analysis**
```python
# Generate plan → analyze coverage gaps
plan = planner.generate_plan(repo_path)
red_subjects = [s for s in plan.subjects if s.coverage == "RED"]
print(f"Missing coverage: {len(red_subjects)} subjects")
```

**Pattern 2: Regression Testing**
```python
# Generate regression plan for changed files
plan = planner.generate_plan(
    repo_path,
    regression_since="origin/main"
)
regression_tests = [s for s in plan.subjects if s.regression]
```

**Pattern 3: Test Prioritization**
```python
# Prioritize by coverage + regression
prioritized = sorted(
    plan.subjects,
    key=lambda s: (s.regression, s.coverage != "GREEN")
)
```

## Output Schema

```markdown
# Test Plan Report

## Overview
- **Coverage Status**:
  - 🟢 Green (DONE): 12 subjects
  - 🟡 Yellow (PARTIAL): 8 subjects
  - 🔴 Red (MISSING): 15 subjects
- **Total Subjects**: 35
- **Regression Subjects**: 3

## Coverage by Module

### Module: src/auth.py

#### 🟢 authenticate(username, password) → bool
**Status**: DONE (existing: test_auth.py:12, test_auth.py:34)
- ✅ Valid credentials
- ✅ Invalid password
- ✅ Nonexistent user
*Non-regression scenarios suppressed (coverage adequate)*

#### 🟡 reset_password(email) → bool
**Status**: PARTIAL (existing: test_auth.py:56)
**Suggested Scenarios**:
- **Smoke**: Happy path (valid email)
- **Unit**: Invalid format, unregistered email, DB failure
- **Integration**: Email service unavailable

#### 🔴 MFA.verify_otp(code) → bool
**Status**: MISSING (no tests)
**Suggested Scenarios**:
- **Smoke**: Valid OTP code
- **Unit**: Expired OTP, invalid format, replay attack
- **Integration**: TOTP service unavailable
- **E2E**: Full 2FA flow with session

### [Additional modules...]

## Metadata
\`\`\`json
{
  "artifact_type": "test_plan",
  "total_subjects": 35,
  "coverage_green": 12,
  "coverage_yellow": 8,
  "coverage_red": 15,
  "regression_subjects": 3,
  "timestamp": "ISO8601"
}
\`\`\`

## Provenance
\`\`\`json
{
  "regression_ref": "origin/main",
  "changed_files": ["src/api.py", "src/models.py"],
  "test_discovery": "pytest --collect-only"
}
\`\`\`
```

## Related Skills

- `tdd-agent` — For iterative test-driven implementation
- `validation` — For test coverage verification
- `checklist` — For test case tracking
- `code` — For complexity/risk analysis

## Worked Examples

**Example 1: REST API**
Input: Flask app with partial test coverage
Output: 20 subjects; 8 GREEN, 5 YELLOW, 7 RED
Regression: POST /users endpoint changed (3 scenarios needed)

**Example 2: Data Processing Pipeline**
Input: Pandas-based ETL with high test coverage
Output: 15 subjects; 12 GREEN, 2 YELLOW, 1 RED
Regression: None (no changes since last merge)

## Failure Modes

| Failure | Cause | Recovery |
|---------|-------|----------|
| Test discovery fails | Tool not in PATH or broken config | Continue with manual review |
| Git diff fails | Not a git repo or invalid refs | Skip regression detection |
| No subjects found | Empty codebase or detection failure | Report and exit cleanly |
| Subject mismatch | Tests don't align with subjects | Report coverage as uncertain |