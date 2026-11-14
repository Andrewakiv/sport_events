from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from sport_events.api.dependencies import get_language_model, get_match_queries
from sport_events.football_models import Match, MatchFilters, MatchPage, Team
from sport_events.main import create_app
from sport_events.match_chat.anthropic_model import AnthropicLanguageModel
from sport_events.match_chat.conversation import (
    ChatMessage,
    LanguageModelUnavailableError,
    ModelReply,
    ModelStop,
    ToolCall,
    ToolDefinition,
    ToolRound,
)
from sport_events.settings import Settings


class StubDatabase:
    async def close(self) -> None:
        pass


class ScriptedModel:
    def __init__(self, replies: list[ModelReply | Exception]) -> None:
        self.replies = replies
        self.histories: list[list[ChatMessage]] = []

    async def reply(
        self,
        system: str,
        history: Sequence[ChatMessage],
        rounds: Sequence[ToolRound],
        tools: Sequence[ToolDefinition],
    ) -> ModelReply:
        self.histories.append(list(history))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class StubQueries:
    def __init__(self) -> None:
        self.team_names: list[str] = []

    async def list_matches(self, query: MatchFilters) -> MatchPage:
        return MatchPage(items=[], total=0, limit=query.limit, offset=query.offset)

    async def get_match(self, provider_id: int) -> Match | None:
        return None

    async def find_teams(self, name: str, limit: int) -> list[Team]:
        self.team_names.append(name)
        return [Team(id=81, name="FC Barcelona")]


async def chat_client(
    model: ScriptedModel | None,
    queries: StubQueries | None = None,
    settings: Settings | None = None,
) -> AsyncIterator[AsyncClient]:
    app = create_app(settings=settings or Settings(_env_file=None), database=StubDatabase())  # type: ignore[arg-type]
    if model is None:
        app.state.language_model = None
    else:
        app.dependency_overrides[get_language_model] = lambda: model
    app.dependency_overrides[get_match_queries] = lambda: queries or StubQueries()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def question(text: str = "Who plays next?") -> dict[str, Any]:
    return {"messages": [{"role": "user", "content": text}]}


async def test_answers_a_question_and_passes_the_page_history_to_the_model() -> None:
    model = ScriptedModel([ModelReply(ModelStop.ANSWER, "Barcelona plays on Tuesday.")])
    body = {
        "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "  Who plays next?  "},
        ]
    }

    async for client in chat_client(model):
        response = await client.post("/api/v1/chat", json=body)

    assert response.status_code == 200
    assert response.json() == {"answer": "Barcelona plays on Tuesday.", "outcome": "answered"}
    assert model.histories[0] == [
        ChatMessage("user", "Hi"),
        ChatMessage("assistant", "Hello!"),
        ChatMessage("user", "Who plays next?"),
    ]


async def test_runs_tools_against_the_request_scoped_queries() -> None:
    model = ScriptedModel(
        [
            ModelReply(
                ModelStop.TOOL_CALLS, "", (ToolCall("c1", "find_teams", {"name": "Barca"}),)
            ),
            ModelReply(ModelStop.ANSWER, "Found it."),
        ]
    )
    queries = StubQueries()

    async for client in chat_client(model, queries):
        response = await client.post("/api/v1/chat", json=question())

    assert response.json()["answer"] == "Found it."
    assert queries.team_names == ["Barca"]


async def test_refusal_is_a_successful_response_with_a_fixed_message() -> None:
    model = ScriptedModel([ModelReply(ModelStop.REFUSED, "")])

    async for client in chat_client(model):
        response = await client.post("/api/v1/chat", json=question())

    assert response.status_code == 200
    assert response.json()["outcome"] == "refused"
    assert response.json()["answer"]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"messages": []},
        {"messages": [{"role": "user", "content": "q"}] * 21},
        {"messages": [{"role": "user", "content": "x" * 1001}]},
        {"messages": [{"role": "user", "content": "   "}]},
        {"messages": [{"role": "system", "content": "q"}]},
        {"messages": [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]},
    ],
)
async def test_rejects_invalid_conversations(body: dict[str, Any]) -> None:
    model = ScriptedModel([])

    async for client in chat_client(model):
        response = await client.post("/api/v1/chat", json=body)

    assert response.status_code == 422
    assert model.histories == []


async def test_returns_503_when_no_api_key_is_configured() -> None:
    async for client in chat_client(None):
        response = await client.post("/api/v1/chat", json=question())

    assert response.status_code == 503
    assert response.json() == {"detail": "chat_unavailable"}


async def test_maps_provider_failures_to_a_safe_502() -> None:
    model = ScriptedModel([LanguageModelUnavailableError()])

    async for client in chat_client(model):
        response = await client.post("/api/v1/chat", json=question())

    assert response.status_code == 502
    assert response.json() == {"detail": "The language model is temporarily unavailable."}


async def test_rate_limits_each_client_with_retry_after() -> None:
    model = ScriptedModel([ModelReply(ModelStop.ANSWER, "ok"), ModelReply(ModelStop.ANSWER, "ok")])
    settings = Settings(
        _env_file=None, chat_rate_limit_requests=2, chat_rate_limit_window_seconds=60
    )

    async for client in chat_client(model, settings=settings):
        statuses = [
            (await client.post("/api/v1/chat", json=question())).status_code for _ in range(2)
        ]
        limited = await client.post("/api/v1/chat", json=question())

    assert statuses == [200, 200]
    assert limited.status_code == 429
    assert 1 <= int(limited.headers["retry-after"]) <= 60
    assert len(model.histories) == 2


def test_creates_a_model_only_when_an_api_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    without_key = create_app(settings=Settings(_env_file=None), database=StubDatabase())  # type: ignore[arg-type]
    with_key = create_app(
        settings=Settings(_env_file=None, ANTHROPIC_API_KEY="test-key"),  # type: ignore[call-arg]
        database=StubDatabase(),  # type: ignore[arg-type]
    )

    assert without_key.state.language_model is None
    assert isinstance(with_key.state.language_model, AnthropicLanguageModel)
