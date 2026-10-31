<h1 align="center">PLA Agent</h1>

A langgraph agent that undertands what user wants and routes them to the right tool, job search or AMP classification, served through FastAPI

## Demo

![Chat asking for senior SRE jobs, answered with matching job listings from JobPulse](docs/jobpulse.png)

## Techstack
- Langgraph
- FastAPI
- Pydantics
- uv 
- Docker
- Ollama

## Architecture

```mermaid
flowchart LR
    client(["Frontend"]) -->|"POST /chat"| api["FastAPI"]
    api --> agent

    subgraph agent["LangGraph agent"]
        direction LR
        start((START)) --> classifier["intent_classifier"]
        classifier -->|"job"| job["job"]
        classifier -->|"classify_AMP"| amp["AMP_classify"]
        job --> finish((END))
        amp --> finish
    end

    classifier -. "structured output" .-> llm[["Gemini"]]
    job -.-> llm
    amp -.-> llm
    job -->|"POST /search"| jobpulse[("JobPulse")]
    amp -. "planned" .-> esm[("DistilESM-2-AMP")]
    agent --- memory[("InMemorySaver<br/>checkpoints")]
```

## Separate microservice
- [JobPulse](https://github.com/nakorn-b/jobpulse): A RAG-based job search assistant to help find relevant jobs from job posting
- [DistilESM-2-AMP](https://github.com/nakorn-b/distilESM-2-AMP): A distilled ESM architecture transformer fine-tuned for Antimicrobial Peptide (AMP) classification from peptide sequence


## Roadmap

- [ ] MCP (Model Context Protocol) support
- [ ] Guardrail
- [ ] Golden for eval
- [ ] Streaming responses via SSE on `/chat`


