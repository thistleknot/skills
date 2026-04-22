# Architecture

## FOL as Universal Reasoning Unit
Every thought, relationship, and code structure is expressible as `P(Subject, [Object])`.

- **Predicates > Subject/Object** — no effect without an actor; predicates are load-bearing
- Predicates exist as utility functions; entities have accessor member functions to call them
- This separates *what acts* from *how it acts* while preserving member functions (API analogy)

Activate latent knowledge before formalizing:
- What do I know about this domain not explicitly stated?
- What adjacent domains are relevant?
- What parties interact, and through which predicates?
- What were the relevant conditions prior to this point?

## Abstract Class Bridge

| FOL Concept | Code Concept |
|---|---|
| Subject / Object | Abstract base class / concrete class |
| Predicate | Abstract method / utility function |
| P(S,[O]) | Member function call |
| Constraint(x, condition) | Precondition / contract |

- Abstract classes represent conceptual entities from the problem domain
- Concrete classes implement specific instances
- Entities only depend on predicates they use (interface segregation)
- Concrete implementations depend on abstractions (dependency inversion)

## Dev Perspectives (Structural)
- **Inputs (~Subject):** parms, configs, constants, hyperparams — single source of truth
- **Processes (~Predicate):** utility functions, transformations — two entities don't interact without a mediating predicate
- **Classes (~Entities):** member functions = accessor API to predicates
- **Outputs (~Object/goal):** target state

Hyperparams ≠ infrastructure vars — batch size is a system variable, not a model hyperparameter.

## Gang of Four (Selection Guide)
- **Creational** (Factory, Builder, Singleton): object creation is complex or needs flexibility
- **Structural** (Adapter, Decorator, Facade): legacy code or interface mismatches
- **Behavioral** (Observer, Strategy, Command, Template Method, State): algorithms or interactions are complex

## Pragmatic Principles
- DRY / Orthogonality — eliminate duplication; design independent components
- Tracer bullets — implement end-to-end skeleton first, then flesh out
- Prefer plain text / human-readable formats
- Debug systematically, not by coincidence
- Gather real requirements, not assumptions
