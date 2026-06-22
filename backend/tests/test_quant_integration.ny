import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.financial_data import CompanyMetrics
from app.services.quant_service import compute_quant, get_latest_quant

pytestmark = pytest.mark.asyncio


async def _seed_metrics(db: AsyncSession, ticker: str):
    row = CompanyMetrics(
        ticker=ticker,
        price_data={
            "current_price": 213.55,
            "fifty_two_week_high": 260.10,
            "fifty_two_week_low": 169.21,
            "pe_ratio": 32.8,
            "market_cap": 3_200_000_000_000,
        },
        income_statement={"total_revenue": 391_035_000_000, "net_income": 93_736_000_000},
        balance_sheet={"total_assets": 364_980_000_000, "total_debt": 101_304_000_000},
        raw={},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def test_compute_quant_stores_result(db: AsyncSession):
    await _seed_metrics(db, "AAPL")
    result = await compute_quant(db, "AAPL")
    assert result.ticker == "AAPL"
    assert result.metrics["cap_tier"] == "mega"
    assert "net_margin" in result.metrics


async def test_get_latest_quant_returns_most_recent(db: AsyncSession):
    await _seed_metrics(db, "MSFT")
    await compute_quant(db, "MSFT")
    await compute_quant(db, "MSFT")
    result = await get_latest_quant(db, "MSFT")
    assert result is not None


async def test_compute_quant_missing_ticker(db: AsyncSession):
    with pytest.raises(ValueError, match="No company_metrics found"):
        await compute_quant(db, "FAKE")
