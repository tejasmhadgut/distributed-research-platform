"""
Benchmark suite for the Distributed AI Research Platform.

Prerequisites:
  - Backend running at localhost:8000
  - At least one company researched (so financial data exists in DB)
  - pip install httpx websockets

Usage:
  python benchmarks/run_benchmarks.py --email you@example.com --password yourpass --ticker AAPL
"""

import argparse
import asyncio
import json
import statistics
import time

import httpx
import websockets

BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"


# ── helpers ──────────────────────────────────────────────────────────────────

def hdr(title: str):
    print(f"\n{'─' * 52}")
    print(f"  {title}")
    print(f"{'─' * 52}")


async def login(email: str, password: str) -> str:
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.post("/api/v1/auth/login", json={"email": email, "password": password})
        r.raise_for_status()
        return r.json()["access_token"]


async def create_session(token: str) -> int:
    async with httpx.AsyncClient(base_url=BASE) as c:
        r = await c.post(
            "/api/v1/sessions",
            json={"title": "benchmark-session"},
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json()["id"]


async def delete_session(token: str, session_id: int):
    async with httpx.AsyncClient(base_url=BASE) as c:
        await c.delete(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"},
        )


# ── benchmark 1: redis cache speedup ─────────────────────────────────────────

async def bench_cache(token: str, ticker: str, runs: int = 6):
    hdr("1. Redis Cache Speedup  (financial metrics endpoint)")
    url = f"{BASE}/api/v1/financial/metrics/{ticker}"
    headers = {"Authorization": f"Bearer {token}"}

    times = []
    async with httpx.AsyncClient() as c:
        for i in range(runs):
            t0 = time.perf_counter()
            r = await c.get(url, headers=headers)
            ms = (time.perf_counter() - t0) * 1000
            times.append(ms)
            label = "cold" if i == 0 else f"warm {i}"
            print(f"  [{label:6s}]  {ms:7.1f} ms   status={r.status_code}")

    cold = times[0]
    warm = statistics.mean(times[1:])
    print(f"\n  Cold:      {cold:.1f} ms")
    print(f"  Warm avg:  {warm:.1f} ms")
    print(f"  Speedup:   {cold / warm:.1f}x")
    return {"cold_ms": round(cold, 1), "warm_avg_ms": round(warm, 1), "speedup": round(cold / warm, 1)}


# ── benchmark 2: pgvector semantic search latency ────────────────────────────

async def bench_search(token: str, ticker: str, runs: int = 8):
    hdr("2. pgvector Semantic Search Latency")
    url = f"{BASE}/api/v1/documents/search"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"query": "revenue growth risk factors competition", "ticker": ticker, "limit": 5}

    times = []
    async with httpx.AsyncClient() as c:
        for i in range(runs):
            t0 = time.perf_counter()
            r = await c.post(url, json=payload, headers=headers)
            ms = (time.perf_counter() - t0) * 1000
            times.append(ms)
            n = len(r.json().get("results", [])) if r.status_code == 200 else 0
            print(f"  run {i+1:2d}:  {ms:7.1f} ms   results={n}")

    times_sorted = sorted(times)
    p50 = statistics.median(times)
    p99 = times_sorted[int(len(times) * 0.99) - 1] if len(times) >= 2 else times_sorted[-1]
    print(f"\n  p50:  {p50:.1f} ms")
    print(f"  p99:  {p99:.1f} ms")
    print(f"  min:  {min(times):.1f} ms")
    print(f"  max:  {max(times):.1f} ms")
    return {"p50_ms": round(p50, 1), "p99_ms": round(p99, 1), "min_ms": round(min(times), 1)}


# ── benchmark 3: websocket first-token + end-to-end latency ──────────────────

async def bench_ws_latency(token: str, ticker: str):
    hdr("3. WebSocket Research Latency  (single company query)")
    session_id = await create_session(token)
    url = f"{WS_BASE}/ws/session/{session_id}?token={token}"

    print(f"  Session: {session_id}  |  Ticker: {ticker}")
    print("  Sending query and timing events…\n")

    first_token_ms = None
    completed_ms = None

    async with websockets.connect(url) as ws:
        t0 = time.perf_counter()
        await ws.send(json.dumps({
            "question": f"Summarise {ticker} revenue and key risks briefly.",
            "ticker": ticker,
            "tickers": [],
        }))

        async for raw in ws:
            data = json.loads(raw)
            elapsed = (time.perf_counter() - t0) * 1000

            if data.get("type") == "status_update":
                print(f"  [{elapsed:7.0f} ms]  status → {data['message']}")

            elif data.get("type") == "chunk" and first_token_ms is None:
                first_token_ms = elapsed
                print(f"  [{elapsed:7.0f} ms]  first token received")

            elif data.get("status") == "completed":
                completed_ms = elapsed
                print(f"  [{elapsed:7.0f} ms]  completed")
                break

            elif data.get("status") == "failed":
                print(f"  [{elapsed:7.0f} ms]  FAILED")
                break

    await delete_session(token, session_id)

    print(f"\n  First token:   {first_token_ms:.0f} ms" if first_token_ms else "\n  First token:   —")
    print(f"  End-to-end:    {completed_ms:.0f} ms" if completed_ms else "  End-to-end:    —")
    return {
        "first_token_ms": round(first_token_ms) if first_token_ms else None,
        "end_to_end_ms": round(completed_ms) if completed_ms else None,
    }


# ── benchmark 4: concurrent websocket connections ────────────────────────────

async def bench_concurrent_ws(token: str, n: int = 10):
    hdr(f"4. Concurrent WebSocket Connections  (n={n})")

    session_ids = []
    for _ in range(n):
        sid = await create_session(token)
        session_ids.append(sid)

    async def connect_one(sid: int):
        url = f"{WS_BASE}/ws/session/{sid}?token={token}"
        try:
            t0 = time.perf_counter()
            async with websockets.connect(url) as ws:
                await ws.ping()
                ms = (time.perf_counter() - t0) * 1000
                return True, ms
        except Exception as e:
            return False, 0.0

    t0 = time.perf_counter()
    results = await asyncio.gather(*[connect_one(sid) for sid in session_ids])
    total_ms = (time.perf_counter() - t0) * 1000

    successes = [ms for ok, ms in results if ok]
    failures = n - len(successes)

    for i, (ok, ms) in enumerate(results):
        status = "OK" if ok else "FAIL"
        print(f"  conn {i+1:2d}:  {status}  {ms:.1f} ms")

    print(f"\n  Opened:   {len(successes)}/{n} connections simultaneously")
    print(f"  Failures: {failures}")
    print(f"  Avg connect time: {statistics.mean(successes):.1f} ms" if successes else "")
    print(f"  Total wall time:  {total_ms:.0f} ms")

    for sid in session_ids:
        await delete_session(token, sid)

    return {"concurrent": n, "successes": len(successes), "avg_connect_ms": round(statistics.mean(successes), 1) if successes else None}


# ── summary ───────────────────────────────────────────────────────────────────

def print_summary(results: dict):
    hdr("SUMMARY  (resume-ready numbers)")
    c = results.get("cache", {})
    s = results.get("search", {})
    w = results.get("ws", {})
    con = results.get("concurrent", {})

    if c:
        print(f"  Redis cache speedup:        {c['speedup']}x  ({c['cold_ms']} ms → {c['warm_avg_ms']} ms)")
    if s:
        print(f"  Semantic search latency:    {s['p50_ms']} ms p50  /  {s['p99_ms']} ms p99")
    if w:
        if w.get("first_token_ms"):
            print(f"  First token latency:        {w['first_token_ms']} ms")
        if w.get("end_to_end_ms"):
            print(f"  End-to-end research query:  {w['end_to_end_ms'] / 1000:.1f}s")
    if con:
        print(f"  Concurrent WS connections:  {con['successes']}/{con['concurrent']}  (avg {con['avg_connect_ms']} ms each)")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--ticker", default="AAPL")
    parser.add_argument("--skip-ws", action="store_true", help="Skip the full research query benchmark (slow)")
    parser.add_argument("--concurrent", type=int, default=10)
    args = parser.parse_args()

    print(f"\nLogging in as {args.email}…")
    token = await login(args.email, args.password)
    print("  OK")

    results = {}
    results["cache"] = await bench_cache(token, args.ticker)
    results["search"] = await bench_search(token, args.ticker)
    results["concurrent"] = await bench_concurrent_ws(token, args.concurrent)

    if not args.skip_ws:
        results["ws"] = await bench_ws_latency(token, args.ticker)

    print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
