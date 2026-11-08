import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain.mcp import MCPAdapter
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash")

JOBPULSE_MCP_URL = os.getenv("JOBPULSE_MCP_URL", "http://localhost:8001/sse")
AMP_MCP_URL = os.getenv("AMP_MCP_URL", "http://localhost:8002/sse")



class State(TypedDict):
    messages: Annotated[list, add_messages]

SYSTEM = {
    "role": "system",
    "content": "You are the PLA agent. Use search_jobs to find jobs. "
    "Use the AMP tool to classify peptide sequences. Otherwise reply normally.",
}


def build_graph(tools):

    agent_llm = llm.bind_tools(tools)

    async def agent(state: State):
        return {"messages": await agent_llm.ainvoke([SYSTEM] + state["messages"])}

    async def respond(state: State):
        return {
            "messages": [await llm.ainvoke([SYSTEM] + state["messages"])] }  # no tools bound

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

    checkpointer = InMemorySaver()

    return graph_builder.compile(checkpointer=checkpointer)


async def init_graph():
    # JobPulse MCP tool
    jobpulse_tool = await MCPAdapter(JOBPULSE_MCP_URL).list_tools()
    # DistilESM-2-AMP MCP tool
    amp_tool = await MCPAdapter(AMP_MCP_URL).list_tools()

    tools = jobpulse_tool + amp_tool
    return build_graph(tools)

async def agent_chat(chat_graph, user_message: str, thread_id: str) -> str:
    response = await chat_graph.ainvoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": thread_id}},
    )
    return response["messages"][-1].text


# graph_builder.add_node("job", job_agent)
# graph_builder.add_node("job_tools", ToolNode(job_tools))
# graph_builder.add_conditional_edges("job", tools_condition, {"tools": "job_tools", END: END})
# graph_builder.add_edge("job_tools", "job")   # loop back so the LLM sees results
# # remove: graph_builder.add_edge('job', END)
