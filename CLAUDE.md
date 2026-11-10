# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

PLA Agent: a LangGraph agent served over FastAPI that routes a user's chat message to one of two external capabilities: **job search** (the JobPulse service) or **antimicrobial peptide (AMP) classification** (the DistilESM-2-AMP service). Both are separate repos and run as separate processes; this repo only orchestrates them.

## Commands

Dependencies are managed with `uv` (Python 3.13, see `.python-version`).

```bash
uv sync                                              # install deps, including the dev group (langgraph-cli)
uv run fastapi dev src/app/api/main.py               # run the API with reload; serves POST /chat
uv run langgraph dev                                 # LangGraph Studio / in-memory server, using langgraph.json
uv run ruff check . && uv run ruff format .          # lint/format (ruff is used, but there is no ruff config and it is not a declared dependency)
```

There is no test suite yet. `Dockerfile` is empty and the root `main.py` is an unused `uv init` stub.

Try the API:

```bash
curl -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"message": "find senior SRE jobs", "thread_id": "t1"}'
```

`thread_id` is optional (a UUID is generated when it is missing). It keys the conversation memory, so reuse it to continue a conversation.

## Architecture

- `src/app/graph/agent.py` builds the graph. `src/app/api/main.py` exposes it. The package is `app` (hatchling packages `src/app`), so imports look like `from app.graph.agent import ...`.
- **Tool-calling graph (current `mcp` branch):** `START → agent → (tools_condition) → tools → respond → END`. The `agent` node is Gemini (`gemini-3.5-flash` via `langchain-google-genai`) with the MCP tools bound. The `respond` node calls the LLM again *without* tools to summarize tool output. This means there is one tool round per turn: `tools` does not loop back to `agent`. Commented code at the bottom of `agent.py` sketches the loop-back alternative.
- **Tools come from MCP servers at startup.** `init_graph()` is async. It lists tools from two MCP SSE endpoints (`JOBPULSE_MCP_URL`, default `http://localhost:8001/sse`, and `AMP_MCP_URL`, default `http://localhost:8002/sse`) and then compiles the graph. FastAPI's `lifespan` calls it once and stores the result on `app.state.chat_graph`, so **both MCP servers must be reachable when the API starts**.
- **Memory** is an `InMemorySaver` checkpointer keyed by `thread_id`. It is lost on restart and is not shared across workers.
- **Two entry points share `build_graph(tools, checkpointer=None)`.** FastAPI uses `init_graph()`, which adds an `InMemorySaver`. `langgraph dev` uses `make_graph()`, named in `langgraph.json`. It is an async context-manager factory that the server opens for each run: it connects to both MCP servers, yields a freshly built graph and closes the sessions when the run ends. That graph must have *no* checkpointer, because the LangGraph server supplies persistence and rejects a custom checkpointer. Keep the factory free of module-level caches. Values in `.env` override shell variables under `langgraph dev`.
- **Previous design (on `main`, v1.0.0):** a structured-output `intent_classifier` node (`Literal['job', 'classify_AMP']`) routed to a `job` node that POSTed to JobPulse `/search` over HTTP (`JOBPULSE_URL`), plus a placeholder AMP node. The README's mermaid diagram still describes this design.

## Configuration

Environment variables load from `.env` through `python-dotenv` (and through `langgraph.json`'s `env`). The ones in use are `GEMINI_API_KEY`, `JOBPULSE_MCP_URL`, `AMP_MCP_URL`, `CORS_ORIGINS` (comma-separated, default `http://localhost:5173` for the PLA frontend; CORS allows only `POST`), and `LANGSMITH_TRACING`. `.env` also has some leftover variables that the code does not read: `JOBPULSE_ENDPOINT`, `AMP_CLASSIFY_ENDPOINT`, `OLLAMA_HOST` and `MODEL_NAME`.

## Conventions

- `CHANGELOG.md` follows Keep a Changelog with SemVer. Add entries under `[Unreleased]`, and keep the version in `pyproject.toml` in step with the latest release.
- README roadmap items: MCP support (in progress on this branch), guardrails, eval goldens, and SSE streaming on `/chat`.
