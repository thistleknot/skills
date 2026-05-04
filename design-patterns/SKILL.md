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

## Working Rule
Use this skill with `code`: `code` owns the edit mechanics; `design-patterns` chooses the relationship shape and contract.

## UI as Adapter, API as Contract Boundary

When a frontend page kicks off real business behavior, the lightest useful pattern is:

- **UI/hook layer as Adapter** - convert clicks, form input, and page events into API calls
- **API/service layer as Facade or contract boundary** - own validation, state transitions, and persistence

Choose this shape when:
- the behavior should be unit-tested without a browser
- more than one client could reuse the rule
- the page is becoming hard to test because business logic is mixed into rendering

**Contract shape:**
- **Require:** page sends a well-formed request and handles declared result states
- **Guarantee:** API owns the business rule, response schema, and error semantics
- **Maintain:** one source of truth for domain behavior
- **Assert:** contract tests at the API boundary; interaction tests at the page boundary

This is usually a better fit than embedding branching logic directly in components.
Use `react-fastapi-sqlite` for the concrete stack pattern, `tdd-agent` for the
Red→Green→Refactor sequence, and `validation` for the proof matrix.
