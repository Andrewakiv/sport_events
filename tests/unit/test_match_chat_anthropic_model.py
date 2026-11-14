from typing import Any, cast

from anthropic import AsyncAnthropic
from anthropic.types import Message, TextBlock, ToolUseBlock

from sport_events.match_chat.anthropic_model import AnthropicLanguageModel
from sport_events.match_chat.conversation import (
    ChatMessage,
    ModelReply,
    ModelStop,
    ToolCall,
    ToolDefinition,
    ToolResult,
    ToolRound,
)


class _FakeMessages:
    def __init__(self, response: Message) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Message:
        self.requests.append(kwargs)
        return self.response


class _FakeClient:
    def __init__(self, response: Message) -> None:
        self.messages = _FakeMessages(response)


def _model(response: Message) -> tuple[AnthropicLanguageModel, _FakeMessages]:
    client = _FakeClient(response)
    return AnthropicLanguageModel(cast(AsyncAnthropic, client)), client.messages


def _message(stop_reason: str, *blocks: Any) -> Message:
    return Message.model_construct(role="assistant", content=list(blocks), stop_reason=stop_reason)


TOOL = ToolDefinition("find_teams", "Find teams.", {"type": "object", "properties": {}})


async def test_sends_haiku_request_with_low_effort_and_tools() -> None:
    model, messages = _model(
        _message("end_turn", TextBlock.model_construct(type="text", text="Hi"))
    )

    reply = await model.reply("system text", [ChatMessage("user", "Hello")], [], [TOOL])

    request = messages.requests[0]
    assert request["model"] == "claude-haiku-5-5"
    assert request["system"] == "system text"
    assert request["output_config"] == {"effort": "low"}
    assert request["messages"] == [{"role": "user", "content": "Hello"}]
    assert request["tools"] == [
        {"name": "find_teams", "description": "Find teams.", "input_schema": TOOL.input_schema}
    ]
    assert (reply.stop, reply.text) == (ModelStop.ANSWER, "Hi")


async def test_maps_tool_use_blocks_and_keeps_provider_content() -> None:
    block = ToolUseBlock.model_construct(
        type="tool_use", id="toolu_1", name="find_teams", input={"name": "Barca"}
    )
    model, _ = _model(_message("tool_use", block))

    reply = await model.reply("s", [ChatMessage("user", "q")], [], [TOOL])

    assert reply.stop is ModelStop.TOOL_CALLS
    assert reply.tool_calls == (ToolCall("toolu_1", "find_teams", {"name": "Barca"}),)
    assert reply.provider_content == [block]


async def test_tool_rounds_echo_provider_content_and_results() -> None:
    block = ToolUseBlock.model_construct(type="tool_use", id="toolu_1", name="t", input={})
    model, messages = _model(
        _message("end_turn", TextBlock.model_construct(type="text", text="ok"))
    )
    previous = ModelReply(
        ModelStop.TOOL_CALLS, "", (ToolCall("toolu_1", "t", {}),), provider_content=[block]
    )
    rounds = [ToolRound(previous, (ToolResult("toolu_1", "oops", is_error=True),))]

    await model.reply("s", [ChatMessage("user", "q")], rounds, [TOOL])

    assert messages.requests[0]["messages"][1:] == [
        {"role": "assistant", "content": [block]},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_1",
                    "content": "oops",
                    "is_error": True,
                }
            ],
        },
    ]


async def test_maps_refusal_and_other_stop_reasons() -> None:
    refused, _ = _model(_message("refusal"))
    truncated, _ = _model(_message("max_tokens"))
    history = [ChatMessage("user", "q")]

    assert (await refused.reply("s", history, [], [TOOL])).stop is ModelStop.REFUSED
    assert (await truncated.reply("s", history, [], [TOOL])).stop is ModelStop.TRUNCATED
