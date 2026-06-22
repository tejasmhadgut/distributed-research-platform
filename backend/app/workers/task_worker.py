import asyncio
import json
import aio_pika
from sqlalchemy import update
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.redis_client import publish_workflow_event
from app.models.workflow import WorkflowTask
from app.services.financial_service import fetch_and_store_metrics
from app.services.edgar_service import fetch_and_store_filings
from app.services.document_service import embed_filing


async def handle_task(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        task_id = payload["task_id"]
        task_type = payload["task_type"]
        workflow_run_id = payload["workflow_run_id"]
        input_data = payload.get("input_data", {})

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(WorkflowTask)
                .where(WorkflowTask.id == task_id)
                .values(status="running")
            )
            await db.commit()

            await publish_workflow_event(workflow_run_id, {
                "task_id": task_id,
                "task_type": task_type,
                "status": "running"
            })

            try:
                result = await execute_task(db, task_type, input_data, workflow_run_id)
                final_status = "completed"
                await db.execute(
                    update(WorkflowTask)
                    .where(WorkflowTask.id == task_id)
                    .values(status="completed", result=result)
                )
            except Exception as e:
                final_status = "failed"
                await db.execute(
                    update(WorkflowTask)
                    .where(WorkflowTask.id == task_id)
                    .values(status="failed", error=str(e))
                )

            await db.commit()

            await publish_workflow_event(workflow_run_id, {
                "task_id": task_id,
                "task_type": task_type,
                "status": final_status,
                "result": result if final_status == "completed" else None,
            })



async def execute_task(db, task_type: str, input_data: dict, workflow_run_id: int | None = None) -> dict:
    ticker = input_data.get("ticker", "AAPL")

    if task_type == "fetch_metrics":
        metrics = await fetch_and_store_metrics(db, ticker)
        return {"metrics_id": metrics.id, "ticker": metrics.ticker}

    if task_type == "search_filings":
        filings = await fetch_and_store_filings(db, ticker)
        return {"filing_ids": [f.id for f in filings], "ticker": ticker}

    if task_type == "analyze_data":
        return {"status": "analyzed", "ticker": ticker}

    if task_type == "generate_report":
        return {"status": "report_generated", "ticker": ticker}
    if task_type == "embed_filings":
        from sqlalchemy import select
        from app.models.financial_data import SECFiling
        result = await db.execute(
            select(SECFiling).where(SECFiling.ticker == ticker).order_by(SECFiling.id.desc())
        )
        filings = result.scalars().all()
        total_chunks = 0
        for filing in filings:
            chunks = await embed_filing(db, filing)
            total_chunks += len(chunks)
        return {"ticker": ticker, "chunks_stored": total_chunks}
    if task_type == "research":
        from app.services.research_service import run_research
        question = input_data.get("question", "Analyze this company")
        ticker = input_data.get("ticker", "AAPL")
        context = input_data.get("context", [])
        result = await run_research(db, question, ticker, context=context or None, workflow_run_id=workflow_run_id)
        return result


    return {"status": "unknown_task_type", "task_type": task_type}


async def main() -> None:
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue("research_tasks", durable=True)
    await queue.consume(handle_task)
    print("Worker started, waiting for tasks...")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
