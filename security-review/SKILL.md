---
name: security-review
description: >
  Codebase security scanning protocol: STRIDE-A threat modeling, OWASP Top 10
  for LLMs and web apps, data-flow tracing to sinks, secret/credential detection,
  CVE dependency audit, and incremental update mode. Use before any deployment
  or when a codebase handles untrusted input, authentication, or sensitive data.
  Includes threat-model-analyst sub-pattern.
status: active
last_validated: 2026-04-28
---

# Security Review

## When to Use

Run a security review when:

- Any new code path handles **untrusted input** (user data, external API responses, file uploads)
- Authentication, authorization, or session management is modified
- New **external dependencies** are added (CVE exposure)
- Sensitive data (PII, credentials, financial records) is read, stored, or transmitted
- A new **agent tool** is registered (potential for prompt injection or excessive agency)
- Before any **production deployment**

---

## Review Scope

Define scope before starting. Over-broad reviews produce noise; under-broad reviews miss risks.

| Scope type | What to cover |
|---|---|
| Full codebase | All trust boundaries, data flows, dependencies |
| Feature delta | Only changed files + their upstream/downstream data flows |
| Dependency audit | Third-party packages only |
| LLM agent | Prompt injection, tool access, output sanitization, excessive agency |

For incremental reviews (PR-gated): focus on changed files + explicit data-flow traces from those changes to security-sensitive sinks.

---

## STRIDE-A Threat Modeling

For each trust boundary in the system, enumerate threats:

| Threat | Question to ask | Mitigation class |
|---|---|---|
| **S**poofing | Can an attacker impersonate a user or service? | Authentication, token validation |
| **T**ampering | Can an attacker modify data in transit or at rest? | Integrity checks, signing, HTTPS |
| **R**epudiation | Can an actor deny having taken an action? | Audit logs, non-repudiation tokens |
| **I**nformation Disclosure | Can sensitive data leak to unauthorised parties? | Encryption, access control, output sanitization |
| **D**enial of Service | Can an attacker exhaust resources? | Rate limiting, input size caps, circuit breakers |
| **E**levation of Privilege | Can a lower-trust principal gain higher-trust access? | Least privilege, trust-tier enforcement |
| **A**gent Misuse *(LLM extension)* | Can a prompt cause an agent to take unintended actions? | Intent classification, tool guardian, sandboxing |

Map each identified threat to a severity (Critical/High/Medium/Low) and a mitigation.
Unmitigated Critical threats block deployment.

---

## OWASP Top 10 for LLM Applications (2025)

| # | Vulnerability | Check |
|---|---|---|
| LLM01 | Prompt Injection | Is untrusted text ever injected into a system prompt or tool argument? |
| LLM02 | Insecure Output Handling | Is LLM output passed to a shell, DB query, or eval without sanitization? |
| LLM03 | Training Data Poisoning | Are fine-tuning datasets sourced from untrusted inputs? |
| LLM04 | Model DoS | Is there a budget cap on tokens per request? |
| LLM05 | Supply-Chain Vulnerabilities | Are model weights or adapters from unverified sources? |
| LLM06 | Sensitive Information Disclosure | Can the model reveal training data, system prompts, or PII? |
| LLM07 | Insecure Plugin Design | Do plugins validate inputs and enforce least privilege? |
| LLM08 | Excessive Agency | Can the agent take high-impact actions without human approval? |
| LLM09 | Overreliance | Are agent outputs used in critical decisions without human review? |
| LLM10 | Model Theft | Are model endpoints protected against extraction attacks? |

---

## Data-Flow Tracing to Sinks

Trace every input from its **source** to its **sink**. Flag paths where untrusted data
reaches a dangerous sink without sanitization.

```
Source types (untrusted unless proven otherwise):
  HTTP request body / query params / headers
  File uploads
  Database reads (if populated from external input)
  LLM output
  Environment variables (if user-controlled)
  External API responses

Dangerous sinks:
  SQL query construction  →  injection risk
  Shell command arguments  →  command injection
  HTML template rendering  →  XSS
  File path construction  →  path traversal
  eval() / exec()  →  code injection
  Deserialization  →  object injection
  LLM system prompt  →  prompt injection
```

For each source→sink path: verify a sanitization or parameterization step exists.

---

## Secret and Credential Detection

Run regex patterns over the diff and full codebase:

```python
SECRET_PATTERNS = {
    "generic_api_key": r"(?i)(api[_-]?key|secret|password|token|bearer)\s*[=:]\s*['\"]?[\w\-]{16,}",
    "openai_key":      r"sk-[a-zA-Z0-9]{32,}",
    "github_pat":      r"ghp_[a-zA-Z0-9]{36}",
    "aws_access_key":  r"AKIA[0-9A-Z]{16}",
    "private_key_pem": r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
    "connection_string": r"(postgresql|mysql|mongodb|redis):\/\/[^:]+:[^@]+@",
}
```

Any match in committed code is a Critical finding. Remove the secret, rotate the
credential, and rewrite git history (or force-push if allowed by policy).

Integrate into the pre-commit hook and CI pipeline. See `agent-governance` for the
agent-as-CI-gate pattern.

---

## CVE Dependency Audit

```bash
# Python
pip-audit --output json > audit.json

# JavaScript / Node
npm audit --json > audit.json

# Go
govulncheck ./... > audit.txt
```

Triage findings:
- **Critical/High CVE on a direct dependency**: block deployment; update or replace
- **Medium CVE**: create a tracked remediation ticket; update within the sprint
- **Low CVE or transitive dependency**: document; update at next dependency refresh

---

## Findings Schema

All security findings are structured for machine-readable output:

```python
class SecurityFinding(BaseModel):
    finding_id: str                              # ULID
    category: Literal["stride", "owasp_llm", "owasp_web", "secret", "cve", "data_flow"]
    severity: Literal["critical", "high", "medium", "low", "info"]
    title: str
    description: str
    affected_location: str                       # file:line or component name
    threat_actor: str | None                     # who could exploit this
    impact: str                                  # what an attacker gains
    mitigation: str                              # specific fix, not "sanitize input"
    cve_id: str | None                           # if applicable
    blocking: bool                               # True = blocks deployment

class SecurityReviewReport(BaseModel):
    run_id: str
    scope: str
    findings: list[SecurityFinding]
    blocking_count: int
    deployment_gate: Literal["pass", "fail"]     # fail if any blocking finding exists
```

---

## Incremental Mode (PR-Gated)

For PR reviews, scope the analysis to the diff:

1. Extract changed files from `git diff --name-only base..head`
2. For each changed file, trace data flows to security-sensitive sinks
3. Run secret scanner on the diff only
4. Check if any changed dependency has new CVEs
5. Run LLM01/LLM02/LLM08 checks if agent code changed
6. Produce a `SecurityReviewReport`; fail the PR if `deployment_gate == "fail"`

---

## Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| Prompt injection in agent tool args | LLM output passed to tool without validation | Sanitize or parametrize; never interpolate LLM output into shell/SQL |
| Secret committed to repo | No pre-commit hook | Add secret scanner to pre-commit + CI; rotate immediately |
| High CVE ignored for weeks | No deployment gate | Gate deployments on `pip-audit` / `npm audit` in CI |
| STRIDE analysis misses a trust boundary | Diagram not updated after refactor | Re-run STRIDE on every architectural change, not just new features |
| LLM agent takes destructive action | Excessive agency (LLM08) | Apply `agent-governance` trust tiers + tool guardian |

---

## Evidence

- OWASP Top 10 for LLM Applications 2025: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- STRIDE threat model: Microsoft SDL (2002), widely adopted
- awesome-copilot: `security-review` skill + `threat-model-analyst` skill
- Anthropic Claude Code: sandboxing and tool-access controls documentation (2025)
<!-- consolidation:see-also:start -->
## See Also
[[agent-governance]]  [[agentic-harness]]  [[openspec-workflow]]
<!-- consolidation:see-also:end -->
