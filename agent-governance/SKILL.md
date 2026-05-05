---
name: agent-governance
description: >
  Safety rails, policy-based tool-access controls, audit trail, trust scoring,
  and semantic intent classification for agent actions. Use whenever an agent
  can take destructive, irreversible, or high-blast-radius actions. Covers
  policy design, tool guardian pattern, audit logging, trust tiers, and
  CI-gate integration. Parent skill for agent-as-ci-gate.
status: active
last_validated: 2026-04-28
---

# Agent Governance

## When to Use

Apply governance whenever an agent can:

- **Delete, overwrite, or publish** files, records, or data
- **Execute shell commands** with elevated privileges or broad file-system access
- **Call external APIs** that have rate limits, billing implications, or data-exfiltration risk
- **Trigger deployments** or infrastructure changes
- **Act on behalf of a user** in a multi-tenant environment

Governance is not optional for production agents. The cost of a single uncontrolled
destructive action exceeds the overhead of the entire governance layer.

---

## Policy Design

Policies are source-controlled markdown files. They are not hard-coded in agent logic.

```
.governance/
  policies/
    tool-access.md       # which tools each agent role may call
    data-classification.md  # what data classes agents may read/write
    blast-radius.md      # maximum scope of any single action
    audit-retention.md   # how long audit records are kept
  hooks/
    pre-action.md        # checks run before any tool call
    post-action.md       # logging + side-effects after any tool call
```

**Policy authoring rules:**
- Every policy has a `scope:` (which agents it applies to) and an `effect:` (ALLOW / DENY)
- Policies are deny-by-default: if no ALLOW policy matches, the action is blocked
- Policy changes require a pull request with at least one human reviewer

---

## Tool Guardian Pattern

A tool guardian intercepts every tool call and evaluates it against active policies
before the tool executes.

```python
class ToolGuardian:
    """
    Require: policies are loaded and valid; tool_call is well-formed.
    Guarantee: blocked calls never reach the underlying tool; every call is logged.
    Maintain: policy evaluation is stateless per call (no side effects in guardian).
    """

    def __init__(self, policy_set: PolicySet, audit_log: AuditLog):
        self.policies = policy_set
        self.audit = audit_log

    def intercept(self, agent_id: str, tool_name: str, args: dict) -> GuardianVerdict:
        intent = self._classify_intent(tool_name, args)
        verdict = self.policies.evaluate(agent_id, tool_name, intent, args)

        self.audit.record(AuditEntry(
            entry_id=str(ULID()),
            agent_id=agent_id,
            tool_name=tool_name,
            intent=intent,
            verdict=verdict.effect,
            args_hash=sha256(json.dumps(args, sort_keys=True).encode()).hexdigest(),
            timestamp=datetime.utcnow(),
        ))

        if verdict.effect == "DENY":
            raise ToolAccessDenied(
                f"Agent '{agent_id}' denied access to '{tool_name}': {verdict.reason}"
            )
        return verdict
```

**Args are hashed, not stored raw** — prevents secrets from leaking into audit logs.

---

## Semantic Intent Classification

Classify the intent of each tool call before policy evaluation. This enables policies
to express intent-level rules ("deny any file deletion outside the project root") rather
than enumerating every possible argument value.

```python
class Intent(str, Enum):
    READ_ONLY     = "read_only"       # no state change
    WRITE_LOCAL   = "write_local"     # writes within the project directory
    WRITE_SYSTEM  = "write_system"    # writes outside project directory
    DELETE        = "delete"          # any deletion
    NETWORK_READ  = "network_read"    # outbound reads (no data sent)
    NETWORK_WRITE = "network_write"   # outbound writes (data exfiltration risk)
    EXEC          = "exec"            # arbitrary code/shell execution
    ESCALATE      = "escalate"        # privilege escalation attempt

DANGEROUS_INTENTS = {Intent.DELETE, Intent.WRITE_SYSTEM, Intent.EXEC, Intent.ESCALATE}
```

An intent classifier inspects `tool_name` and `args` and returns an `Intent`. For
pattern-based classification (most tools), a lookup table suffices. For novel tool calls,
use an LLM classifier with a structured output schema.

---

## Trust Tiers

Not all agents deserve the same access level. Trust is earned, not granted by default.

| Tier | Label | Example | Allowed Intents |
|---|---|---|---|
| T0 | Untrusted | External input, user-provided agents | READ_ONLY |
| T1 | Limited | Newly spawned sub-agents | READ_ONLY, WRITE_LOCAL |
| T2 | Standard | Vetted worker agents | READ_ONLY, WRITE_LOCAL, NETWORK_READ |
| T3 | Privileged | Orchestrator, CI pipeline agents | All except ESCALATE |
| T4 | Admin | Human-in-the-loop override only | All |

Trust tier is assigned at agent spawn time and cannot be self-elevated. Escalation
requests must route to a human approval gate.

---

## Audit Trail

Every action — allowed or denied — is logged. The audit log is append-only, tamper-evident.

```python
class AuditEntry(BaseModel):
    entry_id: str           # ULID
    agent_id: str
    tool_name: str
    intent: Intent
    verdict: Literal["ALLOW", "DENY"]
    args_hash: str          # SHA-256 of serialised args — no raw secrets
    session_id: str
    task_id: str | None
    timestamp: datetime

class AuditLog:
    """Write-once log. Read for compliance review; never deleted in retention window."""
    def record(self, entry: AuditEntry) -> None: ...
    def query(self, agent_id: str = None, intent: Intent = None,
              since: datetime = None) -> list[AuditEntry]: ...
```

Audit records are retained per `audit-retention.md` policy (default: 90 days).

**What to surface in monitoring:**
- DENY rate per agent — sudden spike = policy misconfiguration or adversarial prompt
- DANGEROUS_INTENTS rate — should be rare; alert if > 5% of a session's calls
- New tool names (not in classifier lookup) — require human review before next session

---

## Secrets Scanner

Run a secrets scan on every agent output before it is committed or transmitted:

```python
SECRETS_PATTERNS = [
    r"(?i)(api[_-]?key|secret|password|token|bearer)\s*[=:]\s*['\"]?[\w\-]{16,}",
    r"sk-[a-zA-Z0-9]{32,}",          # OpenAI-style keys
    r"ghp_[a-zA-Z0-9]{36}",          # GitHub PATs
    r"AKIA[0-9A-Z]{16}",             # AWS access key IDs
]

def scan_for_secrets(text: str) -> list[str]:
    """Returns list of matched patterns found. Empty = clean."""
    return [p for p in SECRETS_PATTERNS if re.search(p, text)]
```

Block any output that triggers a secrets match. Log the event (not the matched value).

---

## Agent-as-CI-Gate (Sub-Pattern)

AI quality checks expressed as source-controlled markdown, enforceable as GitHub
status checks. See `agent-as-ci-gate` section below.

```
PR opened / updated
    │
    ▼
governance-audit hook
    ├─ secrets scan on diff
    ├─ policy compliance check (blast-radius, tool-access)
    └─ agent-level check: run AI reviewer against diff
           │
           ├─ PASS  →  GitHub check "AI governance" ✓
           └─ FAIL  →  GitHub check "AI governance" ✗  (blocks merge)
```

Define checks in `.governance/checks/`:

```markdown
# .governance/checks/secrets-scan.md
name: secrets-scan
trigger: pull_request
command: python governance/scan.py --diff $PR_DIFF
pass_condition: exit_code == 0
blocking: true
```

---

## Agent-as-CI-Gate: Full Protocol

AI-defined quality checks that run as GitHub CI status checks, blocking merge
on failure. The checks are source-controlled markdown; the enforcement is GitHub Actions.

### Check Definition Format

```markdown
# .governance/checks/<check-name>.md
name: <check-name>                 # used as GitHub status check name
trigger: pull_request | push | schedule
scope: diff | full                 # diff = only changed files; full = entire repo
command: <shell command>           # receives PR_DIFF, REPO_ROOT, COMMIT_SHA as env vars
pass_condition: exit_code == 0     # or: json_field("score") >= 0.85
blocking: true | false             # true = required status check; false = advisory
timeout_seconds: 120
```

### GitHub Actions Workflow

```yaml
# .github/workflows/ai-governance.yml
name: AI Governance Checks
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  run-governance-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Get PR diff
        run: git diff origin/${{ github.base_ref }}...HEAD > /tmp/pr.diff
        env:
          PR_DIFF_PATH: /tmp/pr.diff

      - name: Run governance checks
        run: |
          python governance/run_checks.py \
            --checks-dir .governance/checks/ \
            --diff /tmp/pr.diff \
            --output governance_report.json

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: governance-report
          path: governance_report.json

      - name: Enforce blocking checks
        run: python governance/enforce.py --report governance_report.json
```

### Check Runner

```python
class GovernanceCheck(BaseModel):
    name: str
    trigger: str
    scope: Literal["diff", "full"]
    command: str
    pass_condition: str
    blocking: bool
    timeout_seconds: int = 120

class CheckResult(BaseModel):
    check_name: str
    passed: bool
    exit_code: int
    output: str
    blocking: bool

def run_checks(
    checks_dir: Path,
    diff_path: Path,
    repo_root: Path,
) -> list[CheckResult]:
    """
    Require: checks_dir contains valid .md check definitions.
    Guarantee: all checks run; failures in non-blocking checks do not raise.
    Maintain: blocking check failures are collected and raised at the end.
    """
    checks = [parse_check(f) for f in checks_dir.glob("*.md")]
    results = []
    for check in checks:
        env = {
            "PR_DIFF": str(diff_path),
            "REPO_ROOT": str(repo_root),
        }
        try:
            proc = subprocess.run(
                check.command, shell=True, env={**os.environ, **env},
                capture_output=True, text=True, timeout=check.timeout_seconds
            )
            passed = _evaluate_pass_condition(check.pass_condition, proc)
        except subprocess.TimeoutExpired:
            passed = False
            proc = SimpleNamespace(returncode=124, stdout="", stderr="timeout")
        results.append(CheckResult(
            check_name=check.name,
            passed=passed,
            exit_code=proc.returncode,
            output=proc.stdout[:2000],
            blocking=check.blocking,
        ))

    blocking_failures = [r for r in results if not r.passed and r.blocking]
    if blocking_failures:
        names = [r.check_name for r in blocking_failures]
        raise SystemExit(f"Blocking governance checks failed: {names}")
    return results
```

### Built-In Check Library

| Check | Command | Blocks |
|---|---|---|
| `secrets-scan` | `python governance/scan.py --diff $PR_DIFF` | ✅ |
| `policy-compliance` | `python governance/policy.py --diff $PR_DIFF` | ✅ |
| `ai-code-review` | `python governance/ai_review.py --diff $PR_DIFF` | ✅ (blocking on HIGH severity) |
| `dependency-audit` | `pip-audit -r requirements.txt` / `npm audit --audit-level=high` | ✅ |
| `eval-regression` | `python eval/run_eval.py --threshold 0.85` | ✅ |
| `blast-radius-check` | `python governance/blast_radius.py --diff $PR_DIFF` | advisory |

### Registering as Required Status Checks

In GitHub repository settings → Branch protection rules → Required status checks:
add `AI Governance Checks / run-governance-checks`.

**This turns governance into a merge gate.** No PR can merge if the governance
workflow fails on a blocking check.

### Incremental Adoption Path

1. Start with `blocking: false` for all new checks — observe without blocking
2. After 2 weeks of clean runs with no false positives, flip to `blocking: true`
3. Add each check via its own PR (not all at once) — easier rollback if noisy
4. Policy files in `.governance/` get CODEOWNERS rule: require human review for changes

---

## Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| Guardian blocks all tool calls | Deny-by-default with no ALLOW policies loaded | Load policy files before agent starts |
| Audit log fills with DENY for harmless tools | Intent classifier mis-classifies | Update intent lookup table; add test cases |
| Agent self-elevates trust tier | No CAS on trust assignment | Enforce trust tier as immutable after spawn |
| Secrets leak through args hash | Args logged raw somewhere else | Audit all log sinks; hash at the earliest intercept point |
| Policy changes bypass review | No PR gate on `.governance/` | Add CODEOWNERS rule + required review for `.governance/` |

---

## Evidence

- awesome-copilot: `governance-audit` hook, `tool-guardian` hook, `secrets-scanner` hook, `agent-governance` skill
- Anthropic Claude Code documentation: tool-access control and sandboxing patterns (2025)
- Microsoft Responsible AI Standard: audit trail, intent classification, escalation gates
- OWASP Top 10 for LLMs (2025): prompt injection, insecure tool use, excessive agency
<!-- consolidation:see-also:start -->
## See Also
[[security-review]]  [[agentic-harness]]  [[checklist]]
<!-- consolidation:see-also:end -->
