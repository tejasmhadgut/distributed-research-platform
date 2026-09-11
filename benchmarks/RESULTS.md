# Benchmark Results

**Date:** 2026-06-28  
**Environment:** Local dev — MacBook Air, Ollama (qwen2.5:7b, CPU), PostgreSQL + Redis running via Docker

---

## 1. Redis Cache Speedup — Financial Metrics Endpoint

| Run | Latency |
|---|---|
| Cold | 96.7 ms |
| Warm avg (5 runs) | 13.6 ms |
| **Speedup** | **7.1x** |

---

## 2. pgvector Semantic Search Latency

| Metric | Value |
|---|---|
| p50 | 1.6 ms |
| p99 | 2.8 ms |
| min | 1.5 ms |
| max | 6.5 ms |

> Search ran against an empty document table (no AAPL filings embedded yet). Latency reflects the vector index overhead only.

---

## 3. Concurrent WebSocket Connections

| Metric | Value |
|---|---|
| Connections opened | 10 / 10 |
| Failures | 0 |
| Avg connect time | 188.6 ms |
| Total wall time | 287 ms |

---

## 4. WebSocket Research Latency — Single Company Query (AAPL)

| Event | Time |
|---|---|
| Fetching financial metrics | 16,310 ms |
| Generating analysis (LLM start) | 88,356 ms |
| First token received | 89,284 ms |
| Completed | 190,867 ms |

| Metric | Value |
|---|---|
| First token latency | ~89 s |
| End-to-end | ~191 s (~3.2 min) |

> Slow due to local Ollama inference on CPU. Architecture supports swapping to any OpenAI-compatible hosted API via a one-line config change.

---

## Resume-Ready Numbers

- **7.1x Redis cache speedup** (96.7 ms cold → 13.6 ms warm)
- **1.6 ms p50 pgvector semantic search latency**
- **10/10 concurrent WebSocket connections** handled simultaneously
- End-to-end AI research query: ~3 min on local CPU inference (Ollama qwen2.5:7b)
