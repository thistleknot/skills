# System Patterns

## Architecture
The skills library follows a modular architecture where each skill is a self-contained unit with:
- SKILL.md documentation file
- Optional implementation files (Python scripts, configuration, etc.)
- Consistent naming and structure conventions

## Key Technical Decisions
- Skills stored in ~/.copilot/skills/ directory
- Each skill has a SKILL.md file as the entry point
- Skills follow consistent documentation patterns
- Skills are discoverable by name

## Design Patterns in Use
- Modular skill design for reusability
- Consistent documentation structure
- Clear separation of concerns between skills
- Reusable patterns across different skill types

## Component Relationships
- Skills library serves as a central repository for reusable development patterns
- Individual skills can be invoked as needed for specific tasks
- Skills can reference each other for complex workflows
