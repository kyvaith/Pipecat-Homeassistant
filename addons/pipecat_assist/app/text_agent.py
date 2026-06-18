"""Text bridge used by the Home Assistant Conversation integration."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from app.config import RuntimeConfig
from app.mcp_bridge import HomeAssistantMCPBridge


def _format_openai_tools(tools_schema) -> list[dict[str, Any]]:
    """Convert Pipecat FunctionSchema objects to OpenAI Chat tools."""

    formatted: list[dict[str, Any]] = []
    for tool in tools_schema.standard_tools:
        formatted.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.properties,
                        "required": tool.required,
                    },
                },
            }
        )
    return formatted


def _tool_args(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def run_text_conversation(
    config: RuntimeConfig,
    *,
    text: str,
    language: str | None,
    conversation_id: str | None,
    flow_id: str | None = None,
) -> dict[str, Any]:
    """Run a text request through OpenAI with HA MCP tools."""

    flow = config.selected_flow(flow_id)
    integration = config.model_integration(flow)
    provider_kind = integration.kind if integration else "openai"
    if provider_kind not in {"openai", "openai_compatible", "ollama"}:
        return {
            "speech": "This Pipecat Assist text bridge does not support the selected model provider yet.",
            "conversation_id": conversation_id,
            "continue_conversation": False,
            "error": "unsupported_text_provider",
        }

    api_key = (integration.api_key if integration else "") or config.openai_api_key
    if provider_kind == "ollama" and not api_key:
        api_key = "ollama"
    if not api_key:
        return {
            "speech": "Pipecat Assist is missing an API key for the selected model provider.",
            "conversation_id": conversation_id,
            "continue_conversation": False,
            "error": "missing_provider_api_key",
        }

    system = (
        f"{flow.instructions}\n\n"
        "You are answering through Home Assistant Conversation text mode. "
        "Use MCP tools silently for explicit smart-home requests. "
        "Keep the final answer short and natural."
    )
    if language:
        system += f"\nThe user's language is {language}."

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if integration and integration.base_url and provider_kind in {"openai_compatible", "ollama"}:
        client_kwargs["base_url"] = integration.base_url
    client = AsyncOpenAI(**client_kwargs)
    tools: list[dict[str, Any]] = []

    bridge: HomeAssistantMCPBridge | None = None
    if flow.mcp_enabled and config.effective_mcp_token:
        bridge = HomeAssistantMCPBridge(
            config.effective_mcp_url,
            config.effective_mcp_token,
            flow.mcp_tool_allowlist,
        )
        try:
            await bridge.start()
            tools_schema = await bridge.tools_schema()
            tools = _format_openai_tools(tools_schema)
        except Exception as err:
            await bridge.close()
            bridge = None
            return {
                "speech": f"Home Assistant MCP is not available: {err}",
                "conversation_id": conversation_id,
                "continue_conversation": False,
                "error": "mcp_unavailable",
            }

    try:
        for _ in range(6):
            kwargs: dict[str, Any] = {
                "model": flow.text_model
                or (integration.default_model if integration else "")
                or config.text_model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            response = await client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))

            tool_calls = message.tool_calls or []
            if not tool_calls:
                speech = message.content or ""
                return {
                    "speech": speech.strip() or "Done.",
                    "conversation_id": conversation_id,
                    "continue_conversation": False,
                }

            if bridge is None:
                return {
                    "speech": "I need Home Assistant MCP tools for that, but MCP is not connected.",
                    "conversation_id": conversation_id,
                    "continue_conversation": False,
                    "error": "mcp_not_connected",
                }

            for tool_call in tool_calls:
                result = await bridge.call_tool(
                    tool_call.function.name,
                    _tool_args(tool_call.function.arguments),
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return {
            "speech": "The request needed too many tool calls and was stopped.",
            "conversation_id": conversation_id,
            "continue_conversation": False,
            "error": "tool_loop_limit",
        }
    finally:
        if bridge:
            await bridge.close()
