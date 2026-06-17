import asyncio
import json
import aio_pika
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.redis_client import publish_workflow_event
from app.models.workflow import WorkflowTask


async def handle_task(message: aio_pika.IncomingMessage) -> None:
    async with message.process():
        payload = json.loads(message.body)
        task_id = payload["task_id"]
        task_type = payload["task_type"]
        workflow_run_id = payload["workflow_run_id"]

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
                result = await execute_task(task_type, payload.get("input_data", {}))
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
                "status": final_status
            })


async def execute_task(task_type: str, input_data: dict) -> dict:
    await asyncio.sleep(1)
    return {"task_type": task_type, "status": "simulated", "input": input_data}


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
