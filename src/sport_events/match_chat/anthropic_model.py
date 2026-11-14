"""Claude adapter for the match chat agent; the only module that imports the Anthropic SDK."""

from collections.abc import Sequence
from typing import cast

from anthropic import AsyncAnthropic
from anthropic.types import ContentBlockParam, MessageParam, ToolParam

from sport_events.match_chat.conversation import (
    ChatMessage,
    ModelReply,
    ModelStop,
    ToolCall,
    ToolDefinition,
    ToolRound,
)

DEFAULT_MODEL = "claude-haiku-5-5"
_REQUEST_TIMEOUT_SECONDS = 30.0


def create_client(api_key: str) -> AsyncAnthropic:
    return AsyncAnthropic(api_key=api_key, timeout=_REQUEST_TIMEOUT_SECONDS, max_retries=2)


class AnthropicLanguageModel:
    def __init__(
        self, client: AsyncAnthropic, model: str = DEFAULT_MODEL, max_tokens: int = 2048
    ) -> None:
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def reply(
        self,
        system: str,
        history: Sequence[ChatMessage],
        rounds: Sequence[ToolRound],
        tools: Sequence[ToolDefinition],
    ) -> ModelReply:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            tools=[_tool_param(tool) for tool in tools],
            messages=_messages(history, rounds),
            output_config={"effort": "low"},
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        tool_calls = tuple(
            ToolCall(
                id=block.id,
                name=block.name,
                arguments=dict(block.input) if isinstance(block.input, dict) else {},
            )
            for block in response.content
            if block.type == "tool_use"
        )
        return ModelReply(
            stop=_stop(response.stop_reason),
            text=text,
            tool_calls=tool_calls,
            provider_content=response.content,
        )


def _tool_param(tool: ToolDefinition) -> ToolParam:
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


def _messages(history: Sequence[ChatMessage], rounds: Sequence[ToolRound]) -> list[MessageParam]:
    messages: list[MessageParam] = []
    for message in history:
        if message.role == "user":
            messages.append({"role": "user", "content": message.content})
        else:
            messages.append({"role": "assistant", "content": message.content})
    for tool_round in rounds:
        # Content blocks (including thinking) go back exactly as the API returned them.
        messages.append(
            {
                "role": "assistant",
                "content": cast("list[ContentBlockParam]", tool_round.reply.provider_content),
            }
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": result.call_id,
                        "content": result.content,
                        "is_error": result.is_error,
                    }
                    for result in tool_round.results
                ],
            }
        )
    return messages


def _stop(stop_reason: str | None) -> ModelStop:
    match stop_reason:
        case "end_turn":
            return ModelStop.ANSWER
        case "tool_use":
            return ModelStop.TOOL_CALLS
        case "refusal":
            return ModelStop.REFUSED
        case _:
            # max_tokens and any stop reason this application does not use.
            return ModelStop.TRUNCATED
