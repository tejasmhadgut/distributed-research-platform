from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.services.quant_service import compute_quant, get_latest_quant

router = APIRouter(prefix="/quant", tags=["quant"])


class QuantRequest(BaseModel):
    ticker: str


@router.post("/")
async def run_quant(req: QuantRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await compute_quant(db, req.ticker.upper())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "id": result.id,
        "ticker": result.ticker,
        "computed_at": result.computed_at,
        "metrics": result.metrics,
    }


@router.get("/{ticker}")
async def get_quant(ticker: str, db: AsyncSession = Depends(get_db)):
    result = await get_latest_quant(db, ticker.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"No quant results for {ticker}")
    return {
        "id": result.id,
        "ticker": result.ticker,
        "computed_at": result.computed_at,
        "metrics": result.metrics,
    }
