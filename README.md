# ARIA — Agentic Real-time Intelligence Architect

> Describe a workflow in plain English. ARIA builds, deploys, and fixes it on n8n.

**Status:** Under active development

---

## What It Does

ARIA takes a natural language description like *"When I get a webhook, send a Slack message to #general"* and autonomously:

1. Identifies which n8n nodes are needed
2. Resolves credentials against your n8n instance
3. Retrieves node templates from a RAG store
4. Assembles and deploys the workflow JSON
5. Tests it, and if it fails — classifies the error and fixes it

The end result is a live, activated workflow running on your self-hosted n8n.

---

## Quick Start

```bash
# Install dependencies
uv sync

# Start infrastructure (n8n + ChromaDB)
docker compose up -d

# Copy and fill in your keys
cp .env.example .env

# Run the demo (no infrastructure needed — uses mocks)
python scripts/demo_agentic_system.py
```

---

## Project Structure

```
src/
├── agentic_system/    LangGraph pipeline (preflight + build cycle)
├── api/               FastAPI endpoints
├── boundary/          External adapters (n8n, ChromaDB, scraper)
├── core/              Domain logic
├── services/          Use-case orchestration
└── jobs/              Async job queue
```

---

## Stack

| What | Tech |
|------|------|
| LLM | Google Gemini via LangChain |
| Agent framework | LangGraph |
| Vector store | ChromaDB |
| Workflow runtime | n8n (self-hosted) |
| API | FastAPI |
| Async jobs | Redis |

---

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — system design, component diagrams, implementation status
- [`docs/agentic_system/`](docs/agentic_system/) — detailed design docs for both pipeline stages
- [`docs/main.md`](docs/main.md) — product specification

---

## Environment Variables

```env
GOOGLE_API_KEY=your_google_api_key
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your_n8n_api_key
CHROMA_HOST=localhost
CHROMA_PORT=8001
REDIS_URL=redis://localhost:6379
```
