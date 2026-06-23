# Distributed AI Research Platform

An AI-powered investment research platform built as a distributed system. Analysts ask natural-language questions about public companies; the platform orchestrates a multi-step workflow across independent workers to fetch financial data, search SEC filings, run quant analytics, and stream a cited research report back in real time.

---

## Architecture

```
┌─────────────┐     WebSocket      ┌──────────────────┐
│   React UI  │ ◄────────────────► │   FastAPI (API)  │
└─────────────┘                    └────────┬─────────┘
                                            │ creates workflow
                                            ▼
                                   ┌──────────────────┐
                                   │  Postgres + DAG  │
                                   └────────┬─────────┘
                                            │ dispatches tasks
                                            ▼
                              ┌─────────────────────────┐
                              │       RabbitMQ          │
                              └──┬──────────┬───────────┘
                                 │          │
                    ┌────────────▼──┐  ┌────▼────────────┐
                    │  Task Worker  │  │  Quant Worker   │
                    │  (ReAct LLM)  │  │  (analytics)    │
                    └───────┬───────┘  └─────────────────┘
                            │ publishes chunks
                            ▼
                       ┌─────────┐
                       │  Redis  │ ◄── pub/sub for streaming
                       └─────────┘     + cache + rate limiting
```

**Request flow:** User submits a question → API creates a workflow run in Postgres → Workflow Engine dispatches DAG tasks to RabbitMQ → Task Worker runs a ReAct LLM loop (tool calls → observations → synthesis) → streams tokens via Redis pub/sub → WebSocket forwards chunks to the browser in real time.

---

## Features

- **Natural language queries** — type company names or plain English; LLM extracts and resolves tickers (Apple → AAPL, "the chip maker" → NVDA)
- **ReAct research loop** — LLM reasons and calls tools iteratively (fetch metrics, search filings, embed documents) before synthesizing a report
- **Multi-company comparison** — side-by-side analysis with a single query; produces markdown tables and a verdict
- **SEC filing search** — 10-K/10-Q documents chunked, embedded (pgvector), and searchable by semantic similarity
- **Quant analytics** — net margin, debt/assets, P/E, 52-week position, cap tier computed per ticker
- **Real-time streaming** — research streams token-by-token via WebSocket with live status updates (Fetching metrics → Searching filings → Generating analysis)
- **Persistent sessions** — multi-turn research context; sessions are named from the first query and renameable inline
- **Automated scheduling** — daily price updates and weekly filing refreshes via APScheduler
- **Redis caching** — financial data, research reports, and document searches cached with explicit invalidation on write
- **Per-user rate limiting** — fixed-window Redis counter keyed by JWT subject

---

## Stack

| Layer | Technology |
|---|---|
| API | Python 3.13, FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL 16 + pgvector |
| Cache / pub-sub | Redis 7 |
| Message queue | RabbitMQ 3 |
| AI | Ollama (qwen2.5:7b) — local, zero cost |
| Embeddings | Ollama (nomic-embed-text) |
| Financial data | defeatbeta-api (prices, income statements, balance sheets) |
| SEC filings | EDGAR Submissions API (no key required) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Infra | Docker Compose (9 services) |
| Testing | Pytest, pytest-asyncio, GitHub Actions CI |

---

## Running Locally

**Prerequisites:** Docker, Ollama with `qwen2.5:7b` and `nomic-embed-text` pulled.

```bash
# Clone
git clone https://github.com/tejasmhadgut/distributed-research-platform.git
cd distributed-research-platform

# Start everything
docker-compose up --build
```

The frontend is served at `http://localhost:5173`. The API is at `http://localhost:8000`.

**Without Docker (dev mode):**

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Workers (separate terminals)
python -m app.workers.workflow_engine
python -m app.workers.task_worker

# Frontend
cd frontend
npm install && npm run dev
```

**Environment variables** (`backend/.env`):

```
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5433/research_platform
REDIS_URL=redis://localhost:6380
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
SECRET_KEY=your-secret-key
```

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI route handlers
│   │   ├── services/          # Business logic (research, quant, LLM, EDGAR)
│   │   ├── workers/           # RabbitMQ consumers (task worker, workflow engine)
│   │   ├── tools/             # LLM tool registry (decorator-based auto-registration)
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── scheduler/         # APScheduler jobs (daily prices, weekly filings)
│   │   ├── middleware/         # Rate limiting
│   │   └── core/              # Config, database, Redis, cache decorator
│   └── tests/                 # Unit + integration tests
└── frontend/
    └── src/
        ├── components/        # DataPanel, ResearchThread, Sidebar, ResearchInput
        ├── contexts/          # Auth, Sessions
        ├── hooks/             # useWebSocket (auto-reconnect, status streaming)
        └── pages/             # WorkspacePage, LoginPage, RegisterPage
```

---

## Key Design Decisions

**Why RabbitMQ over Kafka?** Research tasks need exactly-once execution with acknowledgment and retry semantics — a task queue pattern. Kafka is built for event streaming and replay, which this platform doesn't need.

**Why a DAG workflow engine?** Independent tasks (Fetch Metrics, Search Filings) can run in parallel; the Analyze task blocks until both complete. Implicit ordering can't express this.

**Why Redis pub/sub for WebSocket events?** In-memory connection maps break with multiple API processes. Redis pub/sub lets any API instance forward events to any connected client — horizontally scalable from day one.

**Why Ollama over OpenAI API?** Zero cost, no API key, data stays local. The architecture is identical — swapping to OpenAI is a one-line config change.

**Why `redirect_slashes=False` on FastAPI?** The default 307 redirect causes browsers to drop the `Authorization` header per the HTTP spec, returning 403 on every authenticated endpoint.

---

## Testing

```bash
cd backend
pytest tests/ -v
```

CI runs on every push via GitHub Actions — spins up real Postgres (pgvector) and Redis as services, runs migrations, then executes the full pytest suite.
