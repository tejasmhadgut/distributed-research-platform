from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.tools.registry import list_tools, call_tool

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolCallRequest(BaseModel):
    input_data: dict


@router.get("/")
async def get_tools():
    return {"tools": list_tools()}


@router.post("/{tool_name}")
async def execute_tool(
    tool_name: str,
    body: ToolCallRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await call_tool(tool_name, body.input_data, db)
        return {"tool": tool_name, "result": result}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
