from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.financial_data import CompanyMetrics
from app.models.quant import QuantResult
from app.core.cache import cache_delete
from app.core.cache_decorator import cached


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_metrics(row: CompanyMetrics) -> dict:
    price_data = row.price_data or {}
    income = row.income_statement or {}
    balance = row.balance_sheet or {}

    current_price = _safe_float(price_data.get("current_price"))
    week52_high = _safe_float(price_data.get("fifty_two_week_high"))
    week52_low = _safe_float(price_data.get("fifty_two_week_low"))
    pe_ratio = _safe_float(price_data.get("pe_ratio"))
    market_cap = _safe_float(price_data.get("market_cap"))
    total_revenue = _safe_float(income.get("total_revenue"))
    net_income = _safe_float(income.get("net_income"))
    total_assets = _safe_float(balance.get("total_assets"))
    total_debt = _safe_float(balance.get("total_debt"))

    metrics: dict = {}

    # How far price is from its 52-week high (0 = at high, -1 = at low)
    if current_price and week52_high and week52_high > 0:
        metrics["price_vs_52w_high"] = round((current_price - week52_high) / week52_high, 4)

    # 52-week range width as fraction of mid-price (proxy for volatility)
    if week52_high and week52_low and week52_low > 0:
        mid = (week52_high + week52_low) / 2
        metrics["volatility_proxy"] = round((week52_high - week52_low) / mid, 4)

    # Net profit margin
    if net_income is not None and total_revenue and total_revenue > 0:
        metrics["net_margin"] = round(net_income / total_revenue, 4)

    # Debt-to-asset ratio
    if total_debt is not None and total_assets and total_assets > 0:
        metrics["debt_to_assets"] = round(total_debt / total_assets, 4)

    # Price-to-earnings passthrough (already in price_data, centralised here)
    if pe_ratio is not None:
        metrics["pe_ratio"] = round(pe_ratio, 2)

    # Market cap tier
    if market_cap:
        if market_cap >= 200e9:
            metrics["cap_tier"] = "mega"
        elif market_cap >= 10e9:
            metrics["cap_tier"] = "large"
        elif market_cap >= 2e9:
            metrics["cap_tier"] = "mid"
        else:
            metrics["cap_tier"] = "small"

    return metrics


async def compute_quant(db: AsyncSession, ticker: str) -> QuantResult:
    result = await db.execute(
        select(CompanyMetrics)
        .where(CompanyMetrics.ticker == ticker)
        .order_by(desc(CompanyMetrics.fetched_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()

    if row is None:
        raise ValueError(f"No company_metrics found for {ticker}")

    metrics = _compute_metrics(row)
    quant = QuantResult(ticker=ticker, metrics=metrics)
    db.add(quant)
    await db.commit()
    await db.refresh(quant)
    await cache_delete(f"quant:{ticker.upper()}")
    return quant



@cached(key_fn=lambda db, ticker: f"quant:{ticker.upper()}", ttl=3600)
async def get_latest_quant(db: AsyncSession, ticker: str) -> dict | None:
    result = await db.execute(
        select(QuantResult)
        .where(QuantResult.ticker == ticker.upper())
        .order_by(desc(QuantResult.computed_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return {
        "id": row.id,
        "ticker": row.ticker,
        "computed_at": str(row.computed_at),
        "metrics": row.metrics,
    }
