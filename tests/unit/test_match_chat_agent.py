from collections.abc import Sequence
from datetime import date

import pytest

from sport_events.match_chat.agent import AnswerOutcome, MatchChatAgent
from sport_events.match_chat.conversation import (
    ChatMessage,
    ModelReply,
    ModelStop,
    ToolCall,
    ToolDefinition,
    ToolResult,
    ToolRound,
)


class ScriptedModel:
    def __init__(self, replies: list[ModelReply]) -> None:
        self._replies = replies
        self.systems: list[str] = []
        self.round_counts: list[int] = []

    async def reply(
        self,
        system: str,
        history: Sequence[ChatMessage],
        rounds: Sequence[ToolRound],
        tools: Sequence[ToolDefinition],
    ) -> ModelReply:
        self.systems.append(system)
        self.round_counts.append(len(rounds))
        return self._replies.pop(0)


class RecordingTools:
    definitions: Sequence[ToolDefinition] = ()

    def __init__(self) -> None:
        self.calls: list[ToolCall] = []

    async def execute(self, call: ToolCall) -> ToolResult:
        self.calls.append(call)
        return ToolResult(call_id=call.id, content=f"result of {call.name}")


def _agent(model: ScriptedModel, tools: RecordingTools, max_model_calls: int = 5) -> MatchChatAgent:
    return MatchChatAgent(model, tools, lambda: date(2026, 11, 14), max_model_calls)


def _tool_reply(*names: str) -> ModelReply:
    return ModelReply(
        ModelStop.TOOL_CALLS,
        "",
        tuple(ToolCall(id=f"call-{i}", name=name, arguments={}) for i, name in enumerate(names)),
    )


QUESTION = [ChatMessage("user", "Who won?")]


async def test_returns_a_direct_answer_without_tools() -> None:
    model = ScriptedModel([ModelReply(ModelStop.ANSWER, "Nobody yet.")])
    tools = RecordingTools()

    answer = await _agent(model, tools).answer(QUESTION)

    assert (answer.outcome, answer.text) == (AnswerOutcome.ANSWERED, "Nobody yet.")
    assert tools.calls == []
    assert "Today's date (UTC): 2026-11-14." in model.systems[0]


async def test_runs_tools_in_order_and_feeds_results_back() -> None:
    model = ScriptedModel(
        [_tool_reply("find_teams", "list_matches"), ModelReply(ModelStop.ANSWER, "Done.")]
    )
    tools = RecordingTools()

    answer = await _agent(model, tools).answer(QUESTION)

    assert answer.outcome is AnswerOutcome.ANSWERED
    assert [call.name for call in tools.calls] == ["find_teams", "list_matches"]
    assert model.round_counts == [0, 1]


async def test_stops_at_the_model_call_limit() -> None:
    model = ScriptedModel([_tool_reply("list_matches") for _ in range(3)])
    tools = RecordingTools()

    answer = await _agent(model, tools, max_model_calls=3).answer(QUESTION)

    assert answer.outcome is AnswerOutcome.STEP_LIMIT
    assert len(tools.calls) == 3


@pytest.mark.parametrize(
    ("reply", "outcome"),
    [
        (ModelReply(ModelStop.REFUSED, ""), AnswerOutcome.REFUSED),
        (ModelReply(ModelStop.TRUNCATED, "partial"), AnswerOutcome.TRUNCATED),
        (ModelReply(ModelStop.ANSWER, ""), AnswerOutcome.TRUNCATED),
        (ModelReply(ModelStop.TOOL_CALLS, ""), AnswerOutcome.TRUNCATED),
    ],
)
async def test_maps_unusable_replies_to_a_fixed_message(
    reply: ModelReply, outcome: AnswerOutcome
) -> None:
    answer = await _agent(ScriptedModel([reply]), RecordingTools()).answer(QUESTION)

    assert answer.outcome is outcome
    assert answer.text
    assert "partial" not in answer.text


@pytest.mark.parametrize(
    "history", [[], [ChatMessage("user", "Hi"), ChatMessage("assistant", "Hello")]]
)
async def test_requires_a_conversation_that_ends_with_a_user_message(
    history: list[ChatMessage],
) -> None:
    with pytest.raises(ValueError, match="user message"):
        await _agent(ScriptedModel([]), RecordingTools()).answer(history)


def test_requires_at_least_one_model_call() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        _agent(ScriptedModel([]), RecordingTools(), max_model_calls=0)
