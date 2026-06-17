from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.financial_data import CompanyMetrics, SECFiling

router = APIRouter(prefix="/financial", tags=["financial"])


@router.get("/metrics/{ticker}")
async def get_metrics(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(CompanyMetrics)
        .where(CompanyMetrics.ticker == ticker.upper())
        .order_by(CompanyMetrics.fetched_at.desc())
        .limit(1)
    )
    metrics = result.scalar_one_or_none()
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found for ticker")
    return {
        "ticker": metrics.ticker,
        "fetched_at": metrics.fetched_at,
        "price_data": metrics.price_data,
        "income_statement": metrics.income_statement,
        "balance_sheet": metrics.balance_sheet
    }


@router.get("/filings/{ticker}")
async def get_filings(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(SECFiling)
        .where(SECFiling.ticker == ticker.upper())
        .order_by(SECFiling.fetched_at.desc())
    )
    filings = result.scalars().all()
    return [
        {
            "id": f.id,
            "form_type": f.form_type,
            "filed_at": f.filed_at,
            "filing_url": f.filing_url
        }
        for f in filings
    ]
