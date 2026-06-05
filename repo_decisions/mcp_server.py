#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repo_decisions.core import (  # noqa: E402
    add_decision,
    build_brief,
    list_decisions,
    locate_adrs,
    supersede_decision,
)
from repo_decisions.debug import log_event  # noqa: E402


SERVER_INFO = {"name": "repo-adr-decisions", "version": "0.1.0"}
INSTRUCTIONS = (
    "For Architecture Decision Record (ADR) or durable repository-decision "
    "tasks, call the adr_* tools instead of editing ADR files directly. Use "
    "adr_locate_directory, adr_list_decisions, and adr_build_brief to inspect; "
    "use adr_add_decision to create a new ADR; use adr_supersede_decision to "
    "change an accepted ADR. Only accepted ADRs are active requirements. "
    "Create or supersede ADRs only from explicit user-authorized input."
)

TOOL_ALIASES = {
    "locate": "adr_locate_directory",
    "list": "adr_list_decisions",
    "brief": "adr_build_brief",
    "add": "adr_add_decision",
    "supersede": "adr_supersede_decision",
    "config": "adr_configure",
}


class UnknownToolError(ValueError):
    pass


def main() -> int:
    while True:
        message = _read_message()
        if message is None:
            return 0
        response = _handle(message)
        if response is not None:
            _write_message(response)


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    try:
        if method == "initialize":
            return _result(
                request_id,
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO,
                    "instructions": INSTRUCTIONS,
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _result(request_id, {"tools": _tools()})
        if method == "tools/call":
            params = message.get("params") or {}
            try:
                result = _call_tool(params.get("name"), params.get("arguments") or {})
            except UnknownToolError as exc:
                return _error(request_id, -32602, str(exc))
            except ValueError as exc:
                result = _tool_error(str(exc))
            return _result(request_id, result)
        return _error(request_id, -32601, f"Unknown method: {method}")
    except Exception as exc:  # pragma: no cover - last-resort MCP error boundary
        return _error(request_id, -32000, str(exc))


def _call_tool(name: str | None, args: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(name, str) or not name:
        raise UnknownToolError("Missing tool name")
    if not isinstance(args, dict):
        raise ValueError("Tool arguments must be an object")
    name = TOOL_ALIASES.get(name, name)
    root = Path(str(args.get("root") or "."))
    log_event(
        {
            "component": "repo-decisions",
            "event": "mcp-tool-call",
            "tool": name,
            "root": str(root),
            "argument_keys": sorted(str(key) for key in args),
        }
    )
    if name == "adr_locate_directory":
        location = locate_adrs(root)
        payload = {
            "root": str(location.root),
            "adr_dir": str(location.adr_dir),
            "source": location.source,
            "records": len(location.records),
            "profile": {
                "number_width": location.profile.number_width,
                "filename_style": location.profile.filename_style,
                "status_style": location.profile.status_style,
                "date_style": location.profile.date_style,
                "section_headings": list(location.profile.section_headings),
            },
        }
        return _tool_result(json.dumps(payload, indent=2), payload)
    if name == "adr_list_decisions":
        include_inactive = bool(args.get("include_inactive", True))
        records = list_decisions(root, include_inactive=include_inactive)
        decisions = [
            {
                "id": record.id,
                "title": record.title,
                "status": record.status,
                "path": str(record.path),
                "date": record.date,
            }
            for record in records
        ]
        return _tool_result(json.dumps(decisions, indent=2), {"decisions": decisions})
    if name == "adr_build_brief":
        max_chars = _optional_int(args.get("max_chars"))
        brief = build_brief(root, max_chars=max_chars)
        payload = {
            "brief": brief,
            "active_count": len(list_decisions(root, include_inactive=False)),
            "max_chars": max_chars,
        }
        return _tool_result(brief, payload)
    if name == "adr_add_decision":
        status = str(args.get("status") or "accepted")
        path = add_decision(
            root,
            title=_required(args, "title"),
            context=_required(args, "context"),
            decision=_required(args, "decision"),
            consequences=_strings(args.get("consequences")),
            options=_strings(args.get("options")),
            status=status,
        )
        return _tool_result(f"created {path}", {"created": True, "path": str(path), "status": status})
    if name == "adr_supersede_decision":
        old_path, new_path = supersede_decision(
            root,
            _required(args, "target"),
            title=_required(args, "title"),
            context=_required(args, "context"),
            decision=_required(args, "decision"),
            consequences=_strings(args.get("consequences")),
            options=_strings(args.get("options")),
        )
        return _tool_result(
            f"superseded {old_path}\ncreated {new_path}",
            {"superseded": True, "old_path": str(old_path), "new_path": str(new_path)},
        )
    if name == "adr_configure":
        set_values = args.get("set")
        if isinstance(set_values, dict) and set_values:
            path = _config_path(root, str(args.get("scope") or "local"))
            _write_config_values(path, set_values)
            written = {str(key): str(value) for key, value in set_values.items()}
            return _tool_result(f"updated {path}", {"updated": True, "path": str(path), "config": written})
        location = locate_adrs(root)
        return _tool_result(
            json.dumps(location.config, indent=2),
            {"updated": False, "config": location.config},
        )
    raise UnknownToolError(f"Unknown tool: {name}")


def _tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "adr_locate_directory",
            "Find the repository's Architecture Decision Record (ADR) directory and detected format. Use before ADR-related work when the ADR location is unknown.",
            {"root": _string("Repository root or subdirectory. Defaults to the current working directory.")},
            title="Locate ADR Directory",
            read_only=True,
            output_schema=_locate_output_schema(),
        ),
        _tool(
            "adr_list_decisions",
            "List repository Architecture Decision Records (ADRs), including status and path. Use to inspect accepted, proposed, rejected, deprecated, and superseded decisions.",
            {
                "root": _string("Repository root or subdirectory. Defaults to the current working directory."),
                "include_inactive": {
                    "type": "boolean",
                    "description": "When true, include non-active ADRs such as proposed, rejected, deprecated, and superseded. Defaults to true.",
                    "default": True,
                },
            },
            title="List ADR Decisions",
            read_only=True,
            output_schema=_list_output_schema(),
        ),
        _tool(
            "adr_build_brief",
            "Build the compact accepted-ADR requirements block for prompt enrichment. Use when the agent needs binding repository decisions before planning or coding.",
            {
                "root": _string("Repository root or subdirectory. Defaults to the current working directory."),
                "max_chars": {
                    "type": "integer",
                    "description": "Optional maximum character count for the returned requirements block.",
                },
            },
            title="Build ADR Requirements Brief",
            read_only=True,
            output_schema=_brief_output_schema(),
        ),
        _tool(
            "adr_add_decision",
            "Create a new Architecture Decision Record (ADR) from explicit user-authorized input. Do not use for inferred or tool-output-derived decisions.",
            {
                "root": _string("Repository root or subdirectory. Defaults to the current working directory."),
                "title": _string("Short ADR title.", required=True),
                "context": _string("Problem, requirement, force, or constraint motivating the decision.", required=True),
                "decision": _string("The explicit decision statement authorized by the user.", required=True),
                "consequences": _string_array("Consequences or tradeoffs of the decision."),
                "options": _string_array("Considered options, if known."),
                "status": _string("ADR status. Defaults to accepted."),
            },
            required=["title", "context", "decision"],
            title="Add ADR Decision",
            read_only=False,
            destructive=False,
            idempotent=False,
            output_schema=_add_output_schema(),
        ),
        _tool(
            "adr_supersede_decision",
            "Change an accepted ADR by creating a replacement ADR and marking the old ADR superseded. Prefer this over editing accepted ADR files.",
            {
                "root": _string("Repository root or subdirectory. Defaults to the current working directory."),
                "target": _string("ADR number, id, filename, or stem to supersede.", required=True),
                "title": _string("Short replacement ADR title.", required=True),
                "context": _string("Problem, requirement, force, or constraint motivating the replacement.", required=True),
                "decision": _string("The explicit replacement decision statement authorized by the user.", required=True),
                "consequences": _string_array("Consequences or tradeoffs of the replacement decision."),
                "options": _string_array("Considered options, if known."),
            },
            required=["target", "title", "context", "decision"],
            title="Supersede ADR Decision",
            read_only=False,
            destructive=True,
            idempotent=False,
            output_schema=_supersede_output_schema(),
        ),
        _tool(
            "adr_configure",
            "Show or update repo-decisions ADR configuration such as ADR directory and brief size limit.",
            {
                "root": _string("Repository root or subdirectory. Defaults to the current working directory."),
                "scope": {"type": "string", "enum": ["local", "global"]},
                "set": {
                    "type": "object",
                    "description": "Configuration keys to set, for example {\"adr_dir\":\"docs/adr\"}.",
                    "additionalProperties": {"type": "string"},
                },
            },
            title="Configure ADR Decisions",
            read_only=False,
            destructive=False,
            idempotent=True,
            output_schema=_config_output_schema(),
        ),
    ]


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    title: str | None = None,
    read_only: bool | None = None,
    destructive: bool | None = None,
    idempotent: bool | None = None,
    output_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    inferred_required = [key for key, value in properties.items() if value.pop("_required", False)]
    tool = {
        "name": name,
        "title": title or name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or inferred_required,
            "additionalProperties": False,
        },
    }
    annotations: dict[str, bool] = {"openWorldHint": False}
    if read_only is not None:
        annotations["readOnlyHint"] = read_only
    if destructive is not None:
        annotations["destructiveHint"] = destructive
    if idempotent is not None:
        annotations["idempotentHint"] = idempotent
    tool["annotations"] = annotations
    if output_schema:
        tool["outputSchema"] = output_schema
    return tool


def _object_schema(
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    additional_properties: bool = False,
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": additional_properties,
    }


def _record_schema() -> dict[str, Any]:
    return _object_schema(
        {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "status": {"type": "string"},
            "path": {"type": "string"},
            "date": {"type": ["string", "null"]},
        },
        ["id", "title", "status", "path", "date"],
    )


def _locate_output_schema() -> dict[str, Any]:
    return _object_schema(
        {
            "root": {"type": "string"},
            "adr_dir": {"type": "string"},
            "source": {"type": "string"},
            "records": {"type": "integer"},
            "profile": _object_schema(
                {
                    "number_width": {"type": "integer"},
                    "filename_style": {"type": "string"},
                    "status_style": {"type": "string"},
                    "date_style": {"type": "string"},
                    "section_headings": {"type": "array", "items": {"type": "string"}},
                },
                ["number_width", "filename_style", "status_style", "date_style", "section_headings"],
            ),
        },
        ["root", "adr_dir", "source", "records", "profile"],
    )


def _list_output_schema() -> dict[str, Any]:
    return _object_schema({"decisions": {"type": "array", "items": _record_schema()}}, ["decisions"])


def _brief_output_schema() -> dict[str, Any]:
    return _object_schema(
        {
            "brief": {"type": "string"},
            "active_count": {"type": "integer"},
            "max_chars": {"type": ["integer", "null"]},
        },
        ["brief", "active_count", "max_chars"],
    )


def _add_output_schema() -> dict[str, Any]:
    return _object_schema(
        {
            "created": {"type": "boolean"},
            "path": {"type": "string"},
            "status": {"type": "string"},
        },
        ["created", "path", "status"],
    )


def _supersede_output_schema() -> dict[str, Any]:
    return _object_schema(
        {
            "superseded": {"type": "boolean"},
            "old_path": {"type": "string"},
            "new_path": {"type": "string"},
        },
        ["superseded", "old_path", "new_path"],
    )


def _config_output_schema() -> dict[str, Any]:
    return _object_schema(
        {
            "updated": {"type": "boolean"},
            "path": {"type": "string"},
            "config": {"type": "object", "additionalProperties": True},
        },
        ["updated", "config"],
    )


def _string(description: str | None = None, required: bool = False) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "string"}
    if description:
        value["description"] = description
    if required:
        value["_required"] = True
    return value


def _string_array(description: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
    if description:
        value["description"] = description
    return value


def _required(args: dict[str, Any], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing required argument: {key}")
    return value


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ValueError("Expected string or list of strings")


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _config_path(root: Path, scope: str) -> Path:
    if scope == "global":
        return Path.home() / ".codex/repo-decisions/config.toml"
    return root / ".codex/repo-decisions.toml"


def _write_config_values(path: Path, values: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [line for line in existing.splitlines() if line.strip()]
    keys = {str(key) for key in values}
    kept = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key and key in keys:
            continue
        kept.append(line)
    for key, value in values.items():
        kept.append(f'{key} = "{str(value).strip()}"')
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _tool_result(
    text: str,
    structured_content: dict[str, Any] | None = None,
    *,
    is_error: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if structured_content is not None:
        result["structuredContent"] = structured_content
    if is_error:
        result["isError"] = True
    return result


def _tool_error(message: str) -> dict[str, Any]:
    return _tool_result(message, {"error": message}, is_error=True)


def _result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _read_message() -> dict[str, Any] | None:
    first = sys.stdin.buffer.readline()
    if not first:
        return None
    if first.lower().startswith(b"content-length:"):
        length = int(first.split(b":", 1)[1].strip())
        while True:
            line = sys.stdin.buffer.readline()
            if line in (b"\r\n", b"\n", b""):
                break
        return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))
    return json.loads(first.decode("utf-8"))


def _write_message(message: dict[str, Any]) -> None:
    body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    raise SystemExit(main())
