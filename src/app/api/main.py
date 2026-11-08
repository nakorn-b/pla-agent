import os
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from app.graph.agent import agent_chat, init_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.chat_graph = await init_graph()  # built once at startup
    yield


app = FastAPI(lifespan=lifespan)

# Let the PLA frontend call the API directly from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str = Field(default_factory=lambda: str(uuid4()))


class ChatResponse(BaseModel):
    message: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    graph = request.app.state.chat_graph
    return ChatResponse(message=await agent_chat(graph, req.message, req.thread_id))
