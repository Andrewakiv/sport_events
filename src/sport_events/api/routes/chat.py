"""Champions League chat endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from sport_events.api.dependencies import enforce_chat_rate_limit, get_match_chat_agent
from sport_events.api.schemas.chat import ChatRequest, ChatResponse
from sport_events.match_chat.agent import MatchChatAgent
from sport_events.match_chat.conversation import ChatMessage, LanguageModelUnavailableError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    dependencies=[Depends(enforce_chat_rate_limit)],
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Rate limit exceeded; see Retry-After."},
        status.HTTP_502_BAD_GATEWAY: {"description": "The language model request failed."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Chat is not configured."},
    },
)
async def chat(
    body: ChatRequest,
    agent: Annotated[MatchChatAgent, Depends(get_match_chat_agent)],
) -> ChatResponse:
    history = [ChatMessage(message.role, message.content) for message in body.messages]
    try:
        answer = await agent.answer(history)
    except LanguageModelUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The language model is temporarily unavailable.",
        ) from error
    return ChatResponse(answer=answer.text, outcome=answer.outcome)
