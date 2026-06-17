from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.workflow import WorkflowRun, WorkflowTask


WORKFLOW_DEFINITIONS = {
    "compare_companies": [
        {"task_type": "fetch_metrics", "dependencies": [], "input_key": "companies"},
        {"task_type": "search_filings", "dependencies": [], "input_key": "companies"},
        {"task_type": "analyze_data",  "dependencies": ["fetch_metrics", "search_filings"],"input_type":None},
        {"task_type":"generate_report",  "dependencies": ["analyze_data"], "input_key": None},
    ]
}

async def create_workflow(
    db: AsyncSession,
    session_id: int,
    question: str,
    workflow_type: str,
    input_data: dict
) -> WorkflowRun:
    run = WorkflowRun(session_id=session_id, question=question, status="pending")
    db.add(run)
    await db.flush()

    task_definitions = WORKFLOW_DEFINITIONS.get(workflow_type, WORKFLOW_DEFINITIONS["compare_companies"])
    type_to_id: dict[str, int] = {}

    for task_def in task_definitions:
        dep_ids = [type_to_id[dep] for dep in task_def["dependencies"]]
        task = WorkflowTask(
            workflow_run_id=run.id,
            task_type=task_def["task_type"],
            dependencies=dep_ids,
            input_data=input_data if not task_def["dependencies"] else {},
            status="pending"
        )
        db.add(task)
        await db.flush()
        type_to_id[task_def["task_type"]] = task.id

    await db.commit()
    await db.refresh(run)
    return run

async def get_workflow(db: AsyncSession, workflow_run_id: int) -> WorkflowRun | None:
    result = await db.execute(
        select(WorkflowRun).where(WorkflowRun.id == workflow_run_id)

    )
    return result.scalar_one_or_none()

async def get_workflow_tasks(db: AsyncSession, workflow_run_id: int) -> list[WorkflowTask]:
    result = await db.execute(
        select(WorkflowTask).where(WorkflowTask.workflow_run_id == workflow_run_id)
    )
    return list(result.scalars().all())
