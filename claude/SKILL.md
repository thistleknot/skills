---
name: claude
description: >
  Cheat sheet for Claude Code project structure and file organization — what
  belongs in CLAUDE.md (project memory), .claude/ subfolders, agents, commands,
  hooks, and settings, from core setup through advanced automation. Use when
  setting up a new Claude Code project, deciding where a config or instruction
  file should live, or auditing an existing .claude/ layout. Trigger on "where
  does CLAUDE.md go", "project structure for Claude Code", "what goes in
  .claude/", or organizing agents, commands, and hooks.
---

### Claude Code Project Structure Cheat Sheet

This cheat sheet outlines the optimal folder structure and file organization for Claude Code projects, ranging from core project memory to advanced automation.

---

#### 📂 **Root Directory Essentials**
The root of your project contains the primary identity and configuration files for Claude.

*   **`CLAUDE.md`**: The **"Project Memory."** Contains team instructions, tech stack overview, architecture, and coding conventions. **Always commit this file**.
*   **`CLAUDE.local.md`**: Personal project instructions or overrides. **Gitignored** to keep personal preferences out of the shared repo.
*   **`.mcp.json`**: Configuration for **Model Context Protocol** servers (e.g., GitHub, Postgres, Slack) to extend Claude's toolset.
*   **`README.md`**: Standard project documentation for humans.

---

#### 🛠️ **The `.claude/` Folder ("The Control Center")**
This hidden directory houses the specialized logic and permissions for Claude's behavior.

| Folder/File | Purpose | Usage Example |
| :--- | :--- | :--- |
| **`settings.json`** | Global permissions and configuration. | Allowed tools, token limits. |
| **`settings.local.json`** | Personal permission overrides. | **Gitignored**. |
| **`commands/`** | Custom **slash commands** defined in Markdown. | `review.md` becomes `/project:review`. |
| **`rules/`** | Modular instruction files for standards. | `code-style.md`, `testing.md`. |
| **`skills/`** | **Auto-invoked workflows** for specific tasks. | Must contain a `SKILL.md` file. |
| **`agents/`** | **Subagent personas** for isolated tasks. | `code-reviewer.md`, `security-auditor.md`. |
| **`hooks/`** | Lifecycle event scripts (e.g., PreToolUse). | Automate checks before/after Claude acts. |

---

#### 🏗️ **Standard Application Layout**
A clean repository structure helps Claude navigate and understand your codebase more efficiently.

*   **`src/`**: Core application logic. For large projects, you can place nested `CLAUDE.md` files in subdirectories (e.g., `src/api/CLAUDE.md`) for localized context.
*   **`docs/`**: Detailed documentation including `architecture.md`, `decisions/`, and `runbooks/`.
*   **`tests/`**: Organized by type: `unit/`, `integration/`, and `e2e/`.
*   **`tools/` or `scripts/`**: Executable automation for setup, deployment, or seeding databases.
*   **`plugins/`**: Bundled distributable setups for extending Claude's functionality.

---

#### 💡 **Best Practices for Structure**
*   **Keep it Modular**: Break down complex instructions into modular files within `.claude/rules/` or `.claude/skills/` rather than one giant `CLAUDE.md`.
*   **Hierarchical Context**: Use Level-based `CLAUDE.md` files (Root = Who you are, Project = What the project is, Subfolder = Area-specific rules).
*   **Context Management**: If Claude’s memory (context) exceeds 80%, use the `/clear` command. Use `/compact` between 70-90% to maintain focus.
*   **Security**: Never store secrets in `CLAUDE.md`. Use `.env` files and ensure `.local.json` files are gitignored.