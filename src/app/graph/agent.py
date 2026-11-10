import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain.mcp import MCPAdapter
from langgraph.prebuilt import ToolNode, tools_condition

# The mcp client imports jsonschema lazily on the first tool call to validate
# results, and that import reads schema files from disk. Inside a run it blocks
# the event loop (langgraph dev raises BlockingError), so import it up front.
import jsonschema  # noqa: F401
import referencing.exceptions  # noqa: F401

load_dotenv()

# llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")
# Ollama qwen
llm = ChatOllama(
    model=os.getenv("MODEL_NAME", "qwen3.5:4b"),
    base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
)

JOBPULSE_MCP_URL = os.getenv("JOBPULSE_MCP_URL", "http://localhost:8001/sse")
AMP_MCP_URL = os.getenv("AMP_MCP_URL", "http://localhost:8002/sse")


class State(TypedDict):
    messages: Annotated[list, add_messages]


SYSTEM = {
    "role": "system",
    "content": "You are the PLA agent. Use find_relevant_jobs to find jobs. "
    "Use the AMP tool to classify peptide sequences. Otherwise reply normally.",
}


def build_graph(tools, checkpointer=None):

    agent_llm = llm.bind_tools(tools)

    async def agent(state: State):
        return {"messages": await agent_llm.ainvoke([SYSTEM] + state["messages"])}

    async def respond(state: State):
        return {
            "messages": [await llm.ainvoke([SYSTEM] + state["messages"])]
        }  # no tools bound

    graph_builder = StateGraph(State)
    # Node
    graph_builder.add_node("agent", agent)
    graph_builder.add_node("tools", ToolNode(tools))
    graph_builder.add_node("respond", respond)
    # Edge
    graph_builder.add_edge(START, "agent")
    graph_builder.add_conditional_edges(
        "agent", tools_condition, {"tools": "tools", END: END}
    )
    graph_builder.add_edge("tools", "respond")
    graph_builder.add_edge("respond", END)

    return graph_builder.compile(checkpointer=checkpointer)


async def load_tools():
    # JobPulse MCP tool
    jobpulse_tool = await MCPAdapter(JOBPULSE_MCP_URL).list_tools()
    # DistilESM-2-AMP MCP tool
    amp_tool = await MCPAdapter(AMP_MCP_URL).list_tools()

    return jobpulse_tool + amp_tool


async def init_graph():
    """Graph for the FastAPI app, with its own in-memory conversation memory."""
    return build_graph(await load_tools(), checkpointer=InMemorySaver())


@asynccontextmanager
async def make_graph():
    """Graph factory for `langgraph dev` (referenced in langgraph.json).

    The LangGraph server calls this for every run. The MCP sessions stay open
    while the run executes, so tool calls reuse them, and close when it ends.
    No checkpointer: the server provides persistence and rejects custom ones.
    """
    async with MCPAdapter(JOBPULSE_MCP_URL) as jobpulse, MCPAdapter(AMP_MCP_URL) as amp:
        yield build_graph(await jobpulse.list_tools() + await amp.list_tools())


async def agent_chat(chat_graph, user_message: str, thread_id: str) -> str:
    response = await chat_graph.ainvoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return response["messages"][-1].text
