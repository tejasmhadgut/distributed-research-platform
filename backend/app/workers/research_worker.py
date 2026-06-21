import asyncio
import json
import aio_pika
from sqlalchemy import update
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.redis_client import publish_workflow_event
from app.models.workflow import WorkflowTask
from app.services.research_service import run_research


async def handle_research_task(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        task_id = payload["task_id"]
        workflow_run_id = payload["workflow_run_id"]
        input_data = payload.get("input_data", {})
        question = input_data.get("question", "Analyze this company")
        ticker = input_data.get("ticker", "AAPL")

        async with AsyncSessionLocal() as db:
            await db.execute(
                update(WorkflowTask).where(WorkflowTask.id == task_id).values(status="running")
            )
            await db.commit()
            await publish_workflow_event(workflow_run_id, {"task_id": task_id, "task_type": "research", "status": "running"})

            try:
                result = await run_research(db, question, ticker)
                await db.execute(
                    update(WorkflowTask).where(WorkflowTask.id == task_id).values(status="completed", result=result)
                )
                status = "completed"
            except Exception as e:
                await db.execute(
                    update(WorkflowTask).where(WorkflowTask.id == task_id).values(status="failed", error=str(e))
                )
                status = "failed"

            await db.commit()
            await publish_workflow_event(workflow_run_id, {"task_id": task_id, "task_type": "research", "status": status})


async def main() -> None:
    print("Research worker started...")
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("research_tasks", durable=True)
        await queue.consume(handle_research_task)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
