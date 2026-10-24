from fastapi import FastAPI
from pydantic import BaseModel

from app.graph.agent import agent_chat

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return ChatResponse(message=agent_chat(req.message))
