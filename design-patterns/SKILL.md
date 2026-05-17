---
name: design-patterns
description: >
  Pattern-selection protocol for code and architecture work. Use when choosing
  or refactoring around GoF patterns, programming contracts, or Pragmatic
  Programmer tradeoffs. Treat this as a code sub-skill: select the lightest
  pattern that fits the actual constraint, then encode
  Require/Guarantee/Maintain/Assert at the interface.
status: active
last_validated: 2026-04-29
supersedes: []
validation_method: session
---
# Design Patterns

## Role
This skill sits under code work. Use it when a change stops being a local edit and becomes a relationship-shape problem: object creation, interface mismatch, state-driven behavior, algorithm switching, or contract definition.

## Selection Filter
- Start from the pressure, not the pattern name.
- Prefer no pattern over the wrong pattern.
- If one function and one call site solve it, stop there.
- Introduce a pattern only when it removes repeated creation logic, interface mismatch, cross-cutting behavior, or behavior/state branching.

## Pattern Families
- **Creational** — Factory Method, Abstract Factory, Builder, Prototype, Singleton
- **Structural** — Adapter, Decorator, Facade, Composite, Proxy
- **Behavioral** — Observer, Strategy, Command, Template Method, State

## Contracts
- **Require** — caller preconditions
- **Guarantee** — implementation postconditions
- **Maintain** — invariants that stay true
- **Assert** — execution-point checks at boundaries

## Pragmatic Principles
- DRY and orthogonality before cleverness
- tracer bullets before elaborate abstraction
- plain text and readable interfaces over opaque magic
- systematic debugging over coincidence
- gather real requirements before abstracting

## State Machine / Compiler Pattern (Agentic Systems)

Use this pattern when an automated agent pipeline must be deterministic and tamper-resistant.

**Problem:** A conversational loop allows the agent to choose its next step, self-report completion, and reinterpret ambiguous directives — each decision is a branch in a non-deterministic system.

**Solution:** Replace the loop with a state machine where:
- State transitions are triggered by external tool validation, not the model's self-assessment
- Each transition condition is binary (pass/fail), not a judgement call
- The model is the compiler (transforms inputs to outputs); the harness is the linker (sequences, gates, and certifies)

```
[State N] → run_external_validator() → pass: advance to [State N+1]
                                      → fail: retry or escalate
```

Applies **State** pattern (behavioral GoF) plus **Template Method** for the gate sequence.
Distinct from a simple pipeline: the key property is that the agent never self-reports what state it is in.

## Working Rule
Use this skill with `code`: `code` owns the edit mechanics; `design-patterns` chooses the relationship shape and contract.
<!-- consolidation:see-also:start -->
## See Also
[[architecture]]  [[codebase-knowledge-graph]]  [[agentic-design-patterns]]  [[code]]  [[agentic-harness]]
<!-- consolidation:see-also:end -->
