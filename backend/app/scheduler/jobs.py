import json
import asyncio
import aio_pika
from sqlalchemy import select
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.financial_data import CompanyMetrics, SECFiling


async def _publish(queue_name: str, body: dict):
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(queue_name, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(body).encode()),
            routing_key=queue_name,
        )


async def daily_price_update():
    print("[scheduler] running daily_price_update")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CompanyMetrics.ticker).distinct()
        )
        tickers = [row[0] for row in result.fetchall()]

    for ticker in tickers:
        await _publish("task_queue", {"task_type": "fetch_metrics", "ticker": ticker})
        print(f"[scheduler] queued price update for {ticker}")


async def weekly_filing_refresh():
    print("[scheduler] running weekly_filing_refresh")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CompanyMetrics.ticker).distinct()
        )
        tickers = [row[0] for row in result.fetchall()]

    for ticker in tickers:
        await _publish("task_queue", {"task_type": "fetch_filings", "ticker": ticker})
        print(f"[scheduler] queued filing refresh for {ticker}")


async def weekly_embed_refresh():
    print("[scheduler] running weekly_embed_refresh")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SECFiling.ticker).where(SECFiling.filing_url.isnot(None)).distinct()
        )
        tickers = [row[0] for row in result.fetchall()]

    for ticker in tickers:
        await _publish("task_queue", {"task_type": "embed_filings", "ticker": ticker})
        print(f"[scheduler] queued embed refresh for {ticker}")


def run_daily_price_update():
    asyncio.run(daily_price_update())


def run_weekly_filing_refresh():
    asyncio.run(weekly_filing_refresh())


def run_weekly_embed_refresh():
    asyncio.run(weekly_embed_refresh())
