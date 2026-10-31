# History

## 2026-10-30 — debugging-and-error-recovery consolidated

- Canonicalized the overlapping root-cause workflow in `debugging/SKILL.md`.
- Migrated compact operational triage: reproduction evidence, failure classification, narrow diagnostics, untrusted error text, reversible rollback, and regression/resume checks.
- Superseded `debugging-and-error-recovery`; its full prior contract is preserved in `references/error-recovery-2026-10-30.md`.
- Basis: both skills covered root-cause triage; existing library callers route to `debugging`.
