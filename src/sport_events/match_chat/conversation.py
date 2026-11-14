"""Provider-neutral conversation types shared by the agent, tools, and model adapters."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    content: str
    is_error: bool = False


class ModelStop(StrEnum):
    ANSWER = "answer"
    TOOL_CALLS = "tool_calls"
    REFUSED = "refused"
    TRUNCATED = "truncated"


@dataclass(frozen=True)
class ModelReply:
    stop: ModelStop
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    # Opaque provider payload that the adapter must send back unchanged in a tool round.
    provider_content: object | None = None


@dataclass(frozen=True)
class ToolRound:
    """One model reply that requested tools, with the results returned for it."""

    reply: ModelReply
    results: tuple[ToolResult, ...]


class LanguageModel(Protocol):
    async def reply(
        self,
        system: str,
        history: Sequence[ChatMessage],
        rounds: Sequence[ToolRound],
        tools: Sequence[ToolDefinition],
    ) -> ModelReply:
        """Return the next model reply for the history plus this turn's tool rounds."""
        ...


class ToolExecutor(Protocol):
    @property
    def definitions(self) -> Sequence[ToolDefinition]: ...

    async def execute(self, call: ToolCall) -> ToolResult: ...
