---
name: mcp-tool-registry
description: >
  Pattern for registering, discovering, and routing to MCP (Model Context Protocol)
  tools as the universal agent-tool interface. Use when building or consuming MCP
  servers, designing tool schemas for agent use, or implementing tool discovery and
  routing logic. Covers ACI design, schema quality, versioning, and the convergence
  of Anthropic, Microsoft A2A, and OpenAI on MCP as a standard.
status: active
last_validated: 2026-04-28
---

# MCP Tool Registry

## When to Use

Use this skill when:

- Building an MCP server that agents will call
- Consuming MCP tools from an agent's tool-use loop
- Designing tool schemas (name, description, input shape) for an agent
- Implementing tool discovery: how an agent finds available tools at runtime
- Routing agent requests to the right MCP server instance

---

## MCP Protocol Fundamentals

MCP (Anthropic, 2024) standardizes the **agent ↔ tool** boundary:

```
Agent (client)          MCP Server (host)
      │                       │
      │  tools/list  ──────►  │  returns tool manifest (name, description, inputSchema)
      │                       │
      │  tools/call  ──────►  │  executes tool, returns result
      │  {name, arguments}    │
      │          ◄────────    │  {content: [{type, text/data}]}
```

The key insight: **the tool description is code**. An agent's ability to use a tool
correctly depends almost entirely on the quality of the `description` and `inputSchema`.
This is the ACI (Agent-Computer Interface) design problem.

---

## Tool Schema Design (ACI)

A tool schema has three quality axes:

### 1. Name
- Verb-noun format: `search_files`, `create_branch`, `run_tests`
- Must distinguish from similar tools: `read_file` vs `read_file_range` vs `search_file_content`
- No abbreviations unless the domain is universal: `sql_query` not `sq`

### 2. Description
- **First sentence**: what the tool does. No preamble.
- **Second sentence** (if needed): when to use it vs a similar tool.
- **Do not** repeat the parameter names in the description.
- **Do** name the failure modes and when NOT to use it.

```json
{
  "name": "search_code",
  "description": "Search for a regex pattern across all files in the repository. Use for finding symbol definitions or usages. For simple substring search, use find_in_file instead (faster). Returns file paths and line numbers only, not content."
}
```

### 3. Input Schema (JSON Schema)
- Every parameter must have a `description`.
- Use `enum` for constrained values rather than free-form strings.
- Mark optional parameters as optional; do not include defaults in the schema name.
- Use `examples` in the description for parameters with non-obvious values.

```json
{
  "inputSchema": {
    "type": "object",
    "required": ["pattern"],
    "properties": {
      "pattern": {
        "type": "string",
        "description": "Regular expression to search for. Escaped for Python re module. Example: 'def\\s+\\w+\\(' to find all function definitions."
      },
      "file_glob": {
        "type": "string",
        "description": "Optional glob pattern to filter files. Example: '**/*.py'. Defaults to all files."
      },
      "case_sensitive": {
        "type": "boolean",
        "description": "Whether the search is case-sensitive. Default: true."
      }
    }
  }
}
```

---

## Registry Architecture

A tool registry is a queryable index of available tools across one or more MCP servers:

```python
class ToolRegistration(BaseModel):
    tool_id: str                        # ULID
    server_id: str                      # which MCP server hosts this tool
    server_url: str                     # http://localhost:PORT/mcp
    name: str
    description: str
    input_schema: dict                  # JSON Schema object
    version: str                        # semver
    tags: list[str]                     # e.g. ["file", "search", "code"]
    trust_tier: int                     # 0-4; matches agent-governance trust tiers
    registered_at: datetime
    last_healthy_at: datetime

class ToolRegistry:
    """
    Require: MCP servers are reachable at registration time.
    Guarantee: tools/list is called on each server to auto-populate the registry.
    Maintain: registry is refreshed on server reconnect; stale entries are marked inactive.
    """
    def register_server(self, server_url: str, trust_tier: int) -> list[ToolRegistration]: ...
    def find(self, query: str, tags: list[str] = None) -> list[ToolRegistration]: ...
    def route(self, tool_name: str) -> tuple[str, str]: ...  # (server_url, tool_name)
    def health_check(self) -> dict[str, bool]: ...           # server_id → is_healthy
```

---

## Tool Discovery

At agent startup, auto-discover tools:

```python
async def discover_tools(server_urls: list[str], registry: ToolRegistry) -> None:
    """
    Call tools/list on each server and register the results.
    Runs at startup and on reconnect.
    """
    for url in server_urls:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{url}/mcp", json={
                    "jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1
                })
                tools = response.json()["result"]["tools"]
                for tool in tools:
                    registry.register_server_tool(url, tool)
        except httpx.RequestError as e:
            log.warning(f"MCP server {url} unreachable during discovery: {e}")
            # Non-fatal: agent proceeds with tools from other servers
```

---

## Routing

When an agent emits a tool call, route it to the correct MCP server:

```python
def route_tool_call(tool_name: str, arguments: dict, registry: ToolRegistry,
                    guardian: ToolGuardian, agent_id: str) -> ToolResult:
    """
    Require: tool_name exists in registry; agent_id has a trust tier assigned.
    Guarantee: guardian intercepts before execution; result is structured.
    """
    server_url, canonical_name = registry.route(tool_name)
    if server_url is None:
        raise ToolNotFound(f"No registered tool named '{tool_name}'")

    guardian.intercept(agent_id, canonical_name, arguments)  # raises on DENY

    response = call_mcp_tool(server_url, canonical_name, arguments)
    return ToolResult(tool_name=canonical_name, content=response["content"])
```

---

## Versioning

Tools evolve. Pin tool versions in agent configuration:

```python
# agent config
TOOL_VERSION_PINS = {
    "search_code": ">=1.2.0,<2.0",   # allow patch updates, not breaking changes
    "run_tests": "==1.0.3",           # pin exactly for critical path tools
}
```

Breaking changes in a tool schema (renamed parameter, removed field) require a major
version bump. Additive changes (new optional parameter) are minor.

---

## Convergence: MCP as Universal Standard

As of 2025, MCP has emerged as the convergent standard:

| Platform | MCP Adoption |
|---|---|
| Anthropic Claude Code | Native MCP client + server |
| Microsoft (A2A protocol) | Builds on MCP tool invocation semantics |
| OpenAI | MCP-compatible tool interface in Responses API |
| LangChain / LangGraph | MCPToolkit adapter |
| GitHub Copilot | MCP server support via Extensions |

Design new tools to the MCP schema. Do not use bespoke tool formats that require
per-framework adapters.

---

## Failure Modes

| Symptom | Root cause | Fix |
|---|---|---|
| Agent uses wrong tool for task | Tool descriptions are too similar | Differentiate descriptions; add "use X not Y when…" guidance |
| Agent passes wrong argument type | `inputSchema` lacks type constraints | Add `type`, `enum`, or `pattern` to every parameter |
| Tool call rejected by guardian | Trust tier too low for intent | Check intent classification; raise trust tier or add ALLOW policy |
| Registry returns stale tools | Server restarted without re-registration | Add health-check loop; mark stale on connection failure |
| Tool result unparseable | Server returns unstructured text | Enforce structured `content` array in tool response; add response schema |

---

## Evidence

- MCP specification: Anthropic (2024), https://modelcontextprotocol.io
- ACI research: "ACI: The Interface Design Problem for Agents" — tool quality = model quality in practice
- Microsoft A2A protocol (2025): agent-to-agent routing built on MCP semantics
- awesome-copilot: MCP plugin ecosystem; 60+ MCP server implementations catalogued
<!-- consolidation:see-also:start -->
## See Also
[[feature-catalog]]  [[code]]  [[react-agent]]  [[agentic-harness]]  [[multi-agent-coordination]]
<!-- consolidation:see-also:end -->
