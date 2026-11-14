"""Request and response schemas for the match chat endpoint."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from sport_events.match_chat.agent import AnswerOutcome

MessageText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
]


class ChatMessageRequest(BaseModel):
    role: Literal["user", "assistant"]
    content: MessageText


class ChatRequest(BaseModel):
    messages: list[ChatMessageRequest] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def require_last_message_from_user(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return self


class ChatResponse(BaseModel):
    answer: str
    outcome: AnswerOutcome
