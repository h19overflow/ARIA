# ARIA — Agentic Real-time Intelligence Architect

> Translate natural language into deployed, tested n8n workflows — autonomously.

---

## What It Does

User describes a workflow in plain English. ARIA plans it, builds the n8n JSON, deploys it to a self-hosted n8n instance, runs it, and fixes any errors — without the user touching a node.

---

## Architecture

```
src/
├── api/                  ← FastAPI: routers, lifespan, settings, schemas
├── boundary/             ← External adapters: n8n REST, ChromaDB, scraper/parser
├── core/                 ← Pure domain logic: planning, composition, error classification
├── services/             ← Use-case orchestration: ingestion, retrieval, workflow, jobs
├── agentic_system/       ← LangGraph multi-agent graph: orchestrator, domain, test, fix
└── jobs/                 ← Async job queue: Redis producer/consumer + job model
```

**Dependency flow:**
```
api → services → core
api → services → boundary
services → agentic_system
agentic_system → boundary + core
jobs/worker → services
```

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic v2 |
| LLM | Gemini `gemini-3.1-pro-preview` via `langchain-google-genai` |
| Embeddings | `models/gemini-embedding-001` |
| Agent orchestration | LangGraph `1.0.9` |
| Vector store | ChromaDB via `langchain-chroma` |
| Async jobs | Redis |
| Scraping (static) | `httpx` + `BeautifulSoup4` |
| Scraping (SPA) | `Playwright` (Chromium headless) |
| n8n runtime | Self-hosted via Docker |

---

## Infrastructure (Docker)

```bash
docker compose up -d
```

Starts:
- **ChromaDB** on `localhost:8000`
- **n8n** on `localhost:5678`

---

## Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key

N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your_n8n_api_key

CHROMA_HOST=localhost
CHROMA_PORT=8000

REDIS_URL=redis://localhost:6379

GEMINI_MODEL=gemini-3.1-pro-preview
EMBEDDING_MODEL=models/gemini-embedding-001
```

---

## Installation

```bash
uv sync
uv run playwright install chromium
```

---

## What's Built So Far

### Scraper (`src/boundary/scraper/`)

Scrapes n8n's documentation and workflow templates to build the RAG knowledge base.

**Node docs** (`n8n_scraper.py → scrape_all_nodes`):
- Crawls `docs.n8n.io/integrations/builtin/app-nodes/`
- Fetches all 580+ individual node pages concurrently (semaphore: 5)
- Extracts: name, description, operations, parameters, URL
- Normalised into `N8nDocument` with `doc_type="node"`

**Workflow templates** (`n8n_scraper.py → scrape_workflow_templates`):
- Discovers URLs from `n8n.io/sitemap-workflows.xml` (700+ entries)
- Renders each page via Playwright (Vue/Nuxt SPA) with XHR interception
- Extracts: name, description, nodes used, URL
- Normalised into `N8nDocument` with `doc_type="workflow_template"`

**API spec parser** (`api_parser.py`):
- Accepts OpenAPI 3.x, Swagger 2.x, Postman Collection v2.x
- Auto-detects format, extracts all endpoints
- Normalised into `ApiEndpoint` with method, path, summary, description

### Vector Store (`src/boundary/chroma/`)

- Two collections: `n8n_documents` and `api_specs`
- All documents embedded with `GoogleGenerativeAIEmbeddings`
- Supports filtered semantic search by `doc_type` or `source`

### Ingestion Service (`src/services/ingestion_service.py`)

Three entry points:
- `ingest_n8n_nodes(store)` — scrape + embed all n8n nodes
- `ingest_n8n_workflow_templates(store, limit)` — scrape + embed workflow templates
- `ingest_api_spec(store, spec, source_name)` — parse + embed user API spec

### Retrieval Service (`src/services/retrieval_service.py`)

- `retrieve_n8n_nodes(store, query)` — semantic search over node docs
- `retrieve_workflow_templates(store, query)` — semantic search over templates
- `retrieve_api_endpoints(store, query, source)` — semantic search over user API specs

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest/n8n/nodes` | Trigger n8n node doc scrape + embed |
| `POST` | `/ingest/n8n/workflows` | Trigger workflow template scrape + embed |
| `POST` | `/ingest/api-spec` | Parse and embed a user API spec |
| `POST` | `/workflows` | Submit NL workflow request (async job) |
| `GET` | `/jobs/{id}` | Poll job status |

---

## Test Scripts

```bash
# Run the scraper and export results to scripts/outputs/
uv run python scripts/test_scraper.py

# Semantic search example (requires ChromaDB running + data ingested)
uv run python scripts/example_query.py
```

Outputs:
- `scripts/outputs/scraper_nodes.json` — all scraped node documents
- `scripts/outputs/scraper_workflows.json` — sampled workflow template documents

---

## What's Next
- [ ] Implement `agentic_system/` LangGraph graph
- [ ] Implement `jobs/` worker loop
- [ ] Implement `boundary/n8n/client.py` REST wrapper
