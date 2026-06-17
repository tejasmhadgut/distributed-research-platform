import asyncio
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.core.queue import publish_task
from app.core.redis_client import publish_workflow_event
from app.models.workflow import WorkflowRun, WorkflowTask


async def dispatch_task(db, task: WorkflowTask, run_id: int) -> None:
    await db.execute(
        update(WorkflowTask)
        .where(WorkflowTask.id == task.id)
        .values(status="queued")
    )
    await db.commit()
    await publish_task("research_tasks", {
        "task_id": task.id,
        "task_type": task.task_type,
        "workflow_run_id": run_id,
        "input_data": task.input_data
    })
    await publish_workflow_event(run_id, {
        "task_id": task.id,
        "task_type": task.task_type,
        "status": "queued"
    })


async def dispatch_ready_tasks() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WorkflowRun).where(WorkflowRun.status == "pending")
        )
        runs = result.scalars().all()

        for run in runs:
            tasks_result = await db.execute(
                select(WorkflowTask).where(WorkflowTask.workflow_run_id == run.id)
            )
            tasks = tasks_result.scalars().all()
            completed_ids = {t.id for t in tasks if t.status == "completed"}
            all_completed = all(t.status == "completed" for t in tasks)
            any_failed = any(t.status == "failed" for t in tasks)

            if all_completed:
                await db.execute(
                    update(WorkflowRun).where(WorkflowRun.id == run.id).values(status="completed")
                )
                await db.commit()
                await publish_workflow_event(run.id, {"status": "completed"})
                continue

            if any_failed:
                await db.execute(
                    update(WorkflowRun).where(WorkflowRun.id == run.id).values(status="failed")
                )
                await db.commit()
                await publish_workflow_event(run.id, {"status": "failed"})
                continue

            for task in tasks:
                if task.status != "pending":
                    continue
                deps_met = all(dep_id in completed_ids for dep_id in task.dependencies)
                if deps_met:
                    await dispatch_task(db, task, run.id)


async def main() -> None:
    print("Workflow engine started...")
    while True:
        try:
            await dispatch_ready_tasks()
        except Exception as e:
            print(f"Engine error: {e}")
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
