# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-24

### Added

- LangGraph agent that classifies user intent as either job search (`job`) or
  AMP classification (`classify_AMP`) using Gemini structured output, and routes
  the message to the matching node.
- Job search node that queries the JobPulse `/search` service and presents the
  matching jobs (title, company, location, URL). It falls back to a friendly
  message when the service is unavailable or no jobs are found.
- Placeholder AMP classification node.
- In-memory conversation checkpointing for the agent graph.
- FastAPI app with a `POST /chat` endpoint that sends a message to the agent and
  returns its reply.
- `JOBPULSE_URL` environment variable to configure the JobPulse service
  (defaults to `http://localhost:8888`). Environment variables load from `.env`.
- `langgraph.json` configuration for the LangGraph CLI.
- `langchain-google-genai` dependency and Hatchling build backend.
- Initial project setup: `pyproject.toml`, `uv.lock`, Python version pin and
  `.gitignore`.

[unreleased]: https://github.com/nakorn-b/pla-agent/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/nakorn-b/pla-agent/releases/tag/v1.0.0
