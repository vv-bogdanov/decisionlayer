# MCP Naming and Tool Definition Notes

Date: 2026-06-05

## Sources Checked

- MCP draft tool specification:
  <https://modelcontextprotocol.io/specification/draft/server/tools>
- MCP client best practices:
  <https://modelcontextprotocol.io/docs/develop/clients/client-best-practices>
- MCP tool annotations blog:
  <https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/>
- AWS Prescriptive Guidance for MCP tool definitions:
  <https://docs.aws.amazon.com/prescriptive-guidance/latest/mcp-strategies/mcp-tool-strategy-definitions.html>

## Findings

- Tool names are model-facing identifiers. The MCP spec requires uniqueness only
  within one server and warns that aggregated clients can still hit collisions.
  Generic names such as `list`, `add`, and `config` are therefore weak names.
- Tool names should be short, valid MCP identifiers and descriptive enough for
  keyword-based discovery. Lowercase snake_case `verb_object` names match the
  examples and are easy for generic agents to scan.
- Tool descriptions should read like compact prompts: what the tool does, when
  to use it, what the parameters mean, and important constraints.
- JSON schemas should include parameter descriptions, defaults for finite
  choices where useful, and tight `additionalProperties: false` contracts.
- Tool annotations are useful hints for approval UX, but not security controls.
  Read-only tools should advertise `readOnlyHint`; additive writes can mark
  `destructiveHint: false`; supersede is destructive because it mutates an
  accepted ADR's status.
- For small toolsets like this one, eager tool listing is acceptable. If this
  grows, progressive discovery becomes relevant.

## Applied Decision

- MCP server key and `serverInfo.name`: `repo-adr-decisions`.
- Listed tool names:
  - `adr_locate_directory`
  - `adr_list_decisions`
  - `adr_build_brief`
  - `adr_add_decision`
  - `adr_supersede_decision`
  - `adr_configure`
- Old short names remain hidden compatibility aliases in the MCP handler, but
  are no longer returned by `tools/list`.
