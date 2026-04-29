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
