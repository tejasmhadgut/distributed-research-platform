# Distributed AI Investment Research Platform

An AI-powered investment research platform built as a distributed system. Analysts submit natural-language questions about public companies; the platform orchestrates a multi-step workflow across independent workers to fetch financial data, search SEC filings, run quant analytics, and stream a cited research report back to the browser in real time.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        React UI (Vite)                       │
│  ResearchThread · DataPanel · Sidebar · ResearchInput        │
└──────────────────────────┬───────────────────────────────────┘
                           │  WebSocket (streaming) + REST
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI  (API server)                      │
│  JWT auth · Rate limiting · Session management · WS relay    │
└──────┬────────────────────────────────────────┬─────────────┘
       │ creates workflow run                   │ pub/sub
       ▼                                        ▼
┌─────────────┐                         ┌─────────────┐
│  PostgreSQL │                         │    Redis    │
│  + pgvector │                         │  cache · RL │
│  DAG state  │                         │  streaming  │
└──────┬──────┘                         └─────────────┘
       │ dispatches tasks
       ▼
┌──────────────────────────────────────────────────────────────┐
│                        RabbitMQ                              │
└──────┬───────────────────────────┬────────────────┬─────────┘
       │                           │                │
       ▼                           ▼                ▼
┌─────────────────┐   ┌────────────────────┐  ┌───────────────┐
│ Workflow Engine │   │   Task Worker      │  │ Quant Worker  │
│ DAG scheduler   │   │   ReAct LLM loop   │  │ analytics     │
└─────────────────┘   │   tool registry    │  └───────────────┘
                      └────────────────────┘
```

**Request flow:**
1. User submits a question → LLM extracts tickers from natural language (Apple → AAPL)
2. API creates a workflow run in Postgres and dispatches tasks via RabbitMQ
3. Task Worker runs a ReAct loop: LLM reasons, calls tools (fetch metrics, search filings, embed docs), and synthesizes a report
4. Each step publishes status events to Redis pub/sub → WebSocket streams tokens + status messages to the browser in real time

---

## Features

- **Natural language queries** — type company names or plain English; a pre-flight LLM call extracts and resolves tickers before the workflow starts
- **Instant sidebar** — DataPanel opens immediately with a loading skeleton while tickers are being identified, no waiting for a server round-trip
- **ReAct research loop** — LLM reasons iteratively, calling tools (fetch metrics, search filings, compute quant) before synthesizing a report
- **Multi-company comparison** — side-by-side analysis with a single query; produces markdown tables and a verdict section
- **SEC filing search** — 10-K / 10-Q documents chunked, embedded with `nomic-embed-text` via pgvector, and searchable by semantic similarity
- **Quant analytics** — net margin, debt/assets, P/E, 52-week position, cap tier computed per ticker and surfaced in the DataPanel
- **Real-time streaming** — token-by-token via WebSocket with live phase labels (Fetching metrics → Searching filings → Generating analysis)
- **Formatted AI output** — responses rendered as markdown with headers, tables, bold text, and a Summary / Verdict section
- **WebSocket auto-reconnect** — up to 3 retries on unintentional disconnect; messages preserved across reconnects
- **Client-side data caching** — DataPanel caches per-ticker data in a `useRef` Map; switching between tickers in compare mode is instant
- **Persistent sessions** — multi-turn research context; sessions named from the first query and renameable inline
- **Automated scheduling** — daily price updates and weekly filing refreshes via APScheduler
- **Redis caching** — financial data, research reports, and document searches cached with explicit invalidation on write
- **Per-user rate limiting** — fixed-window Redis counter keyed by JWT subject

---

## Stack

| Layer | Technology |
|---|---|
| API | Python 3.11, FastAPI, SQLAlchemy (async) |
| Database | PostgreSQL 16 + pgvector |
| Cache / pub-sub | Redis 7 |
| Message queue | RabbitMQ 3 |
| AI | Ollama (`qwen2.5:7b`) — local, zero cost |
| Embeddings | Ollama (`nomic-embed-text`) |
| Financial data | defeatbeta-api (prices, income statements, balance sheets) |
| SEC filings | EDGAR Submissions API (no API key required) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Infra | Docker Compose (9 services) |
| Testing | Pytest, pytest-asyncio, GitHub Actions CI |

---

## Running Locally

**Prerequisites:** Docker Desktop, Ollama running locally with the two models pulled:

```bash
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### Docker (recommended)

```bash
git clone https://github.com/tejasmhadgut/distributed-research-platform.git
cd distributed-research-platform

cp backend/.env.example backend/.env   # edit values if needed
docker-compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

### Manual (dev mode)

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 2. Workers (separate terminals)
python -m app.workers.workflow_engine
python -m app.workers.task_worker
python -m app.workers.quant_worker

# 3. Frontend
cd frontend
npm install && npm run dev
```

### Environment variables (`backend/.env`)

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
│   │   ├── api/routes/        # FastAPI route handlers (auth, sessions, ws, financial, quant, documents)
│   │   ├── services/          # Business logic (research, quant, LLM, EDGAR)
│   │   ├── workers/           # RabbitMQ consumers (workflow engine, task worker, quant worker)
│   │   ├── tools/             # LLM tool registry — decorator-based auto-registration
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── scheduler/         # APScheduler jobs (daily prices, weekly filings)
│   │   ├── middleware/         # Per-user rate limiting
│   │   └── core/              # Config, database, Redis, cache decorator
│   ├── alembic/               # Database migrations
│   └── tests/                 # Unit + integration tests (pytest)
├── frontend/
│   └── src/
│       ├── components/        # DataPanel, ResearchThread, Sidebar, ResearchInput
│       ├── contexts/          # Auth (JWT), Sessions
│       ├── hooks/             # useWebSocket (streaming, auto-reconnect, status events)
│       └── pages/             # WorkspacePage, LoginPage, RegisterPage
└── docker-compose.yml         # All 9 services with healthchecks
```

---

## Key Design Decisions

**Why RabbitMQ over direct async calls?**
Research tasks are long-running (10–30s) and need exactly-once execution with retry semantics. RabbitMQ's acknowledgment model gives per-task durability without the complexity of a full job queue framework.

**Why a DAG workflow engine?**
Independent tasks (Fetch Metrics, Search Filings) can run in parallel while the Analyze task blocks until both complete. A simple task list can't express this dependency graph.

**Why Redis pub/sub for WebSocket streaming?**
In-memory connection maps break with multiple API processes. Redis pub/sub lets any API instance forward events to any connected client — horizontally scalable from day one.

**Why Ollama over OpenAI API?**
Zero cost, no API key, data stays local. The architecture is model-agnostic — swapping to OpenAI or Anthropic is a one-line config change.

**Why `redirect_slashes=False` on FastAPI?**
The default 307 redirect drops the `Authorization` header per the HTTP spec, causing 403 on every authenticated endpoint when URLs are called without a trailing slash.

**Why pre-flight LLM extraction instead of requiring a ticker field?**
Forcing users to know ticker symbols breaks the natural language interface. A synchronous pre-flight call to the LLM resolves company names (or descriptions like "the big chip maker") to symbols before the workflow starts, without changing the research pipeline.

---

## Testing

```bash
cd backend
pytest tests/ -v
```

CI runs on every push via GitHub Actions — spins up real PostgreSQL (pgvector) and Redis as services, runs Alembic migrations, then executes the full pytest suite against live infrastructure.
